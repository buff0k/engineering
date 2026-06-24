# Copyright (c) 2025, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from datetime import timedelta
from frappe.utils import getdate


DT = "Availability and Utilisation"

CATEGORY_MAP = {
    "ADT": "ADT's",
    "Excavator": "Excavator's",
    "Dozer": "Dozer's",
}

DB_CATEGORIES = list(CATEGORY_MAP.keys())
UI_CATEGORIES = list(CATEGORY_MAP.values())


def execute(filters=None):
    filters = frappe._dict(filters or {})

    from ..availability_util_shared import dashboard_date_range, dashboard_sites

    default_from_date, default_to_date = dashboard_date_range()

    from_date = getdate(filters.get("from_date") or default_from_date)
    to_date = getdate(filters.get("to_date") or default_to_date)

    filters["from_date"] = from_date
    filters["to_date"] = to_date

    sites = dashboard_sites(filters)
    date_list = get_date_list(from_date, to_date)

    data = []

    for idx, site in enumerate(sites):
        rows = fetch_site_rows(site, from_date, to_date)
        series = build_daily_series(rows, date_list)
        avgs = build_7day_averages(series)

        data.append({
            "site": site,
            "site_order": idx,
            "from_date": from_date,
            "to_date": to_date,
            "date_list_json": frappe.as_json(date_list),
            "averages_json": frappe.as_json(avgs),
            "series_json": frappe.as_json(series),
        })

    return get_columns(), data


def get_columns():
    return [
        {
            "label": "Site",
            "fieldname": "site",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Site Order",
            "fieldname": "site_order",
            "fieldtype": "Int",
            "width": 80,
            "hidden": 1,
        },
        {
            "label": "From Date",
            "fieldname": "from_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": "To Date",
            "fieldname": "to_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": "Date List JSON",
            "fieldname": "date_list_json",
            "fieldtype": "Long Text",
            "width": 80,
            "hidden": 1,
        },
        {
            "label": "Averages JSON",
            "fieldname": "averages_json",
            "fieldtype": "Long Text",
            "width": 80,
            "hidden": 1,
        },
        {
            "label": "Series JSON",
            "fieldname": "series_json",
            "fieldtype": "Long Text",
            "width": 80,
            "hidden": 1,
        },
    ]


def get_date_list(start, end):
    current = start
    out = []

    while current <= end:
        out.append(str(current))
        current += timedelta(days=1)

    return out


def is_sunday(date_value):
    if not date_value:
        return False

    return getdate(date_value).weekday() == 6


def fetch_site_rows(site, from_date, to_date):
    from is_production.production.report.avail_and_util_summary.avail_and_util_summary import (
        get_grouped_data,
    )

    return get_grouped_data({
        "start_date": from_date,
        "end_date": to_date,
        "location": site,
    })


def build_daily_series(rows, date_list):
    bucket = {
        db_cat: {
            day: {
                "avail": None,
                "util": None,
            }
            for day in date_list
        }
        for db_cat in DB_CATEGORIES
    }

    for row in rows:
        if row.get("indent") != 1:
            continue

        day = str(row.get("shift_date"))
        db_cat = row.get("asset_category")

        if db_cat not in bucket:
            continue

        if day not in bucket[db_cat]:
            continue

        bucket[db_cat][day]["avail"] = row.get("plant_shift_availability")
        bucket[db_cat][day]["util"] = row.get("plant_shift_utilisation")

    out = {}

    for db_cat, ui_label in CATEGORY_MAP.items():
        series = []

        for day in date_list:
            av_v = bucket[db_cat][day]["avail"]
            ut_v = bucket[db_cat][day]["util"]

            series.append({
                "date": day,
                "avail": float(av_v) if av_v is not None else None,
                "util": float(ut_v) if ut_v is not None else None,
            })

        out[ui_label] = series

    return out


def build_7day_averages(series):
    out = {}

    for ui_label in UI_CATEGORIES:
        items = [
            item
            for item in series.get(ui_label, [])
            if not is_sunday(item.get("date"))
        ]

        availability_values = [
            float(item["avail"])
            for item in items
            if item.get("avail") is not None
        ]

        utilisation_values = [
            float(item["util"])
            for item in items
            if item.get("util") is not None
        ]

        out[ui_label] = {
            "avail": (
                sum(availability_values) / len(availability_values)
                if availability_values
                else None
            ),
            "util": (
                sum(utilisation_values) / len(utilisation_values)
                if utilisation_values
                else None
            ),
        }

    return out