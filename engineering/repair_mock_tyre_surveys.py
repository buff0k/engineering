"""Repair incomplete January-June 2026 mock ADT tyre surveys.

Server destination:
    apps/engineering/engineering/repair_mock_tyre_surveys.py

The original seed generator only used existing Tyre Master serials and could
therefore create surveys with fewer than six wheel rows.  This repair is
deliberately limited to records whose inspector is ``Mock Survey Generator``.
It never changes real/manual surveys and never writes an ADT or wheel position
back to Tyre Master.
"""

import re

import frappe
from frappe import _
from frappe.utils import flt, getdate


MOCK_INSPECTOR = "Mock Survey Generator"
START_DATE = "2026-01-01"
END_DATE = "2026-06-30"
STANDARD_POSITIONS = ("LF", "RF", "LM", "RM", "LR", "RR")
B60_POSITIONS = ("LF", "RF", "LRO", "LRI", "RRI", "RRO")
B60_POSITION_MAP = {
    "LF": "LF",
    "RF": "RF",
    "LM": "LRI",
    "LR": "LRO",
    "RM": "RRI",
    "RR": "RRO",
    "LRI": "LRI",
    "LRO": "LRO",
    "RRI": "RRI",
    "RRO": "RRO",
}


def _as_bool(value):
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no"}
    return bool(value)


def _asset_information(asset_name):
    """Use the portal's proven Asset/Item model resolver."""

    from engineering.templates.pages.tyre_survey_sup import (
        _get_asset_information,
    )

    return _get_asset_information(asset_name)


def _expected_positions(asset_name):
    information = _asset_information(asset_name)
    layout = str(information.get("tyre_layout") or "standard").lower()
    return (
        B60_POSITIONS if layout == "b60e" else STANDARD_POSITIONS,
        layout,
        information,
    )


def _mock_serial(asset_name, position):
    asset_code = re.sub(r"[^A-Z0-9]+", "", str(asset_name).upper())
    return "MOCK-H1-{0}-{1}".format(asset_code, position)


def _field_values(meta, values):
    return {
        fieldname: value
        for fieldname, value in values.items()
        if fieldname == "doctype" or meta.has_field(fieldname)
    }


def _get_or_create_master(asset_name, position, dry_run):
    serial = _mock_serial(asset_name, position)
    existing = frappe.db.get_value(
        "Tyre Master",
        {"serial_number": serial},
        "name",
    )

    if existing:
        return frappe.get_doc("Tyre Master", existing), False

    meta = frappe.get_meta("Tyre Master")
    values = _field_values(
        meta,
        {
            "doctype": "Tyre Master",
            "serial_number": serial,
            "brand_number": serial,
            "tyre_make": "Mock Seed Tyre",
            "tyre_size": "29.5R25",
            "tread_pattern": "MOCK-ADT",
            "star_ply_rating": "**",
            "tra_code": "E-3",
            "compound_code": "MOCK",
            "overall_diameter": 1875,
            "otd": 65,
            "recommended_pressure": 550,
            "active": 1,
        },
    )

    if dry_run:
        return frappe._dict(values), True

    document = frappe.get_doc(values)
    document.insert(ignore_permissions=True)
    return document, True


def _reading_values(master, survey_date):
    month = getdate(survey_date).month
    otd = flt(master.get("otd")) or 65.0
    # Deterministic, realistic decline that produces usable monthly history.
    rtd = max(14.0, round(otd - (month * 2.2), 1))
    recommended = flt(master.get("recommended_pressure")) or 550.0
    actual = round(recommended * 0.98, 1)

    return {
        "rtd_1": rtd,
        "rtd_2": rtd,
        "rtd_percent": round((rtd / otd) * 100, 1) if otd else 0,
        "recommended_pressure": recommended,
        "actual_pressure": actual,
        "pressure_variance": -2.0,
        "condition_notes": "Mock complete six-wheel survey reading",
        "required_action": "No action required",
    }


