"""Create deterministic mock Tyre Surveys for January-June 2026.

Server destination:
    apps/engineering/engineering/mock_tyre_surveys.py

The companion ``mock_tyre_survey_source.json`` file must be placed in the
same directory. The source contains the observed June 2026 ADT/site/position
mapping. Earlier months simulate tyre rotations and remounts between ADTs at
the same site. No lifetime ADT or position is written back to Tyre Master.

The generator is safe to rerun:

* dry-run mode is the default;
* a fleet/month is skipped if any Tyre Survey already exists for it;
* only serials that currently exist in Tyre Master are included;
* every created document carries an unmistakable mock-data marker.
"""

import hashlib
import json
from calendar import monthrange
from datetime import date
from pathlib import Path

import frappe
from frappe import _
from frappe.utils import flt


SOURCE_FILE = Path(__file__).with_name(
    "mock_tyre_survey_source.json"
)

MOCK_MARKER = "[MOCK DATA: TYRE-SURVEY-SEED-2026-H1]"
MOCK_INSPECTOR = "Mock Survey Generator"

SURVEY_MONTHS = [
    (2026, 1),
    (2026, 2),
    (2026, 3),
    (2026, 4),
    (2026, 5),
    (2026, 6),
]

SITE_ALIASES = {
    "MMS Klipfontein": [
        "Klipfontein",
        "MMS Klipfontein",
    ],
    "Gwab": ["Gwab"],
    "Seriti Kriel Colliery Block 6": [
        "Kriel Rehabilitation",
        "Seriti Kriel Colliery Block 6",
    ],
}

TYRE_MASTER_FIELDS = [
    "serial_number",
    "brand_number",
    "tyre_make",
    "tyre_size",
    "tread_pattern",
    "star_ply_rating",
    "tra_code",
    "compound_code",
    "overall_diameter",
    "otd",
    "recommended_pressure",
]


def _normalise_serial(value):
    return str(value or "").strip().upper()


def _stable_number(*parts):
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def _bounded_number(seed_parts, minimum, maximum, decimals=1):
    span = maximum - minimum
    ratio = (_stable_number(*seed_parts) % 1000000) / 999999
    return round(minimum + (span * ratio), decimals)


def _load_source_rows():
    if not SOURCE_FILE.exists():
        frappe.throw(
            _("Missing mock survey source file: {0}").format(SOURCE_FILE)
        )

    with SOURCE_FILE.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    rows = payload.get("import_ready") or []

    if not rows:
        frappe.throw(_("The mock survey source contains no ADT tyre rows."))

    return rows


def _clean_position(row):
    by_row_number = {
        1: "LF",
        2: "RF",
        3: "RM",
        4: "RR",
        5: "LR",
        6: "LM",
    }

    try:
        row_number = int(row.get("row_number") or 0)
    except (TypeError, ValueError):
        row_number = 0

    if row_number in by_row_number:
        return by_row_number[row_number]

    raw = str(row.get("position") or "").upper()
    compact = "".join(character for character in raw if character.isalpha())

    aliases = {
        "LF": "LF",
        "RF": "RF",
        "RM": "RM",
        "RR": "RR",
        "LR": "LR",
        "SLR": "LR",
        "LM": "LM",
    }

    return aliases.get(compact, compact or "UNKNOWN")


def _source_assignments():
    assignments = {}

    for row in _load_source_rows():
        serial = _normalise_serial(row.get("serial_number"))

        if not serial or serial in assignments:
            continue

        assignments[serial] = {
            "serial_number": serial,
            "site": str(row.get("site") or "").strip(),
            "fleet_number": str(row.get("fleet_number") or "").strip(),
            "position": _clean_position(row),
            "june_rtd_1": flt(row.get("rtd1")),
            "june_rtd_2": flt(row.get("rtd2")),
            "june_actual_pressure": flt(row.get("actual_pressure")),
        }

    return assignments


def _get_tyre_masters(serials):
    meta = frappe.get_meta("Tyre Master")
    fields = [
        fieldname
        for fieldname in TYRE_MASTER_FIELDS
        if fieldname == "serial_number" or meta.has_field(fieldname)
    ]

    masters = frappe.get_all(
        "Tyre Master",
        filters={"serial_number": ["in", list(serials)]},
        fields=fields,
        limit_page_length=1000,
    )

    return {
        _normalise_serial(master.serial_number): master
        for master in masters
    }


