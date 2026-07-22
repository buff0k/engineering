from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta

import frappe
from frappe.utils import add_months, getdate, today

from engineering.tyre_analytics import get_latest_analytics


STANDARD_LAYOUT_IMAGE = (
    "/assets/engineering/images/tyre_layouts/Standard_adt.png"
)
B60E_LAYOUT_IMAGE = (
    "/assets/engineering/images/tyre_layouts/Bell_B60E.png"
)
B60E_POSITIONS = {"RRO", "RRI", "LRI", "LRO"}


def _month_start(value):
    value = getdate(value)
    return date(value.year, value.month, 1)


def _month_end(value):
    return date(value.year, value.month, monthrange(value.year, value.month)[1])


def _average(values, precision=1):
    values = [value for value in values if value is not None]
    return round(sum(values) / len(values), precision) if values else 0


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
            "layout_image": STANDARD_LAYOUT_IMAGE,
            "tyres": [],
        }

    tyres = [row for row in rows if row.fleet_number == fleet_number]
    positions = {str(row.position or "").upper() for row in tyres}
    layout_image = (
        B60E_LAYOUT_IMAGE
        if positions.intersection(B60E_POSITIONS)
        else STANDARD_LAYOUT_IMAGE
    )

    return {
        "fleet_number": fleet_number,
        "site": tyres[0].site if tyres else None,
        "layout_image": layout_image,
        "tyres": [
            {
                "survey": row.survey,
                "survey_date": row.survey_date,
                "position": row.position,
                "serial_number": row.serial_number,
                "tyre_make": row.tyre_make,
                "tread_pattern": row.tread_pattern,
                "average_rtd": row.average_rtd,
                "rtd_percent": row.rtd_percent,
                "wear_rate": row.wear_rate,
                "pressure_variance": row.pressure_variance,
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
    rows = get_latest_analytics(
        as_on_date=anchor_date,
        include_mock=True,
    )

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
        "urgent_tyres": _urgent_rows(rows),
        "adt_view": _adt_view(rows, fleet_number),
    }
