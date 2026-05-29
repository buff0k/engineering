# Copyright (c) 2026, Isambane Mining (Pty) Ltd
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, now_datetime
from datetime import datetime, time, timedelta


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 110},
        {"label": _("Site"), "fieldname": "site", "fieldtype": "Link", "options": "Location", "width": 130},
        {"label": _("Plant No."), "fieldname": "plant_no", "fieldtype": "Link", "options": "Asset", "width": 130},
        {"label": _("Breakdown/Maintenance Reason"), "fieldname": "breakdown_reason", "fieldtype": "Small Text", "width": 260},
        {"label": _("Resolution Summary"), "fieldname": "resolution_summary", "fieldtype": "Small Text", "width": 210},
        {"label": _("Breakdown/Maintenance Start Time"), "fieldname": "breakdown_start_datetime", "fieldtype": "Datetime", "width": 230},
        {"label": _("Datetime back in production"), "fieldname": "resolved_datetime", "fieldtype": "Datetime", "width": 210},
        {"label": _("Breakdown/Maintenance Hours"), "fieldname": "breakdown_hours", "fieldtype": "Float", "precision": 2, "width": 210},
        {"label": _("Open/Closed"), "fieldname": "open_closed", "fieldtype": "Data", "width": 120},
    ]


def get_data(filters):
    start_date = getdate(filters.get("start_date")) if filters.get("start_date") else getdate(now_datetime())
    end_date = getdate(filters.get("end_date")) if filters.get("end_date") else start_date

    report_start_datetime = datetime.combine(start_date, time.min)
    report_end_datetime = datetime.combine(end_date + timedelta(days=1), time.min)

    conditions = [
        "pbm.breakdown_start_datetime is not null",
        "pbm.breakdown_start_datetime < %(report_end_datetime)s",
        "(pbm.resolved_datetime is null or pbm.resolved_datetime > %(report_start_datetime)s)"
    ]

    values = {
        "report_start_datetime": report_start_datetime,
        "report_end_datetime": report_end_datetime,
    }

    if filters.get("site"):
        conditions.append("pbm.location = %(site)s")
        values["site"] = filters.site

    if filters.get("asset_category"):
        conditions.append("pbm.asset_category = %(asset_category)s")
        values["asset_category"] = filters.asset_category

    if filters.get("shift"):
        conditions.append("pbm.shift = %(shift)s")
        values["shift"] = filters.shift

    rows = frappe.db.sql(
        f"""
        select
            pbm.name,
            pbm.location as site,
            pbm.asset_name as plant_no,
            pbm.breakdown_reason as breakdown_reason,
            pbm.resolution_summary as resolution_summary,
            pbm.breakdown_start_datetime as breakdown_start_datetime,
            pbm.resolved_datetime as resolved_datetime,
            pbm.open_closed as open_closed,
            pbm.modified as modified
        from `tabPlant Breakdown or Maintenance` pbm
        where {" and ".join(conditions)}
        order by pbm.breakdown_start_datetime desc, pbm.modified desc
        """,
        values,
        as_dict=True,
    )

    data = []
    current_datetime = now_datetime()

    for row in rows:
        breakdown_start = get_datetime(row.breakdown_start_datetime)
        resolved_datetime = get_datetime(row.resolved_datetime) if row.resolved_datetime else None

        actual_end = resolved_datetime or current_datetime

        current_day = start_date
        while current_day <= end_date:
            day_start = datetime.combine(current_day, time.min)
            day_end = day_start + timedelta(days=1)

            downtime_start = max(breakdown_start, day_start)
            downtime_end = min(actual_end, day_end)

            if downtime_start < downtime_end:
                hours = round((downtime_end - downtime_start).total_seconds() / 3600, 2)

                if hours > 24:
                    hours = 24

                if resolved_datetime and resolved_datetime <= day_end:
                    open_closed = "Closed"
                else:
                    open_closed = "Open"

                data.append({
                    "date": current_day,
                    "site": row.site,
                    "plant_no": row.plant_no,
                    "breakdown_reason": row.breakdown_reason,
                    "resolution_summary": row.resolution_summary,
                    "breakdown_start_datetime": row.breakdown_start_datetime,
                    "resolved_datetime": row.resolved_datetime,
                    "breakdown_hours": hours,
                    "open_closed": open_closed,
                })

            current_day = current_day + timedelta(days=1)

    data.sort(key=lambda d: (d.get("date"), d.get("breakdown_start_datetime")), reverse=True)

    return data
