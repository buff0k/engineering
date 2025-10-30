import frappe
from frappe.utils import getdate, formatdate

def execute(filters=None):
    filters = filters or {}

    start_date = getdate(filters.get("start_date"))
    end_date = getdate(filters.get("end_date"))
    site = filters.get("site")
    shift = filters.get("shift")

    # ----------------------------------------------------
    # 1️⃣ Base query from Availability and Utilisation
    # ----------------------------------------------------
    conditions = ["shift_date BETWEEN %(start_date)s AND %(end_date)s"]
    params = {"start_date": start_date, "end_date": end_date}

    if site:
        conditions.append("location = %(site)s")
        params["site"] = site

    if shift:
        conditions.append("shift = %(shift)s")
        params["shift"] = shift

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            asset_name,
            asset_category,
            shift_date,
            shift_required_hours,
            shift_working_hours,
            shift_breakdown_hours,
            shift_available_hours,
            plant_shift_availability,
            plant_shift_utilisation
        FROM `tabAvailability and Utilisation`
        WHERE {where_clause}
        AND asset_category IN ('Excavator', 'Dozer', 'ADT')
        ORDER BY
            FIELD(asset_category, 'Excavator', 'Dozer', 'ADT'),
            asset_name,
            shift_date
    """

    entries = frappe.db.sql(query, params, as_dict=True)

    if not entries:
        return get_columns(), [], None, None

    # ----------------------------------------------------
    # 2️⃣ Fetch Breakdown & Delay reasons
    # ----------------------------------------------------
    breakdown_data = frappe._dict()
    delay_data = frappe._dict()

    # 🔧 Plant Breakdown — use creation as the date
    bd_rows = frappe.db.sql(f"""
        SELECT asset_name, breakdown_reason_updates, creation
        FROM `tabPlant Breakdown`
        WHERE DATE(creation) BETWEEN %(start_date)s AND %(end_date)s
    """, params, as_dict=True)

    for row in bd_rows:
        key = f"{row.asset_name}_{getdate(row.creation)}"
        breakdown_data[key] = row.breakdown_reason_updates

    # 🔧 Daily Lost Hours Recon — join with correct child table and fieldnames
    delay_rows = frappe.db.sql(f"""
        SELECT
            dla.asset_name,
            dlh.shift_date,
            dla.total_general_lost_hours_child AS gen_lost_hours_comments
        FROM `tabDaily Lost Hours Recon` AS dlh
        INNER JOIN `tabDaily Lost Hours Assets` AS dla
            ON dla.parent = dlh.name
        WHERE dlh.shift_date BETWEEN %(start_date)s AND %(end_date)s
    """, params, as_dict=True)

    for row in delay_rows:
        key = f"{row.asset_name}_{getdate(row.shift_date)}"
        delay_data[key] = row.gen_lost_hours_comments

    # ----------------------------------------------------
    # 3️⃣ Build structured data grouped by category
    # ----------------------------------------------------
    data = []
    categories = ["Excavator", "Dozer", "ADT"]

    for cat in categories:
        cat_entries = [e for e in entries if e.asset_category == cat]
        if not cat_entries:
            continue

        # Add collapsible category header
        data.append({
            "plant_no": f"**{cat}s**",
            "indent": 0,
            "is_group": True,  # This enables collapse/expand
        })

        # Get unique plant names
        plant_names = sorted(set(e.asset_name for e in cat_entries))

        for plant in plant_names:
            plant_entries = [e for e in cat_entries if e.asset_name == plant]

            for entry in plant_entries:
                shift_date = getdate(entry.shift_date)
                key = f"{plant}_{shift_date}"

                data.append({
                    "plant_no": plant,
                    "date": formatdate(shift_date, "dd-MM-yyyy"),
                    "weekday": shift_date.strftime("%A"),
                    "required_hours": entry.shift_required_hours,
                    "worked_hours": entry.shift_working_hours,
                    "breakdown_hours": entry.shift_breakdown_hours,
                    "available_hours": entry.shift_available_hours,
                    "avail": entry.plant_shift_availability,
                    "utiliz": entry.plant_shift_utilisation,
                    "breakdown_reason": breakdown_data.get(key, ""),
                    "delay_reason": delay_data.get(key, ""),
                    "indent": 1,  # Child rows under category
                    "is_group": False
                })

    return get_columns(), data, None, None


def get_columns():
    """Define table columns"""
    return [
        {"fieldname": "plant_no", "label": "Plant No", "fieldtype": "Data", "width": 160},
        {"fieldname": "date", "label": "Date", "fieldtype": "Data", "width": 110},
        {"fieldname": "weekday", "label": "Weekday", "fieldtype": "Data", "width": 110},
        {"fieldname": "required_hours", "label": "Required Hours", "fieldtype": "Float", "width": 130},
        {"fieldname": "worked_hours", "label": "Worked Hours", "fieldtype": "Float", "width": 130},
        {"fieldname": "breakdown_hours", "label": "Breakdown Hours", "fieldtype": "Float", "width": 130},
        {"fieldname": "available_hours", "label": "Available Hours", "fieldtype": "Float", "width": 130},
        {"fieldname": "avail", "label": "Avail %", "fieldtype": "Percent", "width": 100},
        {"fieldname": "utiliz", "label": "Utiliz %", "fieldtype": "Percent", "width": 100},
        {"fieldname": "breakdown_reason", "label": "Breakdown Reason", "fieldtype": "Data", "width": 200},
        {"fieldname": "delay_reason", "label": "Delay Reason", "fieldtype": "Data", "width": 200},
    ]