def _asset_name_candidates(source_name):
    candidates = [source_name]
    upper_name = source_name.upper()

    if upper_name.startswith("IS0"):
        candidates.append("IS" + source_name[3:])
    elif upper_name.startswith("IS"):
        candidates.append("IS0" + source_name[2:])

    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def _resolve_asset(source_name):
    for candidate in _asset_name_candidates(source_name):
        if frappe.db.exists("Asset", candidate):
            return candidate

    asset_meta = frappe.get_meta("Asset")

    if asset_meta.has_field("asset_name"):
        for candidate in _asset_name_candidates(source_name):
            asset = frappe.db.get_value(
                "Asset",
                {"asset_name": candidate},
                "name",
            )

            if asset:
                return asset

    return None


def _get_asset_details(asset_name):
    meta = frappe.get_meta("Asset")
    fields = ["name"]

    for fieldname in ("location", "item_code"):
        if meta.has_field(fieldname):
            fields.append(fieldname)

    return frappe.db.get_value(
        "Asset",
        asset_name,
        fields,
        as_dict=True,
    )


def _resolve_site(source_site, asset_details):
    asset_location = (
        asset_details.get("location")
        if asset_details
        else None
    )

    if asset_location and frappe.db.exists("Location", asset_location):
        return asset_location

    for candidate in SITE_ALIASES.get(source_site, [source_site]):
        if candidate and frappe.db.exists("Location", candidate):
            return candidate

    return None


def _resolve_supplier(requested_supplier=None):
    if requested_supplier:
        if not frappe.db.exists("Supplier", requested_supplier):
            frappe.throw(
                _("Supplier does not exist: {0}").format(requested_supplier)
            )

        return requested_supplier

    for doctype in (
        "Tyre Survey",
        "Tyre Survey Supplier Portal Draft",
    ):
        if not frappe.db.exists("DocType", doctype):
            continue

        recent = frappe.get_all(
            doctype,
            filters={"supplier": ["is", "set"]},
            fields=["supplier"],
            order_by="creation desc",
            limit_page_length=1,
        )

        if recent and recent[0].supplier:
            return recent[0].supplier

    suppliers = frappe.get_all(
        "Supplier",
        pluck="name",
        limit_page_length=3,
    )

    if len(suppliers) == 1:
        return suppliers[0]

    frappe.throw(
        _(
            "Supplier could not be selected automatically. Run again with "
            "--kwargs '{\"supplier\":\"EXACT SUPPLIER NAME\"}'."
        )
    )


def _month_bounds(year, month):
    return (
        date(year, month, 1),
        date(year, month, monthrange(year, month)[1]),
    )


def _survey_date(fleet_number, year, month):
    last_day = monthrange(year, month)[1]
    day = 20 + (_stable_number(fleet_number, year, month, "day") % 8)
    return date(year, month, min(day, last_day))


def _existing_survey_for_month(fleet_number, year, month):
    first_day, last_day = _month_bounds(year, month)

    records = frappe.get_all(
        "Tyre Survey",
        filters={
            "fleet_number": fleet_number,
            "survey_date": ["between", [first_day, last_day]],
        },
        pluck="name",
        limit_page_length=1,
    )

    return records[0] if records else None


