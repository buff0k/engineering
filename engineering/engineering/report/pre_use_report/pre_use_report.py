import frappe
from frappe.utils import getdate


def execute(filters=None):
    if not filters:
        return [], []

    start = getdate(filters.get("start_date"))
    end = getdate(filters.get("end_date"))
    site = filters.get("site")
    shift = filters.get("shift")

    columns = [
        {"label": "Asset Category", "fieldname": "asset_category", "fieldtype": "Data", "width": 120},
        {"label": "Date", "fieldname": "shift_date", "fieldtype": "Date", "width": 120},
        {"label": "Machine No.", "fieldname": "asset_name", "fieldtype": "Data", "width": 120},
        {"label": "Make/Model", "fieldname": "item_name", "fieldtype": "Data", "width": 150},
        {"label": "Start Hours", "fieldname": "start_hours", "fieldtype": "Float", "width": 120},
        {"label": "End Hours", "fieldname": "end_hours", "fieldtype": "Float", "width": 120},
        {"label": "Working Hours", "fieldname": "working_hours", "fieldtype": "Float", "width": 140},
    ]

    conditions = [
        "p.shift_date BETWEEN %(start)s AND %(end)s",
        "p.location = %(site)s"
    ]

    if shift:
        conditions.append("p.shift = %(shift)s")

    query = f"""
        SELECT
            a.asset_category,
            a.asset_name,
            a.item_name,
            p.shift,
            p.shift_date,
            a.eng_hrs_start,
            a.eng_hrs_end,
            a.working_hours
        FROM `tabPre-Use Hours` p
        LEFT JOIN `tabPre-use Assets` a
            ON a.parent = p.name
        WHERE {" AND ".join(conditions)}
        ORDER BY
            a.asset_category,
            a.asset_name,
            p.shift_date,
            p.shift
    """

    rows = frappe.db.sql(
        query,
        {
            "start": start,
            "end": end,
            "site": site,
            "shift": shift
        },
        as_dict=True
    )

    data = []

    # ---------------------------------------------------
    # Specific Shift Selected
    # ---------------------------------------------------

    if shift:

        for r in rows:

            if r.eng_hrs_start is not None and r.eng_hrs_end is not None:

                # Treat End Hours = 0 as machine did not work
                if float(r.eng_hrs_end) == 0:
                    working_hours = 0

                else:
                    working_hours = round(
                        float(r.eng_hrs_end) - float(r.eng_hrs_start), 1
                    )

            elif r.working_hours is not None:
                working_hours = r.working_hours

            else:
                working_hours = None

            data.append({
                "asset_category": r.asset_category,
                "shift_date": r.shift_date,
                "asset_name": r.asset_name,
                "item_name": r.item_name,
                "start_hours": r.eng_hrs_start,
                "end_hours": r.eng_hrs_end,
                "working_hours": working_hours
            })

    # ---------------------------------------------------
    # Combine Day + Night
    # ---------------------------------------------------

    else:

        combo_map = {}

        for r in rows:

            key = (
                r.asset_category,
                r.asset_name,
                r.shift_date
            )

            if key not in combo_map:
                combo_map[key] = {
                    "asset_category": r.asset_category,
                    "shift_date": r.shift_date,
                    "asset_name": r.asset_name,
                    "item_name": r.item_name,
                    "start_hours": None,
                    "end_hours": None
                }

            if r.shift in ["Day", "Morning"]:
                combo_map[key]["start_hours"] = r.eng_hrs_start

            elif r.shift in ["Night", "Afternoon"]:
                combo_map[key]["end_hours"] = r.eng_hrs_end

        for val in combo_map.values():

            start_hours = val["start_hours"]
            end_hours = val["end_hours"]

            working_hours = None

            if start_hours is not None and end_hours is not None:

                # Treat End Hours = 0 as machine did not work
                if float(end_hours) == 0:
                    working_hours = 0

                else:
                    working_hours = round(
                        float(end_hours) - float(start_hours), 1
                    )

            data.append({
                "asset_category": val["asset_category"],
                "shift_date": val["shift_date"],
                "asset_name": val["asset_name"],
                "item_name": val["item_name"],
                "start_hours": start_hours,
                "end_hours": end_hours,
                "working_hours": working_hours
            })

    return columns, data