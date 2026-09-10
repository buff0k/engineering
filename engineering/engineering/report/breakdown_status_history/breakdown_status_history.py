# Copyright (c) 2025, Isambane Mining (Pty) Ltd
# For license information, please see license.txt

import frappe
from frappe.utils import getdate


DOCTYPE = "Plant Breakdown or Maintenance"


def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = [
        {
            "label": "Updated By",
            "fieldname": "update_by",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Datetime",
            "fieldname": "update_date_time",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "Location",
            "fieldname": "location",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Asset Name",
            "fieldname": "asset_name",
            "fieldtype": "Link",
            "options": "Asset",
            "width": 150,
        },
        {
            "label": "Breakdown Start Hours",
            "fieldname": "breakdown_start_hours",
            "fieldtype": "Float",
            "width": 150,
        },
        {
            "label": "Breakdown Reason Updates",
            "fieldname": "breakdown_reason_updates",
            "fieldtype": "Text",
            "width": 250,
        },
        {
            "label": "Breakdown Start Time",
            "fieldname": "breakdown_start_time",
            "fieldtype": "Datetime",
            "width": 180,
        },
        {
            "label": "Workshop Action",
            "fieldname": "workshop_action",
            "fieldtype": "Text",
            "width": 250,
        },
        {
            "label": "Workshop Start Time",
            "fieldname": "workshop_start_time",
            "fieldtype": "Datetime",
            "width": 180,
        },
        {
            "label": "Resolution",
            "fieldname": "resolution",
            "fieldtype": "Text",
            "width": 250,
        },
        {
            "label": "Timeclock",
            "fieldname": "timeclock",
            "fieldtype": "Float",
            "width": 150,
        },
        {
            "label": "Breakdown Resolved",
            "fieldname": "breakdown_resolved",
            "fieldtype": "Check",
            "width": 150,
        },
    ]

    meta = frappe.get_meta(DOCTYPE)

    def has_field(fieldname):
        return bool(meta.get_field(fieldname))

    optional_fields = [
        "breakdown_start_datetime",
        "location",
        "asset_name",
        "breakdown_reason",
        "resolution_summary",
        "breakdown_hours",
        "resolved_datetime",
        "open_closed",
        "hours_breakdown_starts",
        "workshop_action",
        "workshop_start_datetime",
        "mechanic_breakdown_maintenance_start_time",
    ]

    db_fields = ["name", "owner"]

    for fieldname in optional_fields:
        if has_field(fieldname):
            db_fields.append(fieldname)

    db_filters = []

    if filters.get("location") and has_field("location"):
        db_filters.append(
            ["location", "=", filters.location]
        )

    if filters.get("asset_name") and has_field("asset_name"):
        db_filters.append(
            ["asset_name", "=", filters.asset_name]
        )

    if filters.get("from_date") and has_field("breakdown_start_datetime"):
        db_filters.append(
            [
                "breakdown_start_datetime",
                ">=",
                str(filters.from_date) + " 00:00:00",
            ]
        )

    if filters.get("to_date") and has_field("breakdown_start_datetime"):
        db_filters.append(
            [
                "breakdown_start_datetime",
                "<=",
                str(filters.to_date) + " 23:59:59",
            ]
        )

    order_by = (
        "breakdown_start_datetime desc"
        if has_field("breakdown_start_datetime")
        else "modified desc"
    )

    data = frappe.get_all(
        DOCTYPE,
        fields=db_fields,
        filters=db_filters,
        order_by=order_by,
    )

    result = []

    for d in data:
        start_datetime = d.get("breakdown_start_datetime")
        date_only = getdate(start_datetime) if start_datetime else None

        workshop_start = (
            d.get("mechanic_breakdown_maintenance_start_time")
            or d.get("workshop_start_datetime")
        )

        workshop_action = d.get("workshop_action") or ""

        breakdown_reason_updates = (
            d.get("resolution_summary")
            or workshop_action
            or d.get("breakdown_reason")
            or ""
        )

        breakdown_resolved = 1 if (
            d.get("resolved_datetime")
            or d.get("resolution_summary")
            or d.get("open_closed") == "Closed"
        ) else 0

        result.append(
            {
                "update_by": d.get("owner"),
                "update_date_time": date_only,
                "location": d.get("location"),
                "asset_name": d.get("asset_name"),
                "breakdown_start_hours": (
                    d.get("hours_breakdown_starts")
                    if has_field("hours_breakdown_starts")
                    else None
                ),
                "breakdown_reason_updates": breakdown_reason_updates,
                "breakdown_start_time": start_datetime,
                "workshop_action": workshop_action,
                "workshop_start_time": workshop_start,
                "resolution": d.get("resolution_summary"),
                "timeclock": d.get("breakdown_hours"),
                "breakdown_resolved": breakdown_resolved,
            }
        )

    return columns, result
