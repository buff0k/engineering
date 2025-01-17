# Copyright (c) 2025, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    columns, data = [], []

    # Define columns
    columns = [
        {"label": _("Location"), "fieldname": "location", "fieldtype": "Data", "width": 120},
        {"label": _("Shift Date"), "fieldname": "shift_date", "fieldtype": "Date", "width": 100},
        {"label": _("Shift"), "fieldname": "shift", "fieldtype": "Data", "width": 80},
        {"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 150},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 120},
        {"label": _("Pre-Use Link"), "fieldname": "pre_use_link", "fieldtype": "Link", "options": "Pre-Use Hours", "width": 120},
        {"label": _("Shift System"), "fieldname": "shift_system", "fieldtype": "Data", "width": 100},
        {"label": _("Shift Required Hours"), "fieldname": "shift_required_hours", "fieldtype": "Float", "width": 100},
        {"label": _("Shift Start Hours"), "fieldname": "shift_start_hours", "fieldtype": "Float", "width": 100},
        {"label": _("Shift End Hours"), "fieldname": "shift_end_hours", "fieldtype": "Float", "width": 100},
        {"label": _("Shift Working Hours"), "fieldname": "shift_working_hours", "fieldtype": "Float", "width": 120},
        {"label": _("Shift Breakdown Hours"), "fieldname": "shift_breakdown_hours", "fieldtype": "Float", "width": 120},
        {"label": _("Shift Available Hours"), "fieldname": "shift_available_hours", "fieldtype": "Float", "width": 120},
        {"label": _("Plant Shift Availability"), "fieldname": "plant_shift_availability", "fieldtype": "Percent", "width": 150},
        {"label": _("Plant Shift Utilisation"), "fieldname": "plant_shift_utilisation", "fieldtype": "Percent", "width": 150},
    ]

    # Fetch data
    conditions = ""
    if filters.get("date_from"):
        conditions += f" AND shift_date >= '{filters['date_from']}'"
    if filters.get("date_to"):
        conditions += f" AND shift_date <= '{filters['date_to']}'"
    if filters.get("location"):
        conditions += f" AND location = '{filters['location']}'"
    if filters.get("asset_name"):
        conditions += f" AND asset_name = '{filters['asset_name']}'"

    query = f"""
        SELECT 
            location, shift_date, shift, asset_name, item_name, pre_use_link, shift_system,
            shift_required_hours, shift_start_hours, shift_end_hours,
            shift_working_hours, shift_breakdown_hours, shift_available_hours,
            plant_shift_availability, plant_shift_utilisation
        FROM `tabAvailability and Utilisation`
        WHERE 1=1
        {conditions}
        ORDER BY asset_name, shift_date
    """

    records = frappe.db.sql(query, as_dict=True)

    # Group data by asset_name
    grouped_data = {}
    for record in records:
        grouped_data.setdefault(record['asset_name'], []).append(record)

    # Process grouped data with totals at each level
    for asset_name, rows in grouped_data.items():
        total_working_hours = sum(row["shift_working_hours"] for row in rows if row["shift_working_hours"])
        total_available_hours = sum(row["shift_available_hours"] for row in rows if row["shift_available_hours"])
        total_required_hours = sum(row["shift_required_hours"] for row in rows if row["shift_required_hours"])

        avg_availability = (total_available_hours / total_required_hours * 100) if total_required_hours > 0 else 0
        avg_utilisation = (total_working_hours / total_required_hours * 100) if total_required_hours > 0 else 0

        # Add rows for the asset group
        data.extend(rows)

        # Add totals for the group
        data.append({
            "location": _("Total for ") + asset_name,
            "shift_working_hours": total_working_hours,
            "shift_available_hours": total_available_hours,
            "shift_required_hours": total_required_hours,
            "plant_shift_availability": avg_availability,
            "plant_shift_utilisation": avg_utilisation,
        })

    return columns, data
