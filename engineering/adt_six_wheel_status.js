from calendar import monthrange
from collections import defaultdict
from datetime import date

import frappe
from frappe import _
from frappe.utils import add_months, cint, getdate

from engineering.tyre_analytics import (
    apply_common_filters,
    get_latest_analytics,
    include_mock_value,
)


def _month_start(value):
    value = getdate(value)
    return date(value.year, value.month, 1)


def _month_end(value):
    return date(value.year, value.month, monthrange(value.year, value.month)[1])


def execute(filters=None):
    filters = frappe._dict(filters or {})
    anchor_date = getdate(filters.get("anchor_date") or frappe.utils.today())
    number_of_months = max(1, min(cint(filters.get("months") or 5), 24))
    first_month = _month_start(add_months(anchor_date, 1))
    last_month = _month_end(add_months(first_month, number_of_months - 1))

    rows = get_latest_analytics(
        as_on_date=anchor_date,
        include_mock=include_mock_value(filters),
    )
    rows = apply_common_filters(rows, filters)
    grouped = defaultdict(lambda: {"serials": set(), "machines": set()})

    for row in rows:
        if not row.replacement_date:
            continue

        replacement_date = getdate(row.replacement_date)

        if replacement_date < first_month or replacement_date > last_month:
            continue

        month = _month_start(replacement_date)
        key = (month, row.site or "Not Set")
        grouped[key]["serials"].add(row.serial_number)
        grouped[key]["machines"].add(row.fleet_number)

    data = []

    for (month, site), values in sorted(grouped.items()):
        machines = sorted(machine for machine in values["machines"] if machine)
        data.append(
            {
                "forecast_month": month,
                "site": site,
                "tyre_count": len(values["serials"]),
                "machine_count": len(machines),
                "machines": ", ".join(machines),
            }
        )

    month_labels = []
    month_values = []

    for offset in range(number_of_months):
        month = _month_start(add_months(first_month, offset))
        month_labels.append(month.strftime("%b %Y"))
        month_values.append(
            sum(row["tyre_count"] for row in data if row["forecast_month"] == month)
        )

    chart = {
        "data": {
            "labels": month_labels,
            "datasets": [{"name": _("Tyres"), "values": month_values}],
        },
        "type": "bar",
        "colors": ["#E0A800"],
    }
    summary = [
        {
            "value": sum(month_values),
            "indicator": "Orange",
            "label": _("Tyres Forecast"),
            "datatype": "Int",
        },
        {
            "value": sum(1 for row in rows if row.remaining_months is not None and row.remaining_months <= 1),
            "indicator": "Red",
            "label": _("Due Within One Month"),
            "datatype": "Int",
        },
        {
            "value": len({row.fleet_number for row in rows if row.fleet_number}),
            "indicator": "Blue",
            "label": _("ADTs Analysed"),
            "datatype": "Int",
        },
    ]

    return get_columns(), data, None, chart, summary


def get_columns():
    return [
        {"fieldname": "forecast_month", "label": _("Forecast Month"), "fieldtype": "Date", "width": 120},
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "Location", "width": 170},
        {"fieldname": "tyre_count", "label": _("Tyres"), "fieldtype": "Int", "width": 90},
        {"fieldname": "machine_count", "label": _("ADTs"), "fieldtype": "Int", "width": 90},
        {"fieldname": "machines", "label": _("Fleet Numbers"), "fieldtype": "Data", "width": 500},
    ]
