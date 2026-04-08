import calendar
from datetime import datetime

import frappe


def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)
    summary = get_report_summary(data)

    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": "Date", "fieldname": "report_datetime_display", "fieldtype": "Data", "width": 145},
        {"label": "Site", "fieldname": "site", "fieldtype": "Data", "width": 105},
        {"label": "Fleet", "fieldname": "fleet_number", "fieldtype": "Data", "width": 82},
        {"label": "Operator", "fieldname": "reported_by_name_and_surname", "fieldtype": "Data", "width": 210},
        {"label": "Deviation", "fieldname": "deviation_details", "fieldtype": "Data", "width": 120},
        {"label": "Action", "fieldname": "resolution_summary", "fieldtype": "Data", "width": 135},
        {"label": "Actioned By", "fieldname": "actioned_by_name_and_surname", "fieldtype": "Data", "width": 210},
        {"label": "Operating Status", "fieldname": "operating_status_badge", "fieldtype": "Data", "width": 205},
        {"label": "Status", "fieldname": "action_status_badge", "fieldtype": "Data", "width": 90},
        {"label": "Action Time", "fieldname": "action_date_and_time_display", "fieldtype": "Data", "width": 145},
        {"label": "Comp %", "fieldname": "completion_percentage_badge", "fieldtype": "Data", "width": 84}
    ]


def get_data(filters):
    conditions = []
    values = {}

    if filters.get("site") and filters.get("site") != "All Sites":
        conditions.append("site = %(site)s")
        values["site"] = filters.get("site")

    if filters.get("fleet_number"):
        conditions.append("fleet_number = %(fleet_number)s")
        values["fleet_number"] = filters.get("fleet_number")

    if filters.get("operating_status") and filters.get("operating_status") != "All Statuses":
        conditions.append("operating_status = %(operating_status)s")
        values["operating_status"] = filters.get("operating_status")

    if filters.get("action_status"):
        conditions.append("action_status = %(action_status)s")
        values["action_status"] = filters.get("action_status")

    if filters.get("month") and filters.get("year"):
        month_number = list(calendar.month_name).index(filters.get("month"))
        conditions.append("MONTH(report_datetime) = %(month)s")
        conditions.append("YEAR(report_datetime) = %(year)s")
        values["month"] = month_number
        values["year"] = int(filters.get("year"))
    elif filters.get("year"):
        conditions.append("YEAR(report_datetime) = %(year)s")
        values["year"] = int(filters.get("year"))

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    records = frappe.db.sql(
        f"""
        SELECT
            report_datetime,
            site,
            fleet_number,
            reported_by_name_and_surname,
            deviation_details,
            resolution_summary,
            actioned_by_name_and_surname,
            operating_status,
            action_status,
            action_date_and_time,
            completion_percentage
        FROM `tabPre Use Deviation`
        {where_clause}
        ORDER BY report_datetime DESC, creation DESC
        """,
        values=values,
        as_dict=True
    )

    for row in records:
        pct = row.get("completion_percentage")
        if pct is None:
            pct = 100 if row.get("action_date_and_time") else 0

        pct = int(round(flt(pct), 0))

        row["completion_percentage"] = pct
        row["completion_percentage_badge"] = f"{pct}%"
        row["action_status_badge"] = row.get("action_status") or ""
        row["operating_status_badge"] = row.get("operating_status") or ""

        row["report_datetime_display"] = format_dt_short(row.get("report_datetime"))
        row["action_date_and_time_display"] = format_dt_short(row.get("action_date_and_time"))

        row["site"] = str(row.get("site") or "")
        row["fleet_number"] = str(row.get("fleet_number") or "")
        row["reported_by_name_and_surname"] = str(row.get("reported_by_name_and_surname") or "")
        row["deviation_details"] = str(row.get("deviation_details") or "")
        row["resolution_summary"] = str(row.get("resolution_summary") or "")
        row["actioned_by_name_and_surname"] = str(row.get("actioned_by_name_and_surname") or "")

    return records


def get_chart_data(data):
    open_count = len([d for d in data if d.get("action_status") == "Open"])
    closed_count = len([d for d in data if d.get("action_status") == "Closed"])

    return {
        "data": {
            "labels": ["Open", "Closed"],
            "datasets": [
                {
                    "name": "Status",
                    "values": [open_count, closed_count]
                }
            ]
        },
        "type": "donut",
        "height": 220,
        "colors": ["#f97316", "#22c55e"]
    }


def get_report_summary(data):
    total_records = len(data)

    avg_completion = 0
    if total_records:
        avg_completion = sum([flt(d.get("completion_percentage", 0)) for d in data]) / total_records

    avg_completion = int(round(avg_completion, 0))

    return [
        {
            "value": f"{avg_completion}%",
            "label": "Average Completion",
            "datatype": "Data",
            "indicator": "Blue"
        }
    ]


@frappe.whitelist()
def get_site_options():
    sites = frappe.db.sql(
        """
        SELECT DISTINCT site
        FROM `tabPre Use Deviation`
        WHERE IFNULL(site, '') != ''
        ORDER BY site
        """,
        as_dict=True
    )

    options = ["All Sites"]
    options.extend([d.site for d in sites if d.site])
    return "\n".join(options)


@frappe.whitelist()
def get_operating_status_options():
    statuses = frappe.db.sql(
        """
        SELECT DISTINCT operating_status
        FROM `tabPre Use Deviation`
        WHERE IFNULL(operating_status, '') != ''
        ORDER BY operating_status
        """,
        as_dict=True
    )

    options = ["All Statuses"]
    options.extend([d.operating_status for d in statuses if d.operating_status])
    return "\n".join(options)


def format_dt_short(value):
    if not value:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%d-%m-%y %H:%M")

    text = str(value).replace("T", " ")
    try:
        dt = datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d-%m-%y %H:%M")
    except Exception:
        return text[:14]


def flt(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0