def _child_row(master, position, survey_date):
    child_doctype = frappe.get_meta("Tyre Survey").get_field("tyres").options
    meta = frappe.get_meta(child_doctype)
    values = {
        "position": position,
        "serial_number": master.get("serial_number"),
        "brand_number": master.get("brand_number"),
        "tyre_make": master.get("tyre_make"),
        "tyre_size": master.get("tyre_size"),
        "tread_pattern": master.get("tread_pattern"),
        "star_ply_rating": master.get("star_ply_rating"),
        "tra_code": master.get("tra_code"),
        "compound_code": master.get("compound_code"),
        "overall_diameter": master.get("overall_diameter"),
        "otd": master.get("otd"),
    }
    values.update(_reading_values(master, survey_date))
    return _field_values(meta, values)


def repair(dry_run=True):
    """Complete only the mock H1 surveys to exactly six tyre positions.

    Preview::

        bench --site jorrie.isambane.co.za execute \
          engineering.repair_mock_tyre_surveys.repair

    Apply::

        bench --site jorrie.isambane.co.za execute \
          engineering.repair_mock_tyre_surveys.repair \
          --kwargs '{"dry_run": False}'
    """

    dry_run = _as_bool(dry_run)
    survey_meta = frappe.get_meta("Tyre Survey")

    if not survey_meta.has_field("inspector_name"):
        frappe.throw(
            _(
                "Safety stop: Tyre Survey has no inspector_name field, so "
                "mock surveys cannot be identified without risking real data."
            )
        )

    surveys = frappe.get_all(
        "Tyre Survey",
        filters={
            "inspector_name": MOCK_INSPECTOR,
            "survey_date": ["between", [START_DATE, END_DATE]],
            "docstatus": ["<", 2],
        },
        fields=["name", "fleet_number", "survey_date", "docstatus"],
        order_by="survey_date asc, fleet_number asc",
        limit_page_length=1000,
    )

    result = {
        "dry_run": dry_run,
        "mock_surveys_found": len(surveys),
        "surveys_repaired": 0,
        "positions_renamed_for_b60": 0,
        "missing_rows_added": 0,
        "mock_tyre_masters_created": 0,
        "surveys_already_complete": 0,
        "surveys_skipped_submitted": 0,
        "remaining_incomplete": [],
    }

    created_master_serials = set()

    for survey_row in surveys:
        if int(survey_row.docstatus or 0) != 0:
            result["surveys_skipped_submitted"] += 1
            continue

        document = frappe.get_doc("Tyre Survey", survey_row.name)
        expected, layout, information = _expected_positions(
            document.fleet_number
        )
        changed = False

        if layout == "b60e":
            for tyre in document.get("tyres") or []:
                old_position = str(tyre.position or "").strip().upper()
                new_position = B60_POSITION_MAP.get(old_position, old_position)

                if new_position != old_position:
                    tyre.position = new_position
                    result["positions_renamed_for_b60"] += 1
                    changed = True

        current_positions = {
            str(tyre.position or "").strip().upper()
            for tyre in document.get("tyres") or []
        }
        missing = [position for position in expected if position not in current_positions]

        for position in missing:
            master, created = _get_or_create_master(
                document.fleet_number,
                position,
                dry_run,
            )
            serial = master.get("serial_number")

            if created and serial not in created_master_serials:
                created_master_serials.add(serial)
                result["mock_tyre_masters_created"] += 1

            if not dry_run:
                document.append(
                    "tyres",
                    _child_row(master, position, document.survey_date),
                )

            result["missing_rows_added"] += 1
            changed = True

        if not changed:
            result["surveys_already_complete"] += 1
            continue

        result["surveys_repaired"] += 1

        if not dry_run:
            document.flags.ignore_permissions = True
            document.save(ignore_permissions=True)

    if not dry_run:
        frappe.db.commit()

    # A second count is reported in apply mode so incomplete results cannot be
    # mistaken for success. Submitted mock surveys are listed separately.
    if not dry_run:
        for survey_row in surveys:
            if int(survey_row.docstatus or 0) != 0:
                continue

            document = frappe.get_doc("Tyre Survey", survey_row.name)
            expected, _, _ = _expected_positions(document.fleet_number)
            positions = {
                str(row.position or "").strip().upper()
                for row in document.get("tyres") or []
            }

            if len(document.get("tyres") or []) != 6 or set(expected) != positions:
                result["remaining_incomplete"].append(document.name)

    result["remaining_incomplete"] = result["remaining_incomplete"][:20]
    return result
