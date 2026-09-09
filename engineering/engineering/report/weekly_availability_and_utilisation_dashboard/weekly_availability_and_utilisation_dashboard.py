# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import re
from datetime import timedelta

import frappe
from frappe.utils import getdate

from engineering.engineering.report.availability_and_utilisation_engine import (
    availability_and_utilisation_engine as au_engine,
)

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

    engine_rows = fetch_engine_rows(
        sites,
        from_date,
        to_date,
        filters.get("asset_ownership")
        or "Isambane & Excavo Assets",
    )

    data = []

    for idx, site in enumerate(sites):
        site_rows = [
            row
            for row in engine_rows
            if row.get("location") == site
        ]

        daily_series = build_daily_series(
            site_rows,
            date_list,
        )
        asset_series = build_asset_series(
            site_rows
        )
        avgs = build_7day_averages(
            daily_series
        )

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


def fetch_engine_rows(
    sites,
    from_date,
    to_date,
    asset_ownership,
):
    """Fetch canonical shift rows once for every selected site."""
    if not sites:
        return []

    rows = au_engine.get_data(
        frappe._dict({
            "from_date": from_date,
            "to_date": to_date,
            "locations": sites,
            "assets": [],
            "companies": [],
            "asset_ownership": asset_ownership,
            "free_hours": 0,
            "production_machines_only": 0,
            "au_percentage_basis": "100% A & U",
        })
    ) or []

    return [
        row
        for row in rows
        if isinstance(row, dict)
        and int(row.get("indent") or 0) == 3
        and not row.get("is_formula_row")
        and row.get("asset_category")
        in DB_CATEGORIES
    ]


def build_daily_series(rows, date_list):
    grouped = {}

    for row in rows:
        day = str(row.get("shift_date") or "")
        category = row.get("asset_category")

        if (
            category not in DB_CATEGORIES
            or day not in date_list
        ):
            continue

        grouped.setdefault(
            (category, day),
            [],
        ).append(row)

    output = {}

    for category, label in CATEGORY_MAP.items():
        series = []

        for day in date_list:
            source_rows = grouped.get(
                (category, day),
                [],
            )

            if source_rows:
                summary = au_engine.build_summary_row(
                    source_rows,
                    indent=1,
                    asset_category=category,
                    shift_date=day,
                )
                availability = summary.get(
                    "availability_percentage"
                )
                utilisation = summary.get(
                    "utilisation_percentage"
                )
            else:
                availability = None
                utilisation = None

            series.append({
                "date": day,
                "avail": availability,
                "util": utilisation,
            })

        output[label] = series

    return output


def build_asset_series(rows):
    grouped = {}

    for row in rows:
        category = row.get("asset_category")
        asset_name = row.get("asset_name")

        if (
            category not in DB_CATEGORIES
            or not asset_name
        ):
            continue

        grouped.setdefault(
            (category, asset_name),
            [],
        ).append(row)

    output = {
        label: []
        for label in UI_CATEGORIES
    }

    for (category, asset_name), source_rows in grouped.items():
        summary = au_engine.build_summary_row(
            source_rows,
            indent=2,
            asset_category=category,
            asset_name=asset_name,
        )

        output[CATEGORY_MAP[category]].append({
            "plant_no": asset_name,
            "avail": summary.get(
                "availability_percentage"
            ),
            "util": summary.get(
                "utilisation_percentage"
            ),
        })

    for label in UI_CATEGORIES:
        output[label].sort(
            key=lambda item: natural_sort_key(
                item.get("plant_no")
            )
        )

    return output


def get_plant_no(row):
    value = row.get("asset_name")

    if value not in [None, ""]:
        return str(value).strip()

    fallback_keys = [
        "plant_no",
        "plant_number",
        "plant",
        "asset",
        "machine",
        "machine_no",
        "equipment",
        "equipment_no",
    ]

    for key in fallback_keys:
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