"""Seed deterministic mock damage into mock tyre surveys only.

Server destination:
    apps/engineering/engineering/seed_mock_tyre_damage.py

Mock grader utilisation remains in ``mock_grader_utilisation.json`` and is
never written to the real Availability and Utilisation DocType.
"""

import hashlib
import json
from pathlib import Path

import frappe
from frappe import _


DATA_FILE = Path(__file__).with_name("mock_grader_utilisation.json")
MOCK_INSPECTOR = "Mock Survey Generator"
MOCK_DAMAGE_MARKER = "[MOCK DAMAGE: GRADER-COMPARISON-2026]"
NORMAL_MOCK_NOTES = {
    "",
    "Mock monthly reading",
    "Mock complete six-wheel survey reading",
}
DAMAGE_TYPES = (
    (
        "Sidewall cut",
        "Inspect sidewall and remove tyre from service if casing is exposed",
    ),
    (
        "Tread impact damage",
        "Inspect impact area and schedule repair assessment",
    ),
    (
        "Puncture",
        "Repair puncture and verify pressure before returning to service",
    ),
    (
        "Bead damage",
        "Remove tyre and inspect bead and rim condition",
    ),
    (
        "Tread separation",
        "Remove tyre from service and arrange casing inspection",
    ),
)


def _as_bool(value):
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no"}
    return bool(value)


def _stable_number(*parts):
    payload = "|".join(str(part) for part in parts)
    return int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12], 16)


def _load_months():
    if not DATA_FILE.exists():
        frappe.throw(_("Missing mock grader data file: {0}").format(DATA_FILE))

    with DATA_FILE.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    return payload.get("months") or []


def _mock_rows(month):
    survey_meta = frappe.get_meta("Tyre Survey")
    tyres_field = survey_meta.get_field("tyres")

    if not tyres_field or not tyres_field.options:
        frappe.throw(_("Tyre Survey has no configured tyres child table."))

    child_doctype = tyres_field.options
    child_table = "tab{0}".format(child_doctype.replace("`", "``"))
    rows = frappe.db.sql(
        """
        SELECT
            tsi.name,
            tsi.condition_notes,
            tsi.required_action
        FROM `{child_table}` tsi
        INNER JOIN `tabTyre Survey` ts ON ts.name = tsi.parent
        WHERE ts.inspector_name = %(inspector)s
          AND ts.docstatus = 0
          AND DATE_FORMAT(ts.survey_date, '%%Y-%%m') = %(month)s
        ORDER BY tsi.name
        """.format(child_table=child_table),
        {"inspector": MOCK_INSPECTOR, "month": month},
        as_dict=True,
    )
    return child_doctype, rows


def seed(dry_run=True):
    """Add clearly marked mock damage without touching actual surveys."""

    dry_run = _as_bool(dry_run)
    result = {
        "dry_run": dry_run,
        "dataset": "MOCK ONLY",
        "months": [],
        "damage_rows_added": 0,
        "damage_rows_already_seeded": 0,
        "actual_surveys_modified": 0,
    }

    for month_data in _load_months():
        month = str(month_data["month"])
        target = int(month_data.get("damage_target") or 0)
        child_doctype, rows = _mock_rows(month)
        existing = [
            row
            for row in rows
            if MOCK_DAMAGE_MARKER in str(row.condition_notes or "")
        ]
        candidates = [
            row
            for row in rows
            if row in existing
            or str(row.condition_notes or "").strip() in NORMAL_MOCK_NOTES
        ]
        candidates.sort(key=lambda row: _stable_number(month, row.name))
        selected = candidates[:target]
        to_add = [row for row in selected if row not in existing]

        for row in to_add:
            damage_index = _stable_number(month, row.name, "damage") % len(
                DAMAGE_TYPES
            )
            damage_type, action = DAMAGE_TYPES[damage_index]

            if not dry_run:
                frappe.db.set_value(
                    child_doctype,
                    row.name,
                    {
                        "condition_notes": "{0} {1}".format(
                            MOCK_DAMAGE_MARKER,
                            damage_type,
                        ),
                        "required_action": "{0} [MOCK]".format(action),
                    },
                    update_modified=False,
                )

        result["damage_rows_added"] += len(to_add)
        result["damage_rows_already_seeded"] += len(existing)
        result["months"].append(
            {
                "month": month,
                "mock_grader_utilisation": month_data.get(
                    "grader_utilisation"
                ),
                "damage_target": target,
                "eligible_mock_rows": len(candidates),
                "already_seeded": len(existing),
                "would_add": len(to_add),
            }
        )

    if not dry_run:
        frappe.db.commit()

    return result
