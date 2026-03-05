# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

# import frappe



import frappe
from frappe.utils import getdate, today


NO_EXPIRY_SECTIONS = (
    "Machine Service Records",
    "Service Schedule",
    "Wearcheck",
)

BUCKETS = [
    ("overdue", "Overdue", None, -1),     # < 0
    ("d0_7", "0–7", 0, 7),
    ("d8_14", "8–14", 8, 14),
    ("d15_21", "15–21", 15, 21),
    ("d22_28", "22–28", 22, 28),
]


def execute(filters=None):
    filters = filters or {}

    as_at = getdate(filters.get("as_at_date") or today())
    site = (filters.get("site") or "").strip() or None
    section = (filters.get("section") or "").strip() or None
    view = (filters.get("view") or "Summary").strip() or "Summary"
    bucket = (filters.get("bucket") or "").strip() or None

    # Click behaviour:
    # - Summary view (default): show section rows + bucket counts
    # - Assets view: show list of assets inside one chosen bucket (and optional section)
    if view == "Assets" and bucket:
        return _assets_view(as_at, site, section, bucket)

    return _summary_view(as_at, site, section)


def _base_latest_expiry_sql(where_sql: str) -> str:
    """
    One "current" legal per Asset+Section+Site = MAX(expiry_date)
    (Renewals push expiry forward; this is what should drive due/overdue.)
    """
    return f"""
        SELECT
            el.site,
            el.sections AS section,
            el.fleet_number AS asset,
            MAX(el.expiry_date) AS expiry_date
        FROM `tabEngineering Legals` el
        WHERE
            el.expiry_date IS NOT NULL
            AND el.sections NOT IN %(no_expiry_sections)s
            {where_sql}
        GROUP BY el.site, el.sections, el.fleet_number
    """


def _summary_view(as_at, site, section):
    columns = [
        {"label": "Section", "fieldname": "section", "fieldtype": "Data", "width": 220},
        {"label": "🔴 Overdue", "fieldname": "overdue", "fieldtype": "Int", "width": 110},
        {"label": "🟠 0–7", "fieldname": "d0_7", "fieldtype": "Int", "width": 90},
        {"label": "🟡 8–14", "fieldname": "d8_14", "fieldtype": "Int", "width": 90},
        {"label": "🟩 15–21", "fieldname": "d15_21", "fieldtype": "Int", "width": 95},
        {"label": "🟦 22–28", "fieldname": "d22_28", "fieldtype": "Int", "width": 95},
    ]

    where = []
    params = {"no_expiry_sections": NO_EXPIRY_SECTIONS, "as_at": as_at}

    if site:
        where.append("AND el.site = %(site)s")
        params["site"] = site

    if section:
        where.append("AND el.sections = %(section)s")
        params["section"] = section

    latest_sql = _base_latest_expiry_sql("\n".join(where))

    # days_left = DATEDIFF(expiry_date, as_at)
    data = frappe.db.sql(
        f"""
        WITH latest AS (
            {latest_sql}
        )
        SELECT
            latest.section AS section,
            SUM(CASE WHEN DATEDIFF(latest.expiry_date, %(as_at)s) < 0 THEN 1 ELSE 0 END) AS overdue,
            SUM(CASE WHEN DATEDIFF(latest.expiry_date, %(as_at)s) BETWEEN 0 AND 7 THEN 1 ELSE 0 END) AS d0_7,
            SUM(CASE WHEN DATEDIFF(latest.expiry_date, %(as_at)s) BETWEEN 8 AND 14 THEN 1 ELSE 0 END) AS d8_14,
            SUM(CASE WHEN DATEDIFF(latest.expiry_date, %(as_at)s) BETWEEN 15 AND 21 THEN 1 ELSE 0 END) AS d15_21,
            SUM(CASE WHEN DATEDIFF(latest.expiry_date, %(as_at)s) BETWEEN 22 AND 28 THEN 1 ELSE 0 END) AS d22_28
        FROM latest
        GROUP BY latest.section
        ORDER BY latest.section
        """,
        params,
        as_dict=True,
    )

    return columns, data, None, None


