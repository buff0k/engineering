import frappe
from frappe.utils import add_days, nowdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data, None, get_chart(data), get_summary(data)


def get_columns():
    return [
        {"label": "Machine Type", "fieldname": "machine_type", "fieldtype": "Data", "width": 130},
        {"label": "Plant Number", "fieldname": "plant_number", "fieldtype": "Data", "width": 130},
        {"label": "Location", "fieldname": "location", "fieldtype": "Link", "options": "Location", "width": 140},
        {"label": "Component", "fieldname": "component", "fieldtype": "Data", "width": 140},
        {"label": "Sample Date", "fieldname": "sample_date", "fieldtype": "Date", "width": 110},
        {"label": "Hours / KM", "fieldname": "hours_km", "fieldtype": "Float", "width": 100},
        {"label": "Oil Grade", "fieldname": "oil_grade", "fieldtype": "Data", "width": 110},
        {"label": "Sample Number", "fieldname": "sample_number", "fieldtype": "Int", "width": 120},
        {"label": "Lab Result", "fieldname": "lab_result", "fieldtype": "Data", "width": 110},
        {"label": "Condition", "fieldname": "condition", "fieldtype": "Data", "width": 110},
        {"label": "Action Required", "fieldname": "action_required", "fieldtype": "Small Text", "width": 220},
        {"label": "Next Sample Due", "fieldname": "next_sample_due", "fieldtype": "Date", "width": 130},
        {"label": "Comments", "fieldname": "comments", "fieldtype": "Small Text", "width": 260},
    ]


def get_data(filters):
    conditions = ["wr.docstatus < 2"]
    values = {}

    if filters.get("from_date"):
        conditions.append("wr.sampledate >= %(from_date)s")
        values["from_date"] = filters.from_date

    if filters.get("to_date"):
        conditions.append("wr.sampledate <= %(to_date)s")
        values["to_date"] = filters.to_date

    if filters.get("plant_number"):
        conditions.append("wr.asset = %(plant_number)s")
        values["plant_number"] = filters.plant_number

    if filters.get("component"):
        conditions.append("wr.component LIKE %(component)s")
        values["component"] = "%" + filters.component + "%"

    if filters.get("location"):
        conditions.append("wr.location = %(location)s")
        values["location"] = filters.location

    if filters.get("condition"):
        status_map = {
            "Normal": 0,
            "Monitor": 1,
            "Requires Attention": 2,
            "Urgent": 3,
            "Critical": 4,
            "Import Failed": "import_failed",
        }
        selected = status_map.get(filters.condition)

        if selected == "import_failed":
            conditions.append("wr.import_failed = 1")
        elif selected is not None:
            conditions.append("wr.status = %(condition_status)s")
            values["condition_status"] = selected

    if filters.get("only_attention"):
        conditions.append("""
            (
                wr.import_failed = 1
                OR wr.status >= 2
            )
        """)

    where_clause = " AND ".join(conditions)

    return frappe.db.sql(f"""
        SELECT
            COALESCE(a.asset_category, wr.raw_asset_value, wr.machine, '') AS machine_type,
            COALESCE(wr.asset, wr.machine, '') AS plant_number,
            wr.location AS location,
            wr.component AS component,
            wr.sampledate AS sample_date,
            wr.machread AS hours_km,
            COALESCE(wr.oilbrand, wr.oilsupplier, '') AS oil_grade,
            wr.sampno AS sample_number,
            COALESCE(wr.import_status, '') AS lab_result,
            CASE
                WHEN wr.import_failed = 1 THEN 'Import Failed'
                WHEN wr.status = 4 THEN 'Critical'
                WHEN wr.status = 3 THEN 'Urgent'
                WHEN wr.status = 2 THEN 'Requires Attention'
                WHEN wr.status = 1 THEN 'Monitor'
                ELSE 'Normal'
            END AS `condition`,
            COALESCE(wr.actiontext, '') AS action_required,
            DATE_ADD(wr.sampledate, INTERVAL 30 DAY) AS next_sample_due,
            COALESCE(wr.commentstext, wr.feedbacktext, '') AS comments
        FROM `tabWearCheck Results` wr
        LEFT JOIN `tabAsset` a ON a.name = wr.asset
        WHERE {where_clause}
        ORDER BY wr.sampledate DESC, wr.sampno DESC
    """, values, as_dict=True)


def get_summary(data):
    return [
        {"label": "Total Samples", "value": len(data), "indicator": "Blue", "datatype": "Int"},
        {"label": "Critical", "value": len([d for d in data if d.condition == "Critical"]), "indicator": "Red", "datatype": "Int"},
        {"label": "Urgent", "value": len([d for d in data if d.condition == "Urgent"]), "indicator": "Red", "datatype": "Int"},
        {"label": "Requires Attention", "value": len([d for d in data if d.condition == "Requires Attention"]), "indicator": "Orange", "datatype": "Int"},
        {"label": "Normal", "value": len([d for d in data if d.condition == "Normal"]), "indicator": "Green", "datatype": "Int"},
    ]


def get_chart(data):
    counts = {}
    for row in data:
        counts[row.condition] = counts.get(row.condition, 0) + 1

    return {
        "type": "donut",
        "height": 260,
        "data": {
            "labels": list(counts.keys()),
            "datasets": [{"name": "Samples", "values": list(counts.values())}],
        },
    }
