from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
import json
from pathlib import Path

import frappe
from frappe.utils import add_months, getdate, today

from engineering.tyre_analytics import get_latest_analytics


STANDARD_LAYOUT_IMAGE = (
    "/assets/engineering/images/tyre_layouts/Standard_adt.png?v=20260716b"
)
B60E_LAYOUT_IMAGE = (
    "/assets/engineering/images/tyre_layouts/Bell_B60E.png?v=20260716b"
)
B60E_POSITIONS = {"RRO", "RRI", "LRI", "LRO"}
MOCK_DAMAGE_MARKER = "[MOCK DAMAGE: GRADER-COMPARISON-2026]"
MOCK_GRADER_DATA_FILE = (
    Path(__file__).resolve().parents[3]
    / "mock_grader_utilisation.json"
)
MODEL_FIELDS = (
    "custom_vehicle_model",
    "vehicle_model",
    "custom_model",
    "model",
)
MAKE_FIELDS = (
    "custom_vehicle_make",
    "vehicle_make",
    "custom_make",
    "make",
    "manufacturer",
    "brand",
)
KNOWN_MODELS = ("740GC", "B60E", "B60", "B45E", "B40E", "B40D", "A40G")


def _month_start(value):
    value = getdate(value)
    return date(value.year, value.month, 1)


def _month_end(value):
    return date(value.year, value.month, monthrange(value.year, value.month)[1])


def _average(values, precision=1):
    values = [value for value in values if value is not None]
    return round(sum(values) / len(values), precision) if values else 0


def _first_doc_value(doc, fieldnames):
    meta = frappe.get_meta(doc.doctype)

    for fieldname in fieldnames:
        if meta.has_field(fieldname) and doc.get(fieldname):
            return str(doc.get(fieldname)).strip()

    return ""


def _asset_information(asset_name):
    if not frappe.db.exists("Asset", asset_name):
        return {"vehicle_make": "", "model": ""}

    asset = frappe.get_doc("Asset", asset_name)
    item = None
    vehicle_make = _first_doc_value(asset, MAKE_FIELDS)
    model = _first_doc_value(asset, MODEL_FIELDS)
    searchable = [
        asset.name,
        asset.get("item_name"),
        asset.get("item_code"),
        vehicle_make,
        model,
    ]

    if asset.get("item_code") and frappe.db.exists("Item", asset.item_code):
        item = frappe.get_doc("Item", asset.item_code)
        vehicle_make = vehicle_make or _first_doc_value(item, MAKE_FIELDS)
        model = model or _first_doc_value(item, MODEL_FIELDS)
        searchable.extend(
            [
                item.get("item_name"),
                item.get("item_code"),
                item.get("description"),
                vehicle_make,
                model,
            ]
        )

    model_text = "".join(
        character
        for character in " ".join(
            str(value) for value in searchable if value not in (None, "")
        ).upper()
        if character.isalnum()
    )

    for known_model in KNOWN_MODELS:
        if known_model in model_text:
            model = known_model
            break

    if not vehicle_make and str(model).upper().startswith("B"):
        vehicle_make = "Bell"

    return {"vehicle_make": vehicle_make, "model": model}


def _group_average(rows, key_field, value_field):
    grouped = defaultdict(list)

    for row in rows:
        value = row.get(value_field)

        if value is not None and value > 0:
            grouped[row.get(key_field) or "Not Set"].append(value)

    result = [
        {
            "label": label,
            "value": _average(values, 2),
        }
        for label, values in grouped.items()
    ]
    result.sort(key=lambda item: (-item["value"], item["label"]))
    return result


def _pressure_compliance_by_site(rows):
    grouped = defaultdict(list)

    for row in rows:
        grouped[row.site or "Not Set"].append(row.pressure_compliant)

    result = [
        {
            "label": site,
            "value": round((sum(values) / len(values)) * 100, 1),
        }
        for site, values in grouped.items()
    ]
    result.sort(key=lambda item: item["label"])
    return result


def _replacement_forecast(rows, anchor_date):
    first_month = _month_start(add_months(anchor_date, 1))
    forecast = []

    for offset in range(5):
        month = _month_start(add_months(first_month, offset))
        last_day = _month_end(month)
        count = sum(
            1
            for row in rows
            if row.replacement_date
            and month <= getdate(row.replacement_date) <= last_day
        )
        forecast.append(
            {
                "label": month.strftime("%b %Y"),
                "value": count,
            }
        )

    return forecast


def _mock_grader_damage_comparison():
    """Return only the isolated mock comparison dataset."""

    if not MOCK_GRADER_DATA_FILE.exists():
        return []

    with MOCK_GRADER_DATA_FILE.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    survey_meta = frappe.get_meta("Tyre Survey")
    tyres_field = survey_meta.get_field("tyres")

    if not tyres_field or not tyres_field.options:
        return []

    child_table = "tab{0}".format(
        tyres_field.options.replace("`", "``")
    )
    damage_rows = frappe.db.sql(
        """
        SELECT ts.survey_date
        FROM `{child_table}` tsi
        INNER JOIN `tabTyre Survey` ts ON ts.name = tsi.parent
        WHERE ts.inspector_name = %(inspector)s
          AND ts.docstatus = 0
          AND COALESCE(tsi.condition_notes, '') LIKE %(marker)s
        """.format(child_table=child_table),
        {
            "inspector": "Mock Survey Generator",
            "marker": "%{0}%".format(MOCK_DAMAGE_MARKER),
        },
        as_dict=True,
    )
    damage_counts = defaultdict(int)

    for row in damage_rows:
        month_key = getdate(row.survey_date).strftime("%Y-%m")
        damage_counts[month_key] += 1

    return [
        {
            "label": date.fromisoformat(
                "{0}-01".format(month["month"])
            ).strftime("%b %Y"),
            "month": month["month"],
            "grader_utilisation": month.get("grader_utilisation") or 0,
            "damaged_tyres": damage_counts.get(month["month"], 0),
            "damage_target": month.get("damage_target") or 0,
            "data_status": "MOCK ONLY",
        }
        for month in payload.get("months") or []
    ]