def _assets_view(as_at, site, section, bucket):
    columns = [
        {"label": "Asset", "fieldname": "asset", "fieldtype": "Link", "options": "Asset", "width": 130},
        {"label": "Site", "fieldname": "site", "fieldtype": "Link", "options": "Location", "width": 120},
        {"label": "Section", "fieldname": "section", "fieldtype": "Data", "width": 170},
        {"label": "Expiry Date", "fieldname": "expiry_date", "fieldtype": "Date", "width": 110},
        {"label": "Days Left", "fieldname": "days_left", "fieldtype": "Int", "width": 90},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 80},
    ]

    where = []
    params = {
        "no_expiry_sections": NO_EXPIRY_SECTIONS,
        "as_at": as_at,
        "bucket": bucket,
    }

    if site:
        where.append("AND el.site = %(site)s")
        params["site"] = site

    if section:
        where.append("AND el.sections = %(section)s")
        params["section"] = section

    latest_sql = _base_latest_expiry_sql("\n".join(where))

    # bucket condition
    if bucket == "overdue":
        bucket_sql = "days_left < 0"
    elif bucket == "d0_7":
        bucket_sql = "days_left BETWEEN 0 AND 7"
    elif bucket == "d8_14":
        bucket_sql = "days_left BETWEEN 8 AND 14"
    elif bucket == "d15_21":
        bucket_sql = "days_left BETWEEN 15 AND 21"
    elif bucket == "d22_28":
        bucket_sql = "days_left BETWEEN 22 AND 28"
    else:
        # safety fallback -> show nothing
        bucket_sql = "1=0"

    data = frappe.db.sql(
        f"""
        WITH latest AS (
            {latest_sql}
        ),
        current AS (
            SELECT
                lm.asset,
                lm.site,
                lm.section,
                lm.expiry_date,
                MAX(el.start_date) AS start_date
            FROM latest lm
            JOIN `tabEngineering Legals` el
                ON el.site = lm.site
                AND el.sections = lm.section
                AND el.fleet_number = lm.asset
                AND el.expiry_date = lm.expiry_date
            GROUP BY lm.site, lm.section, lm.asset, lm.expiry_date
        ),
        due AS (
            SELECT
                current.asset,
                current.site,
                current.section,
                current.start_date,
                current.expiry_date,
                DATEDIFF(current.expiry_date, %(as_at)s) AS days_left
            FROM current
        ),
        flags AS (
            SELECT
                el.fleet_number AS asset,
                el.site,
                el.sections AS section,
                MAX(
                    CASE
                        WHEN el.start_date IS NOT NULL
                         AND el.start_date BETWEEN DATE_SUB(%(as_at)s, INTERVAL 20 DAY) AND %(as_at)s
                        THEN 1 ELSE 0
                    END
                ) AS has_recent
            FROM `tabEngineering Legals` el
            WHERE
                el.sections NOT IN %(no_expiry_sections)s
                {("\n".join(where))}
            GROUP BY el.site, el.sections, el.fleet_number
        )
        SELECT
            d.asset,
            d.site,
            d.section,
            d.start_date,
            d.expiry_date,
            d.days_left,
            CASE
                WHEN IFNULL(f.has_recent, 0) = 1 THEN '✅'
                ELSE '❌'
            END AS status
        FROM due d
        LEFT JOIN flags f
            ON f.site = d.site AND f.section = d.section AND f.asset = d.asset
        WHERE {bucket_sql}
        ORDER BY d.days_left ASC, d.section ASC, d.asset ASC
        """,
        params,
        as_dict=True,
    )

    # show a helpful title line in report (no extra status types)
    message = f"Assets view: Bucket={bucket}, As-at={as_at}"

    return columns, data, message, None