# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, today

BUCKETS = [
    ("overdue", "Overdue"),
    ("d0_7", "0–7"),
    ("d8_14", "8–14"),
    ("d15_21", "15–21"),
    ("d22_28", "22–28"),
]


def execute(filters=None):
    filters = filters or {}

    as_at = getdate(today())
    site = (filters.get("site") or "").strip() or None
    asset = (filters.get("asset") or "").strip() or None
    start_date = filters.get("start_date") or None
    end_date = filters.get("end_date") or None
    view = (filters.get("view") or "Summary").strip() or "Summary"
    bucket = (filters.get("bucket") or "").strip() or None

    if view == "Assets" and bucket:
        return _assets_view(as_at, site, asset, start_date, end_date, bucket)

    return _summary_view(as_at, site, asset, start_date, end_date)


def _where_sql(site=None, asset=None, start_date=None, end_date=None, table_alias="lr"):
    where = [
        f"{table_alias}.docstatus < 2",
        f"{table_alias}.expiry_date IS NOT NULL",
    ]
    params = {}

    if site:
        where.append(f"{table_alias}.site = %(site)s")
        params["site"] = site

    if asset:
        where.append(f"{table_alias}.fleet_number = %(asset)s")
        params["asset"] = asset

    if start_date:
        where.append(f"{table_alias}.expiry_date >= %(start_date)s")
        params["start_date"] = start_date

    if end_date:
        where.append(f"{table_alias}.expiry_date <= %(end_date)s")
        params["end_date"] = end_date

    return " AND ".join(where), params


def _latest_sql(where_sql):
    return f"""
        SELECT
            lr.site,
            lr.fleet_number,
            MAX(lr.expiry_date) AS expiry_date
        FROM `tabLicence Registration` lr
        WHERE {where_sql}
        GROUP BY lr.site, lr.fleet_number
    """


def _summary_view(as_at, site=None, asset=None, start_date=None, end_date=None):
    columns = [
        {"label": "Document", "fieldname": "document", "fieldtype": "Data", "width": 220},
        {"label": "🔴 Overdue", "fieldname": "overdue", "fieldtype": "Int", "width": 110},
        {"label": "🟠 0–7", "fieldname": "d0_7", "fieldtype": "Int", "width": 90},
        {"label": "🟡 8–14", "fieldname": "d8_14", "fieldtype": "Int", "width": 90},
        {"label": "🟦 15–21", "fieldname": "d15_21", "fieldtype": "Int", "width": 95},
        {"label": "🟩 22–28", "fieldname": "d22_28", "fieldtype": "Int", "width": 95},
    ]

    where_sql, params = _where_sql(site, asset, start_date, end_date)
    params["as_at"] = as_at
    latest_sql = _latest_sql(where_sql)

    data = frappe.db.sql(
        f"""
        WITH latest AS (
            {latest_sql}
        )
        SELECT
            'Licence Registration' AS document,
            SUM(CASE WHEN DATEDIFF(latest.expiry_date, %(as_at)s) < 0 THEN 1 ELSE 0 END) AS overdue,
            SUM(CASE WHEN DATEDIFF(latest.expiry_date, %(as_at)s) BETWEEN 0 AND 7 THEN 1 ELSE 0 END) AS d0_7,
            SUM(CASE WHEN DATEDIFF(latest.expiry_date, %(as_at)s) BETWEEN 8 AND 14 THEN 1 ELSE 0 END) AS d8_14,
            SUM(CASE WHEN DATEDIFF(latest.expiry_date, %(as_at)s) BETWEEN 15 AND 21 THEN 1 ELSE 0 END) AS d15_21,
            SUM(CASE WHEN DATEDIFF(latest.expiry_date, %(as_at)s) BETWEEN 22 AND 28 THEN 1 ELSE 0 END) AS d22_28
        FROM latest
        """,
        params,
        as_dict=True,
    )

    if not data:
        data = [{"document": "Licence Registration", "overdue": 0, "d0_7": 0, "d8_14": 0, "d15_21": 0, "d22_28": 0}]

    return columns, data, None, None


