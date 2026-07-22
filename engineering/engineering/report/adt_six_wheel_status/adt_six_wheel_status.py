import frappe
from frappe import _

from engineering.tyre_analytics import (
    get_latest_analytics,
    include_mock_value,
)


POSITION_ORDER = {
    "LF": 1,
    "RF": 2,
    "RM": 3,
    "RRO": 3,
    "RR": 4,
    "RRI": 4,
    "LR": 5,
    "LRI": 5,
    "LM": 6,
    "LRO": 6,
}


def execute(filters=None):
    filters = frappe._dict(filters or {})
    fleet_number = filters.get("fleet_number")

    if not fleet_number:
        return get_columns(), []

    rows = get_latest_analytics(
        as_on_date=filters.get("as_on_date"),
        include_mock=include_mock_value(filters),
    )
    rows = [row for row in rows if row.fleet_number == fleet_number]
    rows.sort(
        key=lambda row: (
            POSITION_ORDER.get(str(row.position or "").upper(), 99),
            row.position or "",
        )
    )

    data = [
        {
            "survey": row.survey,
            "survey_date": row.survey_date,
            "site": row.site,
            "position": row.position,
            "serial_number": row.serial_number,
            "tyre_make": row.tyre_make,
            "tyre_size": row.tyre_size,
            "tread_pattern": row.tread_pattern,
            "otd": row.otd,
            "average_rtd": row.average_rtd,
            "rtd_percent": row.rtd_percent,
            "wear_rate": row.wear_rate,
            "pressure_variance": row.pressure_variance,
            "remaining_months": row.remaining_months,
            "replacement_date": row.replacement_date,
            "urgency_score": row.urgency_score,
            "urgency_band": row.urgency_band,
            "condition_notes": row.condition_notes,
            "required_action": row.required_action,
        }
        for row in rows
    ]

    chart = {
        "data": {
            "labels": [row.position for row in rows],
            "datasets": [
                {
                    "name": _("Remaining Tread %"),
                    "values": [row.rtd_percent for row in rows],
                }
            ],
        },
        "type": "bar",
        "colors": ["#2E7D32"],
    }
    summary = [
        {
            "value": len(rows),
            "indicator": "Blue",
            "label": _("Tyres Fitted"),
            "datatype": "Int",
        },
        {
            "value": sum(1 for row in rows if row.rtd_percent < 25),
            "indicator": "Red",
            "label": _("Below 25% Tread"),
            "datatype": "Int",
        },
        {
            "value": sum(1 for row in rows if row.pressure_variance < -10),
            "indicator": "Orange",
            "label": _("Underinflated >10%"),
            "datatype": "Int",
        },
    ]

    return get_columns(), data, None, chart, summary


def get_columns():
    return [
        {"fieldname": "survey", "label": _("Survey"), "fieldtype": "Link", "options": "Tyre Survey", "width": 140},
        {"fieldname": "survey_date", "label": _("Survey Date"), "fieldtype": "Date", "width": 100},
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "Location", "width": 150},
        {"fieldname": "position", "label": _("Position"), "fieldtype": "Data", "width": 85},
        {"fieldname": "serial_number", "label": _("Serial Number"), "fieldtype": "Data", "width": 150},
        {"fieldname": "tyre_make", "label": _("Make"), "fieldtype": "Data", "width": 110},
        {"fieldname": "tyre_size", "label": _("Size"), "fieldtype": "Data", "width": 100},
        {"fieldname": "tread_pattern", "label": _("Pattern"), "fieldtype": "Data", "width": 110},
        {"fieldname": "otd", "label": _("OTD"), "fieldtype": "Float", "precision": 1, "width": 70},
        {"fieldname": "average_rtd", "label": _("Avg RTD"), "fieldtype": "Float", "precision": 1, "width": 85},
        {"fieldname": "rtd_percent", "label": _("RTD %"), "fieldtype": "Percent", "width": 80},
        {"fieldname": "wear_rate", "label": _("Wear mm/month"), "fieldtype": "Float", "precision": 2, "width": 125},
        {"fieldname": "pressure_variance", "label": _("Pressure Var. %"), "fieldtype": "Percent", "width": 110},
        {"fieldname": "remaining_months", "label": _("Months Left"), "fieldtype": "Float", "precision": 1, "width": 95},
        {"fieldname": "replacement_date", "label": _("Replace By"), "fieldtype": "Date", "width": 105},
        {"fieldname": "urgency_score", "label": _("Score"), "fieldtype": "Int", "width": 65},
        {"fieldname": "urgency_band", "label": _("Band"), "fieldtype": "Data", "width": 90},
        {"fieldname": "condition_notes", "label": _("Condition"), "fieldtype": "Data", "width": 180},
        {"fieldname": "required_action", "label": _("Required Action"), "fieldtype": "Data", "width": 200},
    ]
