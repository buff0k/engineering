# Copyright (c) 2025, Isambane Mining (Pty) Ltd
# For license information, please see license.txt

import frappe

def execute(filters=None):
    # Define columns for the report
    columns = [
        {"label": "Updated By", "fieldname": "update_by", "fieldtype": "Data", "width": 150},
        {"label": "Datetime", "fieldname": "update_date_time", "fieldtype": "Date", "width": 120},
        {"label": "Location", "fieldname": "location", "fieldtype": "Data", "width": 150},
        {"label": "Asset Name", "fieldname": "asset_name", "fieldtype": "Data", "width": 150},
        {"label": "Breakdown Start Hours", "fieldname": "breakdown_start_hours", "fieldtype": "Float", "width": 150},
        {"label": "Breakdown Reason Updates", "fieldname": "breakdown_reason_updates", "fieldtype": "Text", "width": 250},
        {"label": "Breakdown Start Time", "fieldname": "breakdown_start_time", "fieldtype": "Datetime", "width": 180},
        {"label": "Workshop Action", "fieldname": "workshop_action", "fieldtype": "Text", "width": 250},
        {"label": "Workshop Start Time", "fieldname": "workshop_start_time", "fieldtype": "Datetime", "width": 180},
        {"label": "Resolution", "fieldname": "resolution", "fieldtype": "Text", "width": 250},
        {"label": "Timeclock", "fieldname": "timeclock", "fieldtype": "Float", "width": 150},
        {"label": "Breakdown Resolved", "fieldname": "breakdown_resolved", "fieldtype": "Check", "width": 150},
    ]

    # Fetch data from the Plant Breakdown doctype
    data = frappe.db.sql("""
        SELECT 
            name,
            owner AS update_by,
            breakdown_start_datetime,
            location,
            asset_name,
            breakdown_reason,
            workshop_action,
            resolution_summary,
            hours_breakdown_starts,
            breakdown_hours,
            workshop_start_datetime,
            resolved_datetime
        FROM 
            `tabPlant Breakdown`
        ORDER BY 
            breakdown_start_datetime DESC
    """, as_dict=True)

    # Prepare rows with conditional logic
    result = []
    for d in data:
        # Date only (no time)
        date_only = None
        if d.get("breakdown_start_datetime"):
            date_only = d.breakdown_start_datetime.date()

        # Breakdown Reason Updates (priority order)
        breakdown_reason_updates = (
            d.resolution_summary
            or d.workshop_action
            or d.breakdown_reason
            or ""
        )

        # Check if breakdown is resolved (real-time)
        breakdown_resolved = 1 if (d.get("resolved_datetime") or d.get("resolution_summary")) else 0

        result.append({
            "update_by": d.update_by,
            "update_date_time": date_only,
            "location": d.location,
            "asset_name": d.asset_name,
            "breakdown_reason_updates": breakdown_reason_updates,
            "workshop_action": d.workshop_action,
            "breakdown_start_time": d.breakdown_start_datetime,
            "workshop_start_time": d.workshop_start_datetime,
            "breakdown_start_hours": d.hours_breakdown_starts,
            "timeclock": d.breakdown_hours,
            "resolution": d.resolution_summary,
            "breakdown_resolved": breakdown_resolved
        })

    return columns, result
