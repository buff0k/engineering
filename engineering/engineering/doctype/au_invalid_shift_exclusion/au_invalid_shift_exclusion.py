import hashlib
import json

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime


ALLOWED_ROLES = {
    "Engineering Manager",
    "Production Manager",
}


class AUInvalidShiftExclusion(Document):
    pass


def make_shift_key(location, shift_date, shift, asset_name):
    identity = "|".join([
        str(location or "").strip().lower(),
        str(getdate(shift_date)),
        str(shift or "").strip().lower(),
        str(asset_name or "").strip().lower(),
    ])

    return hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()


def apply_invalid_shift_exclusions(rows):
    rows = [
        row for row in (rows or [])
        if isinstance(row, dict)
    ]

    if not rows:
        return rows

    locations = sorted({
        str(row.get("location") or "").strip()
        for row in rows
        if row.get("location")
    })

    dates = sorted({
        str(row.get("shift_date"))
        for row in rows
        if row.get("shift_date")
    })

    if not locations or not dates:
        return rows

    exclusions = frappe.get_all(
        "AU Invalid Shift Exclusion",
        filters={
            "status": "Active",
            "location": ["in", locations],
            "shift_date": ["between", [dates[0], dates[-1]]],
        },
        fields=[
            "name",
            "location",
            "shift_date",
            "shift",
            "asset_name",
            "exclusion_comment",
            "excluded_by",
            "excluded_on",
        ],
    )

    exclusion_map = {
        make_shift_key(
            row.location,
            row.shift_date,
            row.shift,
            row.asset_name,
        ): row
        for row in exclusions
    }

    for row in rows:
        key = make_shift_key(
            row.get("location"),
            row.get("shift_date"),
            row.get("shift"),
            row.get("asset_name"),
        )

        exclusion = exclusion_map.get(key)

        if exclusion and row.get("invalid_au"):
            row["invalid_au_excluded"] = 1
            row["invalid_au_exclusion"] = exclusion.name
            row["invalid_au_exclusion_comment"] = (
                exclusion.exclusion_comment
            )

    return rows


@frappe.whitelist()
def exclude_invalid_au_shift(
    location,
    shift_date,
    shift,
    asset_name,
    exclusion_comment,
    asset_category=None,
    company=None,
    work_hours=0,
    pbm_total_downtime=0,
    required_hours=0,
    invalid_reason=None,
):
    user_roles = set(
        frappe.get_roles(frappe.session.user)
    )

    if (
        frappe.session.user != "Administrator"
        and not user_roles.intersection(ALLOWED_ROLES)
    ):
        frappe.throw(
            "Only Engineering Managers and Production Managers "
            "may exclude an invalid A&U shift.",
            frappe.PermissionError,
        )

    location = str(location or "").strip()
    shift = str(shift or "").strip()
    asset_name = str(asset_name or "").strip()
    exclusion_comment = str(
        exclusion_comment or ""
    ).strip()

    if not location:
        frappe.throw("Site is required.")

    if not asset_name:
        frappe.throw("Machine is required.")

    if shift not in ("Day", "Night"):
        frappe.throw("Shift must be Day or Night.")

    if len(exclusion_comment) < 5:
        frappe.throw(
            "Please provide a meaningful exclusion comment."
        )

    shift_date = getdate(shift_date)

    shift_key = make_shift_key(
        location,
        shift_date,
        shift,
        asset_name,
    )

    existing = frappe.db.exists(
        "AU Invalid Shift Exclusion",
        {"shift_key": shift_key},
    )

    if existing:
        frappe.throw(
            f"This shift was already excluded in {existing}."
        )

    source_references = {}

    try:
        from engineering.engineering.report.availability_and_utilisation_engine.availability_and_utilisation_engine import (
            get_invalid_au_pbm_records,
        )

        source_references = get_invalid_au_pbm_records(
            asset_name=asset_name,
            location=location,
            shift_date=shift_date,
            shift=shift,
        )
    except Exception:
        frappe.clear_messages()

    doc = frappe.get_doc({
        "doctype": "AU Invalid Shift Exclusion",
        "location": location,
        "shift_date": shift_date,
        "shift": shift,
        "asset_name": asset_name,
        "asset_category": asset_category,
        "company": company,
        "work_hours": flt(work_hours),
        "pbm_total_downtime": flt(
            pbm_total_downtime
        ),
        "required_hours": flt(required_hours),
        "invalid_reason": str(
            invalid_reason or ""
        ).strip(),
        "exclusion_comment": exclusion_comment,
        "source_references": json.dumps(
            source_references,
            indent=2,
            default=str,
        ),
        "excluded_by": frappe.session.user,
        "excluded_on": now_datetime(),
        "status": "Active",
        "shift_key": shift_key,
    })

    doc.insert()
    frappe.db.commit()

    return {
        "name": doc.name,
        "message": (
            f"{asset_name} {shift_date} {shift} "
            "was permanently removed from Invalid A&U flags."
        ),
    }
