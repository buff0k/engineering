from collections import defaultdict

import frappe
from frappe import _

from engineering.tyre_analytics import (
    get_latest_analytics,
    include_mock_value,
)


def execute(filters=None):
    filters = frappe._dict(filters or {})
    rows = get_latest_analytics(
        as_on_date=filters.get("as_on_date"),
        include_mock=include_mock_value(filters),
    )
    grouped = defaultdict(list)

    for row in rows:
        grouped[row.site or "Not Set"].append(row)

    data = []

    for site, site_rows in grouped.items():
        wear_values = [row.wear_rate for row in site_rows if row.wear_rate > 0]
        pressure_compliant = sum(row.pressure_compliant for row in site_rows)
        data.append(
            {
                "site": site,
                "tyre_count": len(site_rows),
                "adt_count": len({row.fleet_number for row in site_rows if row.fleet_number}),
                "average_wear_rate": round(sum(wear_values) / len(wear_values), 2) if wear_values else 0,
                "average_rtd_percent": round(sum(row.rtd_percent for row in site_rows) / len(site_rows), 1),
                "pressure_compliance": round((pressure_compliant / len(site_rows)) * 100, 1),
                "low_tread_count": sum(row.low_tread for row in site_rows),
                "damage_incidents": sum(row.damage_incident for row in site_rows),
                "actions_required": sum(row.action_required for row in site_rows),
                "critical_count": sum(1 for row in site_rows if row.urgency_band == "Critical"),
            }
        )

    data.sort(key=lambda row: (-row["average_wear_rate"], row["site"]))
    chart = {
        "data": {
            "labels": [row["site"] for row in data],
            "datasets": [
                {
                    "name": _("Average Wear mm/month"),
                    "values": [row["average_wear_rate"] for row in data],
                }
            ],
        },
        "type": "bar",
        "colors": ["#1565C0"],
    }
    summary = [
        {
            "value": len(data),
            "indicator": "Blue",
            "label": _("Sites"),
            "datatype": "Int",
        },
        {
            "value": sum(row["critical_count"] for row in data),
            "indicator": "Red",
            "label": _("Critical Tyres"),
            "datatype": "Int",
        },
        {
            "value": sum(row["actions_required"] for row in data),
            "indicator": "Orange",
            "label": _("Actions Required"),
            "datatype": "Int",
        },
    ]

    return get_columns(), data, None, chart, summary


def get_columns():
    return [
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "Location", "width": 190},
        {"fieldname": "tyre_count", "label": _("Tyres"), "fieldtype": "Int", "width": 80},
        {"fieldname": "adt_count", "label": _("ADTs"), "fieldtype": "Int", "width": 80},
        {"fieldname": "average_wear_rate", "label": _("Avg Wear mm/month"), "fieldtype": "Float", "precision": 2, "width": 150},
        {"fieldname": "average_rtd_percent", "label": _("Avg RTD %"), "fieldtype": "Percent", "width": 110},
        {"fieldname": "pressure_compliance", "label": _("Pressure Compliance %"), "fieldtype": "Percent", "width": 160},
        {"fieldname": "low_tread_count", "label": _("Below 25% Tread"), "fieldtype": "Int", "width": 130},
        {"fieldname": "damage_incidents", "label": _("Damage Incidents"), "fieldtype": "Int", "width": 130},
        {"fieldname": "actions_required", "label": _("Actions Required"), "fieldtype": "Int", "width": 130},
        {"fieldname": "critical_count", "label": _("Critical"), "fieldtype": "Int", "width": 90},
    ]