def _reading_values(master, assignment, month_number):
    serial = assignment["serial_number"]
    otd = flt(master.get("otd"))
    recommended = flt(master.get("recommended_pressure")) or 500.0

    june_rtd_1 = assignment.get("june_rtd_1") or max(otd * 0.68, 8.0)
    june_rtd_2 = assignment.get("june_rtd_2") or max(otd * 0.70, 8.0)
    months_before_june = 6 - month_number

    monthly_wear_1 = _bounded_number(
        (serial, "wear-1"),
        0.55,
        1.35,
        2,
    )
    monthly_wear_2 = _bounded_number(
        (serial, "wear-2"),
        0.55,
        1.35,
        2,
    )

    rtd_1 = min(otd, june_rtd_1 + (monthly_wear_1 * months_before_june))
    rtd_2 = min(otd, june_rtd_2 + (monthly_wear_2 * months_before_june))
    rtd_1 = round(max(rtd_1, 1.0), 1)
    rtd_2 = round(max(rtd_2, 1.0), 1)

    if month_number == 6 and assignment.get("june_actual_pressure"):
        actual_pressure = assignment["june_actual_pressure"]
    else:
        pressure_variance = _bounded_number(
            (serial, month_number, "pressure"),
            -0.12,
            0.12,
            4,
        )
        actual_pressure = round(recommended * (1 + pressure_variance), 0)

    average_rtd = (rtd_1 + rtd_2) / 2
    rtd_percent = round((average_rtd / otd) * 100, 1) if otd else 0
    pressure_percent = (
        round(((actual_pressure - recommended) / recommended) * 100, 1)
        if recommended
        else 0
    )

    notes = "Mock monthly reading"
    required_action = "No action required"

    if rtd_percent <= 20:
        notes = "Mock low tread condition"
        required_action = "Plan tyre replacement"
    elif abs(pressure_percent) >= 10:
        notes = "Mock pressure variance"
        required_action = "Correct pressure and recheck"

    return {
        "rtd_1": rtd_1,
        "rtd_2": rtd_2,
        "rtd_percent": rtd_percent,
        "recommended_pressure": recommended,
        "actual_pressure": actual_pressure,
        "pressure_variance": pressure_percent,
        "condition_notes": notes,
        "required_action": required_action,
    }


def _tyre_row(master, assignment, position, month_number):
    values = {
        "position": position,
        "serial_number": assignment["serial_number"],
    }

    for fieldname in TYRE_MASTER_FIELDS:
        if fieldname != "serial_number":
            values[fieldname] = master.get(fieldname)

    values.update(_reading_values(master, assignment, month_number))
    return values


def _monthly_slot_assignments(resolved_rows):
    """Build monthly historical snapshots without permanent wheel binding.

    June retains the placement observed in the source reports. Working
    backwards, roughly 60 percent of tyres are deterministically swapped to
    different ADT/position slots at the same site each month. The movement is
    reproducible on every run and a serial occurs only once per month.
    """

    by_site = {}

    for row in resolved_rows:
        by_site.setdefault(row["site"], []).append(dict(row))

    monthly = {month: [] for _, month in SURVEY_MONTHS}
    simulated_remounts = 0

    for site, june_rows in sorted(by_site.items()):
        current = sorted(
            june_rows,
            key=lambda row: (
                row["asset_name"],
                row["position"],
                row["assignment"]["serial_number"],
            ),
        )
        monthly[6].extend(dict(row) for row in current)

        for month in range(5, 0, -1):
            earlier = [dict(row) for row in current]
            order = sorted(
                range(len(earlier)),
                key=lambda index: _stable_number(
                    site,
                    month,
                    earlier[index]["asset_name"],
                    earlier[index]["position"],
                    earlier[index]["assignment"]["serial_number"],
                ),
            )
            pair_count = min(
                len(order) // 2,
                max(1, int(len(order) * 0.30)),
            )

            for pair_index in range(pair_count):
                left = order[pair_index * 2]
                right = order[(pair_index * 2) + 1]

                earlier[left]["master"], earlier[right]["master"] = (
                    earlier[right]["master"],
                    earlier[left]["master"],
                )
                earlier[left]["assignment"], earlier[right]["assignment"] = (
                    earlier[right]["assignment"],
                    earlier[left]["assignment"],
                )
                simulated_remounts += 2

            monthly[month].extend(dict(row) for row in earlier)
            current = earlier

    return monthly, simulated_remounts


def _header_values(
    supplier,
    site,
    asset_name,
    survey_date,
    tyre_count,
):
    meta = frappe.get_meta("Tyre Survey")
    values = {
        "doctype": "Tyre Survey",
        "supplier": supplier,
        "site": site,
        "fleet_number": asset_name,
        "survey_date": survey_date,
        "general_remarks": (
            "{0} Historical reporting seed; {1} mapped ADT tyres."
        ).format(MOCK_MARKER, tyre_count),
    }

    optional_values = {
        "inspector_name": MOCK_INSPECTOR,
        "portal_user": frappe.session.user or "Administrator",
        "machine_type": "ADT",
    }

    for fieldname, value in optional_values.items():
        if meta.has_field(fieldname):
            values[fieldname] = value

    return values


