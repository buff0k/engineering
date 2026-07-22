from collections import defaultdict

import frappe
from frappe import _

from engineering.tyre_analytics import (
    apply_common_filters,
    get_latest_analytics,
    include_mock_value,
)


def execute(filters=None):
    filters = frappe._dict(filters or {})
    rows = get_latest_analytics(
        as_on_date=filters.get("as_on_date"),
        include_mock=include_mock_value(filters),
    )
    rows = apply_common_filters(rows, filters)
    grouped = defaultdict(list)

    for row in rows:
        grouped[row.tyre_make or "Not Set"].append(row)

    data = []

    for tyre_make, brand_rows in grouped.items():
        wear_values = [row.wear_rate for row in brand_rows if row.wear_rate > 0]
        remaining_values = [
            row.remaining_months
            for row in brand_rows
            if row.remaining_months is not None
        ]
        pressure_compliant = sum(row.pressure_compliant for row in brand_rows)
        data.append(
            {
                "tyre_make": tyre_make,
                "tyre_count": len(brand_rows),
                "average_wear_rate": round(sum(wear_values) / len(wear_values), 2) if wear_values else 0,
                "average_remaining_months": round(sum(remaining_values) / len(remaining_values), 1) if remaining_values else None,
                "average_rtd_percent": round(sum(row.rtd_percent for row in brand_rows) / len(brand_rows), 1),
                "pressure_compliance": round((pressure_compliant / len(brand_rows)) * 100, 1),
                "damage_incidents": sum(row.damage_incident for row in brand_rows),
                "actions_required": sum(row.action_required for row in brand_rows),
                "critical_count": sum(1 for row in brand_rows if row.urgency_band == "Critical"),
            }
        )

    data.sort(key=lambda row: (-row["average_wear_rate"], row["tyre_make"]))
    chart = {
        "data": {
            "labels": [row["tyre_make"] for row in data],
            "datasets": [
                {
                    "name": _("Average Wear mm/month"),
                    "values": [row["average_wear_rate"] for row in data],
                }
            ],
        },
        "type": "bar",
        "colors": ["#00897B"],
    }
    summary = [
        {
            "value": len(data),
            "indicator": "Blue",
            "label": _("Brands"),
            "datatype": "Int",
        },
        {
            "value": sum(row["tyre_count"] for row in data),
            "indicator": "Blue",
            "label": _("Tyres Analysed"),
            "datatype": "Int",
        },
        {
            "value": sum(row["critical_count"] for row in data),
            "indicator": "Red",
            "label": _("Critical Tyres"),
            "datatype": "Int",
        },
    ]

    return get_columns(), data, None, chart, summary


def get_columns():
    return [
        {"fieldname": "tyre_make", "label": _("Tyre Make"), "fieldtype": "Data", "width": 170},
        {"fieldname": "tyre_count", "label": _("Tyres"), "fieldtype": "Int", "width": 80},
        {"fieldname": "average_wear_rate", "label": _("Avg Wear mm/month"), "fieldtype": "Float", "precision": 2, "width": 150},
        {"fieldname": "average_remaining_months", "label": _("Avg Months Remaining"), "fieldtype": "Float", "precision": 1, "width": 160},
        {"fieldname": "average_rtd_percent", "label": _("Avg RTD %"), "fieldtype": "Percent", "width": 110},
        {"fieldname": "pressure_compliance", "label": _("Pressure Compliance %"), "fieldtype": "Percent", "width": 160},
        {"fieldname": "damage_incidents", "label": _("Damage Incidents"), "fieldtype": "Int", "width": 130},
        {"fieldname": "actions_required", "label": _("Actions Required"), "fieldtype": "Int", "width": 130},
        {"fieldname": "critical_count", "label": _("Critical"), "fieldtype": "Int", "width": 90},
    ]
