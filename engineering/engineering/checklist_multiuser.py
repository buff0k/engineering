import calendar
import re

import frappe
from frappe.utils import flt


ALLOWED_PARENT_DOCTYPES = {
    "Engineering Checklist Register",
    "Engineering LDV Checklist Register",
}

CHILD_DOCTYPE = "Engineering Checklist Register Row"


def _normalize_text(value):
    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def _status_fields():
    result = []
    meta = frappe.get_meta(CHILD_DOCTYPE)

    for df in meta.fields:
        fieldname = (df.fieldname or "").strip()
        label = (df.label or "").strip()
        search_text = f"{label} {fieldname}".lower()

        if df.fieldtype != "Select" or not fieldname:
            continue

        if "day" not in search_text and "night" not in search_text:
            continue

        match = re.search(r"(\d+)", f"{label} {fieldname}")
        day_number = int(match.group(1)) if match else None

        result.append((fieldname, day_number, df))

    return result


def _days_in_month(month, year):
    month_map = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }

    month_number = month_map.get(
        _normalize_text(month).lower()
    )

    try:
        year_number = int(year)
    except (TypeError, ValueError):
        return 31

    if not month_number:
        return 31

    return calendar.monthrange(
        year_number,
        month_number
    )[1]


def _is_submitted(value):
    return _normalize_text(value).lower() in {
        "submitted",
        "late submission",
    }


def _row_submission(register_doc, row_name):
    days_in_month = _days_in_month(
        register_doc.month,
        register_doc.year,
    )

    active_fields = [
        fieldname
        for fieldname, day_number, _df in _status_fields()
        if day_number
        and day_number <= days_in_month
    ]

    total_target = days_in_month * 2

    if not total_target or not active_fields:
        return 0.0

    values = frappe.db.get_value(
        CHILD_DOCTYPE,
        row_name,
        active_fields,
        as_dict=True,
    ) or {}

    selected_count = sum(
        1
        for fieldname in active_fields
        if _is_submitted(
            values.get(fieldname)
        )
    )

    return round(
        (selected_count / total_target) * 100,
        1,
    )


def _average(parent_doctype, register_name):
    rows = frappe.get_all(
        CHILD_DOCTYPE,
        filters={
            "parent": register_name,
            "parenttype": parent_doctype,
        },
        fields=[
            "checklist_submission",
        ],
        limit_page_length=0,
    )

    if not rows:
        return "0.0%"

    average = (
        sum(
            flt(row.get("checklist_submission"))
            for row in rows
        )
        / len(rows)
    )

    return f"{average:.1f}%"


@frappe.whitelist()
def update_checklist_cell(
    parent_doctype,
    register_name,
    row_name,
    fieldname,
    value=None,
):
    """
    Save only one checklist Day/Night cell.

    This avoids saving the user's complete stale copy
    of the monthly register.
    """

    if parent_doctype not in ALLOWED_PARENT_DOCTYPES:
        frappe.throw(
            "This register does not support "
            "multi-user checklist saving."
        )

    if (
        not register_name
        or not row_name
        or not fieldname
    ):
        frappe.throw(
            "Register, row and field are required."
        )

    register_doc = frappe.get_doc(
        parent_doctype,
        register_name,
    )

    register_doc.check_permission("write")

    # Lock only this monthly register for the very short
    # duration of one cell update.
    #
    # This serializes simultaneous updates so calculated
    # percentages cannot race against each other.
    frappe.db.sql(
        f"""
        SELECT name
        FROM `tab{parent_doctype}`
        WHERE name=%s
        FOR UPDATE
        """,
        (register_name,),
    )

    row_link = frappe.db.get_value(
        CHILD_DOCTYPE,
        row_name,
        [
            "parent",
            "parenttype",
            "parentfield",
        ],
        as_dict=True,
    )

    if not row_link:
        frappe.throw(
            "Checklist row was not found. "
            "Please reload the register."
        )

    if (
        row_link.get("parent") != register_name
        or row_link.get("parenttype")
        != parent_doctype
    ):
        frappe.throw(
            "This checklist row does not belong "
            "to the selected register."
        )

    allowed_fields = {
        status_fieldname: df
        for (
            status_fieldname,
            _day_number,
            df,
        ) in _status_fields()
    }

    if fieldname not in allowed_fields:
        frappe.throw(
            "Only Day/Night checklist status "
            "fields can be saved this way."
        )

    clean_value = _normalize_text(value)

    df = allowed_fields[fieldname]

    allowed_values = [
        option.strip()
        for option in (
            df.options or ""
        ).splitlines()
        if option.strip()
    ]

    if (
        clean_value
        and allowed_values
        and clean_value not in allowed_values
    ):
        frappe.throw(
            f"Invalid checklist status: "
            f"{clean_value}"
        )

    # IMPORTANT:
    #
    # Only this exact cell is updated.
    #
    # We deliberately do NOT save the complete parent
    # document because another user may have changed
    # other checklist cells since this browser loaded.
    frappe.db.set_value(
        CHILD_DOCTYPE,
        row_name,
        fieldname,
        clean_value,
        update_modified=False,
    )

    row_submission = _row_submission(
        register_doc,
        row_name,
    )

    if frappe.get_meta(
        CHILD_DOCTYPE
    ).has_field(
        "checklist_submission"
    ):
        frappe.db.set_value(
            CHILD_DOCTYPE,
            row_name,
            "checklist_submission",
            row_submission,
            update_modified=False,
        )

    average = _average(
        parent_doctype,
        register_name,
    )

    if frappe.get_meta(
        parent_doctype
    ).has_field(
        "checklist_submission_average"
    ):
        frappe.db.set_value(
            parent_doctype,
            register_name,
            "checklist_submission_average",
            average,
            update_modified=True,
        )

    modified = frappe.db.get_value(
        parent_doctype,
        register_name,
        "modified",
    )

    return {
        "row_name": row_name,
        "fieldname": fieldname,
        "value": clean_value,
        "row_submission": row_submission,
        "checklist_submission_average": average,
        "modified": modified,
    }
