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
    rows.sort(
        key=lambda row: (
            -row.urgency_score,
            row.remaining_months if row.remaining_months is not None else 999999,
            row.site or "",
            row.fleet_number or "",
            row.position or "",
        )
    )

    data = [
        {
            "survey": row.survey,
            "survey_date": row.survey_date,
            "site": row.site,
            "fleet_number": row.fleet_number,
            "position": row.position,
            "serial_number": row.serial_number,
            "tyre_make": row.tyre_make,
            "tread_pattern": row.tread_pattern,
            "average_rtd": row.average_rtd,
            "rtd_percent": row.rtd_percent,
            "wear_rate": row.wear_rate,
            "recommended_pressure": row.recommended_pressure,
            "actual_pressure": row.actual_pressure,
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

    band_order = ["Critical", "Warning", "Check", "Good", "Normal"]
    band_counts = {
        band: sum(1 for row in rows if row.urgency_band == band)
        for band in band_order
    }
    chart = {
        "data": {
            "labels": band_order,
            "datasets": [
                {
                    "name": _("Tyres"),
                    "values": [band_counts[band] for band in band_order],
                }
            ],
        },
        "type": "bar",
        "colors": ["#D32F2F"],
    }
    summary = [
        {
            "value": band_counts["Critical"],
            "indicator": "Red",
            "label": _("Critical Tyres"),
            "datatype": "Int",
        },
        {
            "value": band_counts["Warning"],
            "indicator": "Orange",
            "label": _("Warning Tyres"),
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
        {"fieldname": "fleet_number", "label": _("ADT"), "fieldtype": "Link", "options": "Asset", "width": 105},
        {"fieldname": "position", "label": _("Position"), "fieldtype": "Data", "width": 80},
        {"fieldname": "serial_number", "label": _("Serial Number"), "fieldtype": "Data", "width": 150},
        {"fieldname": "tyre_make", "label": _("Make"), "fieldtype": "Data", "width": 110},
        {"fieldname": "tread_pattern", "label": _("Pattern"), "fieldtype": "Data", "width": 110},
        {"fieldname": "average_rtd", "label": _("Avg RTD (mm)"), "fieldtype": "Float", "precision": 1, "width": 105},
        {"fieldname": "rtd_percent", "label": _("RTD %"), "fieldtype": "Percent", "width": 85},
        {"fieldname": "wear_rate", "label": _("Wear mm/month"), "fieldtype": "Float", "precision": 2, "width": 125},
        {"fieldname": "recommended_pressure", "label": _("Rec. Pressure"), "fieldtype": "Float", "width": 105},
        {"fieldname": "actual_pressure", "label": _("Actual Pressure"), "fieldtype": "Float", "width": 110},
        {"fieldname": "pressure_variance", "label": _("Pressure Var. %"), "fieldtype": "Percent", "width": 110},
        {"fieldname": "remaining_months", "label": _("Months Left"), "fieldtype": "Float", "precision": 1, "width": 95},
        {"fieldname": "replacement_date", "label": _("Replace By"), "fieldtype": "Date", "width": 105},
        {"fieldname": "urgency_score", "label": _("Score"), "fieldtype": "Int", "width": 70},
        {"fieldname": "urgency_band", "label": _("Band"), "fieldtype": "Data", "width": 90},
        {"fieldname": "condition_notes", "label": _("Condition"), "fieldtype": "Data", "width": 180},
        {"fieldname": "required_action", "label": _("Required Action"), "fieldtype": "Data", "width": 200},
    ]