def _bucket_condition(bucket):
    if bucket == "overdue":
        return "DATEDIFF(latest.expiry_date, %(as_at)s) < 0"
    if bucket == "d0_7":
        return "DATEDIFF(latest.expiry_date, %(as_at)s) BETWEEN 0 AND 7"
    if bucket == "d8_14":
        return "DATEDIFF(latest.expiry_date, %(as_at)s) BETWEEN 8 AND 14"
    if bucket == "d15_21":
        return "DATEDIFF(latest.expiry_date, %(as_at)s) BETWEEN 15 AND 21"
    if bucket == "d22_28":
        return "DATEDIFF(latest.expiry_date, %(as_at)s) BETWEEN 22 AND 28"
    return "1 = 0"


def _assets_view(as_at, site=None, asset=None, start_date=None, end_date=None, bucket=None):
    columns = [
        {"label": "Fleet Number", "fieldname": "fleet_number", "fieldtype": "Link", "options": "Asset", "width": 130},
        {"label": "Site", "fieldname": "site", "fieldtype": "Link", "options": "Location", "width": 160},
        {"label": "Registration Number", "fieldname": "registration_number", "fieldtype": "Data", "width": 150},
        {"label": "Issue Date", "fieldname": "issue_date", "fieldtype": "Date", "width": 110},
        {"label": "Expiry Date", "fieldname": "expiry_date", "fieldtype": "Date", "width": 110},
        {"label": "Days Left", "fieldname": "days_left", "fieldtype": "Int", "width": 90},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 140},
        {"label": "Document", "fieldname": "document", "fieldtype": "Data", "width": 110},
    ]

    where_sql, params = _where_sql(site, asset, start_date, end_date)
    params["as_at"] = as_at
    latest_sql = _latest_sql(where_sql)
    bucket_sql = _bucket_condition(bucket)

    rows = frappe.db.sql(
        f"""
        WITH latest AS (
            {latest_sql}
        )
        SELECT
            lr.name,
            lr.site,
            lr.fleet_number,
            lr.registration_number,
            lr.issue_date,
            lr.expiry_date,
            DATEDIFF(lr.expiry_date, %(as_at)s) AS days_left,
            CASE
                WHEN DATEDIFF(lr.expiry_date, %(as_at)s) < 0 THEN 'Overdue'
                WHEN DATEDIFF(lr.expiry_date, %(as_at)s) BETWEEN 0 AND 7 THEN '0-7 days'
                WHEN DATEDIFF(lr.expiry_date, %(as_at)s) BETWEEN 8 AND 14 THEN '8-14 days'
                WHEN DATEDIFF(lr.expiry_date, %(as_at)s) BETWEEN 15 AND 21 THEN '15-21 days'
                WHEN DATEDIFF(lr.expiry_date, %(as_at)s) BETWEEN 22 AND 28 THEN '22-28 days'
                ELSE '-'
            END AS status,
            lr.attach
        FROM `tabLicence Registration` lr
        INNER JOIN latest
            ON latest.site = lr.site
            AND latest.fleet_number = lr.fleet_number
            AND latest.expiry_date = lr.expiry_date
        WHERE {bucket_sql}
        ORDER BY days_left ASC, lr.site ASC, lr.fleet_number ASC
        """,
        params,
        as_dict=True,
    )

    data = []
    for r in rows:
        data.append({
            "name": r.get("name"),
            "site": r.get("site"),
            "fleet_number": r.get("fleet_number"),
            "registration_number": r.get("registration_number"),
            "issue_date": r.get("issue_date"),
            "expiry_date": r.get("expiry_date"),
            "days_left": r.get("days_left"),
            "status": r.get("status"),
            "attach": r.get("attach"),
            "document": "Open",
        })

    return columns, data, None, None