def _urgent_rows(rows):
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            -row.urgency_score,
            row.remaining_months
            if row.remaining_months is not None
            else 999999,
            row.site or "",
            row.fleet_number or "",
        ),
    )

    return [
        {
            "site": row.site,
            "fleet_number": row.fleet_number,
            "position": row.position,
            "serial_number": row.serial_number,
            "average_rtd": row.average_rtd,
            "wear_rate": row.wear_rate,
            "remaining_months": row.remaining_months,
            "replacement_date": row.replacement_date,
            "urgency_score": row.urgency_score,
            "urgency_band": row.urgency_band,
            "required_action": row.required_action,
        }
        for row in sorted_rows[:10]
    ]


def _adt_view(rows, fleet_number):
    if not fleet_number:
        return {
            "fleet_number": None,
            "site": None,
            "vehicle_make": None,
            "model": None,
            "tyre_layout": "standard",
            "layout_image": STANDARD_LAYOUT_IMAGE,
            "tyres": [],
        }

    tyres = [row for row in rows if row.fleet_number == fleet_number]
    positions = {str(row.position or "").upper() for row in tyres}

    asset_information = _asset_information(fleet_number)

    model_code = "".join(
        character
        for character in str(asset_information.get("model") or "").upper()
        if character.isalnum()
    )
    is_b60 = "B60" in model_code or bool(
        positions.intersection(B60E_POSITIONS)
    )
    layout_image = (
        B60E_LAYOUT_IMAGE
        if is_b60
        else STANDARD_LAYOUT_IMAGE
    )

    return {
        "fleet_number": fleet_number,
        "site": tyres[0].site if tyres else None,
        "vehicle_make": asset_information.get("vehicle_make"),
        "model": asset_information.get("model"),
        "tyre_layout": "b60e" if is_b60 else "standard",
        "layout_image": layout_image,
        "tyres": [
            {
                "survey": row.survey,
                "survey_date": row.survey_date,
                "position": row.position,
                "serial_number": row.serial_number,
                "tyre_make": row.tyre_make,
                "tread_pattern": row.tread_pattern,
                "otd": row.otd,
                "average_rtd": row.average_rtd,
                "rtd_percent": row.rtd_percent,
                "wear_rate": row.wear_rate,
                "recommended_pressure": row.recommended_pressure,
                "actual_pressure": row.actual_pressure,
                "pressure_variance": row.pressure_variance,
                "scrap_limit_mm": 14,
                "remaining_months": row.remaining_months,
                "replacement_date": row.replacement_date,
                "urgency_score": row.urgency_score,
                "urgency_band": row.urgency_band,
                "condition_notes": row.condition_notes,
                "required_action": row.required_action,
            }
            for row in tyres
        ],
    }


@frappe.whitelist()
def get_dashboard_data(as_on_date=None, site=None, fleet_number=None):
    anchor_date = getdate(as_on_date or today())
    all_rows = get_latest_analytics(
        as_on_date=anchor_date,
        include_mock=True,
    )
    rows = all_rows

    if site:
        rows = [row for row in rows if row.site == site]

    bands = ["Critical", "Warning", "Check", "Good", "Normal"]
    band_counts = [
        {
            "label": band,
            "value": sum(1 for row in rows if row.urgency_band == band),
        }
        for band in bands
    ]
    due_date = anchor_date + timedelta(days=30)

    return {
        "as_on_date": anchor_date,
        "scrap_limit_mm": 14,
        "kpis": {
            "tyres_analysed": len(rows),
            "critical": sum(1 for row in rows if row.urgency_band == "Critical"),
            "warning": sum(1 for row in rows if row.urgency_band == "Warning"),
            "below_25_percent": sum(1 for row in rows if row.rtd_percent < 25),
            "underinflated": sum(1 for row in rows if row.pressure_variance < -10),
            "due_within_30_days": sum(
                1
                for row in rows
                if row.replacement_date
                and getdate(row.replacement_date) <= due_date
            ),
        },
        "replacement_forecast": _replacement_forecast(rows, anchor_date),
        "urgency_bands": band_counts,
        "site_wear": _group_average(rows, "site", "wear_rate"),
        "brand_wear": _group_average(rows, "tyre_make", "wear_rate")[:10],
        "pressure_compliance": _pressure_compliance_by_site(rows),
        "mock_grader_damage": _mock_grader_damage_comparison(),
        "urgent_tyres": _urgent_rows(rows),
        # The machine view is intentionally independent of the Site filter.
        # A selected ADT must always show its latest fitted tyres and layout.
        "adt_view": _adt_view(all_rows, fleet_number),
    }
