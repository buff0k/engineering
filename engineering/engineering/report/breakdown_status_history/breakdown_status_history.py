# Copyright (c) 2024, Isambane Mining (Pty) Ltd and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    # Define columns for fields in the Breakdown History child table only
    columns = [
        {"label": "Updated By", "fieldname": "update_by", "fieldtype": "Data", "width": 150},
        {"label": "Date", "fieldname": "date", "fieldtype": "Datetime", "width": 150},
        {"label": "Location", "fieldname": "location", "fieldtype": "Data", "width": 150},
        {"label": "Asset Name", "fieldname": "asset_name", "fieldtype": "Data", "width": 150},
        {"label": "Breakdown Reason Updates", "fieldname": "breakdown_reason_updates", "fieldtype": "Text", "width": 200},
        {"label": "Breakdown Status", "fieldname": "breakdown_status", "fieldtype": "Data", "width": 150},
        {"label": "Breakdown Start Hours", "fieldname": "breakdown_start_hours", "fieldtype": "Float", "width": 150}
    ]

    # Fetch data from Breakdown History child table only, ordered by Date
    data = frappe.db.sql("""
        SELECT 
            bh.update_by, bh.date, bh.location, bh.asset_name,
            bh.breakdown_reason_updates, bh.breakdown_status, bh.breakdown_start_hours
        FROM 
            `tabBreakdown History` AS bh
        ORDER BY 
            bh.date DESC
    """, as_dict=True)

    return columns, data
