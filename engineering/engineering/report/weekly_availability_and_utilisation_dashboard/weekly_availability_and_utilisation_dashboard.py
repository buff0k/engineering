# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt


import re
from datetime import timedelta

import frappe
from frappe.utils import getdate


DT = "Availability and Utilisation"

CATEGORY_MAP = {
    "ADT": "ADTs",
    "Excavator": "Excavators",
    "Dozer": "Dozers",
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

        daily_series = build_daily_series(rows, date_list)
        asset_series = build_asset_series(rows)
        avgs = build_7day_averages(daily_series)

        data.append({
            "site": site,
            "site_order": idx,
            "from_date": from_date,
            "to_date": to_date,
            "date_list_json": frappe.as_json(date_list),
            "averages_json": frappe.as_json(avgs),
            "series_json": frappe.as_json(daily_series),
            "asset_series_json": frappe.as_json(asset_series),
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
            "label": "Daily Series JSON",
            "fieldname": "series_json",
            "fieldtype": "Long Text",
            "width": 80,
            "hidden": 1,
        },
        {
            "label": "Asset Series JSON",
            "fieldname": "asset_series_json",
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
        if not isinstance(row, dict):
            continue

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


def build_asset_series(rows):
    grouped = {
        ui_label: {}
        for ui_label in UI_CATEGORIES
    }

    for row in rows:
        if not isinstance(row, dict):
            continue

        shift_date = row.get("shift_date")

        if shift_date and is_sunday(shift_date):
            continue

        db_cat = row.get("asset_category")

        if db_cat not in CATEGORY_MAP:
            continue

        ui_label = CATEGORY_MAP[db_cat]

        plant_no = get_plant_no(row)

        if not plant_no:
            continue

        availability = row.get("plant_shift_availability")
        utilisation = row.get("plant_shift_utilisation")

        if plant_no not in grouped[ui_label]:
            grouped[ui_label][plant_no] = {
                "plant_no": plant_no,
                "availability_values": [],
                "utilisation_values": [],
            }

        if availability is not None:
            grouped[ui_label][plant_no]["availability_values"].append(float(availability))

        if utilisation is not None:
            grouped[ui_label][plant_no]["utilisation_values"].append(float(utilisation))

    output = {}

    for ui_label in UI_CATEGORIES:
        assets = []

        for plant_no, item in grouped.get(ui_label, {}).items():
            availability_values = item["availability_values"]
            utilisation_values = item["utilisation_values"]

            assets.append({
                "plant_no": plant_no,
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
            })

        assets.sort(key=lambda item: natural_sort_key(item.get("plant_no")))

        output[ui_label] = assets

    return output


def get_plant_no(row):
    possible_keys = [
        "plant_no",
        "plant_number",
        "plant",
        "asset",
        "asset_name",
        "machine",
        "machine_no",
        "equipment",
        "equipment_no",
    ]

    for key in possible_keys:
        value = row.get(key)

        if value not in [None, ""]:
            return str(value).strip()

    return ""


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


def natural_sort_key(value):
    value = str(value or "")

    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", value)
    ]