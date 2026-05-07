# Copyright (c) 2026
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_days, flt


SUPPORT_EQUIPMENT_CATEGORIES = [
    "Water Pump",
    "Lightning Plant",
    "Generator",
]


def execute(filters=None):
    filters = frappe._dict(filters or {})

    validate_filters(filters)

    dates = get_date_range(filters.from_date, filters.to_date)
    columns = get_columns(dates)
    data = get_data(filters, dates)

    return columns, data


def validate_filters(filters):
    if not filters.get("location"):
        frappe.throw("Site is required.")

    if not filters.get("from_date"):
        frappe.throw("From Date is required.")

    if not filters.get("to_date"):
        frappe.throw("To Date is required.")

    if getdate(filters.from_date) > getdate(filters.to_date):
        frappe.throw("From Date cannot be after To Date.")

    if filters.get("equipment_category"):
        if filters.equipment_category not in SUPPORT_EQUIPMENT_CATEGORIES:
            frappe.throw(f"Invalid Equipment Category: {filters.equipment_category}")


def get_date_range(from_date, to_date):
    dates = []
    current_date = getdate(from_date)
    end_date = getdate(to_date)

    while current_date <= end_date:
        dates.append(current_date)
        current_date = add_days(current_date, 1)

    return dates


def get_columns(dates):
    columns = [
        {
            "label": "Plant Number",
            "fieldname": "plant_number",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Asset",
            "fieldname": "asset_name",
            "fieldtype": "Link",
            "options": "Asset",
            "width": 120,
        },
        {
            "label": "Equipment Category",
            "fieldname": "equipment_category",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": "Model",
            "fieldname": "model",
            "fieldtype": "Data",
            "width": 160,
        },
    ]

    for date_value in dates:
        date_key = get_date_key(date_value)
        day_label = date_value.strftime("%A").upper()
        date_label = date_value.strftime("%d/%m/%Y")

        columns.extend([
            {
                "label": f"{day_label}<br>{date_label}<br>Day Open",
                "fieldname": f"{date_key}_day_open",
                "fieldtype": "Int",
                "width": 110,
            },
            {
                "label": f"{day_label}<br>{date_label}<br>Day Close",
                "fieldname": f"{date_key}_day_close",
                "fieldtype": "Int",
                "width": 110,
            },
            {
                "label": f"{day_label}<br>{date_label}<br>Day Total",
                "fieldname": f"{date_key}_day_total",
                "fieldtype": "Int",
                "width": 110,
            },
            {
                "label": f"{day_label}<br>{date_label}<br>Night Open",
                "fieldname": f"{date_key}_night_open",
                "fieldtype": "Int",
                "width": 110,
            },
            {
                "label": f"{day_label}<br>{date_label}<br>Night Close",
                "fieldname": f"{date_key}_night_close",
                "fieldtype": "Int",
                "width": 110,
            },
            {
                "label": f"{day_label}<br>{date_label}<br>Night Total",
                "fieldname": f"{date_key}_night_total",
                "fieldtype": "Int",
                "width": 110,
            },
            {
                "label": f"{day_label}<br>{date_label}<br>Full Day Total",
                "fieldname": f"{date_key}_daily_total",
                "fieldtype": "Int",
                "width": 130,
            },
        ])

    return columns


def get_data(filters, dates):
    records = get_support_equipment_records(filters)
    asset_map = {}

    for record in records:
        asset_name = record.get("asset_name")

        if not asset_name:
            continue

        if asset_name not in asset_map:
            asset_map[asset_name] = get_empty_asset_row(record, dates)

        row = asset_map[asset_name]
        date_key = get_date_key(record.shift_date)
        shift_key = get_shift_key(record.shift)

        if not shift_key:
            continue

        row[f"{date_key}_{shift_key}_open"] = to_whole_number(record.engine_start_hours)
        row[f"{date_key}_{shift_key}_close"] = to_whole_number(record.engine_end_hours)
        row[f"{date_key}_{shift_key}_total"] = to_whole_number(record.working_hours)

        day_total = flt(row.get(f"{date_key}_day_total"))
        night_total = flt(row.get(f"{date_key}_night_total"))

        row[f"{date_key}_daily_total"] = to_whole_number(day_total + night_total)

    return sorted(
        asset_map.values(),
        key=lambda d: (
            d.get("equipment_category") or "",
            d.get("plant_number") or "",
            d.get("asset_name") or "",
        ),
    )


def get_support_equipment_records(filters):
    conditions = [
        "parent.location = %(location)s",
        "parent.shift_date between %(from_date)s and %(to_date)s",
        "parent.docstatus < 2",
    ]

    values = {
        "location": filters.location,
        "from_date": filters.from_date,
        "to_date": filters.to_date,
    }

    if filters.get("equipment_category"):
        conditions.append("child.equipment_category = %(equipment_category)s")
        values["equipment_category"] = filters.equipment_category
    else:
        conditions.append("child.equipment_category in %(support_categories)s")
        values["support_categories"] = tuple(SUPPORT_EQUIPMENT_CATEGORIES)

    where_clause = " and ".join(conditions)

    return frappe.db.sql(
        f"""
        select
            parent.name as parent_name,
            parent.shift_date,
            parent.shift,
            child.asset_name,
            child.plant_number,
            child.equipment_category,
            child.model,
            child.engine_start_hours,
            child.engine_end_hours,
            child.working_hours
        from `tabSupport Equipment` parent
        inner join `tabSupport Equipment Assets` child
            on child.parent = parent.name
        where {where_clause}
        order by
            child.equipment_category asc,
            child.plant_number asc,
            parent.shift_date asc,
            parent.shift asc
        """,
        values,
        as_dict=True,
    )


def get_empty_asset_row(record, dates):
    row = {
        "plant_number": record.get("plant_number"),
        "asset_name": record.get("asset_name"),
        "equipment_category": record.get("equipment_category"),
        "model": record.get("model"),
    }

    for date_value in dates:
        date_key = get_date_key(date_value)

        row[f"{date_key}_day_open"] = 0
        row[f"{date_key}_day_close"] = 0
        row[f"{date_key}_day_total"] = 0

        row[f"{date_key}_night_open"] = 0
        row[f"{date_key}_night_close"] = 0
        row[f"{date_key}_night_total"] = 0

        row[f"{date_key}_daily_total"] = 0

    return row


def get_date_key(date_value):
    return getdate(date_value).strftime("%Y_%m_%d")


def get_shift_key(shift):
    if not shift:
        return None

    shift = shift.strip().lower()

    if shift == "day":
        return "day"

    if shift == "night":
        return "night"

    return None


def to_whole_number(value):
    if value in [None, ""]:
        return 0

    return int(round(flt(value), 0))