def generate(supplier=None, dry_run=True):
    """Generate the January-June 2026 mock Tyre Surveys.

    Run a preview first::

        bench --site jorrie.isambane.co.za execute \
          engineering.mock_tyre_surveys.generate

    Import after reviewing the preview::

        bench --site jorrie.isambane.co.za execute \
          engineering.mock_tyre_surveys.generate \
          --kwargs '{"dry_run": false}'

    Pass ``supplier`` in kwargs only if automatic supplier selection cannot use
    an existing Tyre Survey or Supplier Portal Draft.
    """

    if isinstance(dry_run, str):
        dry_run = dry_run.strip().lower() not in {"0", "false", "no"}

    assignments = _source_assignments()
    masters = _get_tyre_masters(assignments.keys())
    selected_supplier = _resolve_supplier(supplier)
    resolved_rows = []
    missing_assets = set()
    missing_sites = set()

    for serial, assignment in assignments.items():
        master = masters.get(serial)

        if not master:
            continue

        asset_name = _resolve_asset(assignment["fleet_number"])

        if not asset_name:
            missing_assets.add(assignment["fleet_number"])
            continue

        asset_details = _get_asset_details(asset_name)
        site = _resolve_site(assignment["site"], asset_details)

        if not site:
            missing_sites.add(assignment["site"])
            continue

        resolved_rows.append(
            {
                "asset_name": asset_name,
                "site": site,
                "position": assignment["position"],
                "master": master,
                "assignment": assignment,
            }
        )

    monthly_assignments, simulated_remounts = _monthly_slot_assignments(
        resolved_rows
    )
    mapped_fleets = {
        row["asset_name"]
        for row in resolved_rows
    }

    result = {
        "dry_run": bool(dry_run),
        "supplier": selected_supplier,
        "source_assignments": len(assignments),
        "matched_tyre_masters": len(masters),
        "mapped_fleets": len(mapped_fleets),
        "simulated_tyre_remounts": simulated_remounts,
        "surveys_created": 0,
        "surveys_would_create": 0,
        "surveys_skipped_existing_month": 0,
        "tyre_rows_created": 0,
        "tyre_rows_would_create": 0,
        "missing_assets": sorted(missing_assets),
        "missing_sites": sorted(missing_sites),
        "created_documents": [],
    }

    for year, month in SURVEY_MONTHS:
        grouped_for_month = {}

        for row in monthly_assignments[month]:
            key = (row["asset_name"], row["site"])
            grouped_for_month.setdefault(key, []).append(row)

        for (asset_name, site), tyres in sorted(grouped_for_month.items()):
            tyres.sort(key=lambda row: row["position"])
            existing = _existing_survey_for_month(asset_name, year, month)

            if existing:
                result["surveys_skipped_existing_month"] += 1
                continue

            result["surveys_would_create"] += 1
            result["tyre_rows_would_create"] += len(tyres)

            if dry_run:
                continue

            survey_date = _survey_date(asset_name, year, month)
            document = frappe.get_doc(
                _header_values(
                    selected_supplier,
                    site,
                    asset_name,
                    survey_date,
                    len(tyres),
                )
            )

            for row in tyres:
                document.append(
                    "tyres",
                    _tyre_row(
                        row["master"],
                        row["assignment"],
                        row["position"],
                        month,
                    ),
                )

            document.insert(ignore_permissions=True)
            result["surveys_created"] += 1
            result["tyre_rows_created"] += len(tyres)
            result["created_documents"].append(document.name)

            if result["surveys_created"] % 25 == 0:
                frappe.db.commit()

    if not dry_run:
        frappe.db.commit()

    result["created_documents"] = result["created_documents"][:20]
    return result


def delete_mock_surveys(confirm=None):
    """Delete only records created by this generator.

    This is intentionally guarded.  It does nothing unless ``confirm`` is the
    exact phrase ``DELETE MOCK SURVEYS``.
    """

    if confirm != "DELETE MOCK SURVEYS":
        frappe.throw(
            _(
                "Deletion was not confirmed. Pass: "
                "--kwargs '{\"confirm\":\"DELETE MOCK SURVEYS\"}'"
            )
        )

    records = frappe.get_all(
        "Tyre Survey",
        filters={"general_remarks": ["like", "%{0}%".format(MOCK_MARKER)]},
        pluck="name",
        limit_page_length=1000,
    )

    for name in records:
        frappe.delete_doc(
            "Tyre Survey",
            name,
            ignore_permissions=True,
            force=True,
        )

    frappe.db.commit()
    return {"deleted": len(records)}
