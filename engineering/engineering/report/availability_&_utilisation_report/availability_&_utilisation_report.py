import frappe
from frappe.utils import flt


def r1(v):
    return round(flt(v), 1)


def calc_availability(req_hrs, avail_hrs):
    req_hrs = flt(req_hrs)
    avail_hrs = flt(avail_hrs)

    if req_hrs <= 0:
        return 0.0

    return r1((avail_hrs / req_hrs) * 100)


def calc_utilisation(work_hrs, avail_hrs):
    work_hrs = flt(work_hrs)
    avail_hrs = flt(avail_hrs)

    if avail_hrs <= 0:
        return 0.0

    return r1((work_hrs / avail_hrs) * 100)


def get_columns():
    return [
        {"label": "Asset Category", "fieldname": "asset_category", "fieldtype": "Data", "width": 140},
        {"label": "Shift Date", "fieldname": "shift_date", "fieldtype": "Date", "width": 110},
        {"label": "Asset", "fieldname": "asset_name", "fieldtype": "Data", "width": 130},
        {"label": "Shift", "fieldname": "shift", "fieldtype": "Data", "width": 70},
        {"label": "Location", "fieldname": "location", "fieldtype": "Data", "width": 90},

        {"label": "Actual Hours", "fieldname": "actual_hours", "fieldtype": "Float", "width": 100, "precision": 1},
        {"label": "Planned Downtime", "fieldname": "planned_downtime", "fieldtype": "Float", "width": 120, "precision": 1},
        {"label": "Req Hrs", "fieldname": "shift_required_hours", "fieldtype": "Float", "width": 90, "precision": 1},
        {"label": "Work Hrs", "fieldname": "shift_working_hours", "fieldtype": "Float", "width": 90, "precision": 1},
        {"label": "Avail Hrs", "fieldname": "shift_available_hours", "fieldtype": "Float", "width": 90, "precision": 1},
        {"label": "Mechanical Downtime", "fieldname": "mechanical_downtime", "fieldtype": "Float", "width": 140, "precision": 1},
        {"label": "Actual Breakdown", "fieldname": "actual_breakdown", "fieldtype": "Float", "width": 130, "precision": 1},
        {"label": "Actual Inspection", "fieldname": "actual_inspection", "fieldtype": "Float", "width": 130, "precision": 1},
        {"label": "Actual Service Time", "fieldname": "actual_service_time", "fieldtype": "Float", "width": 140, "precision": 1},
        {"label": "Other Lost Hours", "fieldname": "other_lost_hours", "fieldtype": "Float", "width": 120, "precision": 1},
        {"label": "General &...", "fieldname": "general_and", "fieldtype": "Float", "width": 90, "precision": 1},
        {"label": "Other Lost Hours Variance", "fieldname": "other_lost_hours_variance", "fieldtype": "Float", "width": 160, "precision": 1},

        {"label": "Avail (%)", "fieldname": "plant_shift_availability", "fieldtype": "Percent", "width": 85, "precision": 1},
        {"label": "Util (%)", "fieldname": "plant_shift_utilisation", "fieldtype": "Percent", "width": 85, "precision": 1},
    ]


def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_data(filters):
    conditions = []
    values = {}

    if filters.get("start_date"):
        conditions.append("shift_date >= %(start_date)s")
        values["start_date"] = filters.get("start_date")

    if filters.get("end_date"):
        conditions.append("shift_date <= %(end_date)s")
        values["end_date"] = filters.get("end_date")

    if filters.get("site"):
        conditions.append("location = %(site)s")
        values["site"] = filters.get("site")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    rows = frappe.db.sql(
        f"""
        SELECT
            IFNULL(asset_category, '') AS asset_category,
            shift_date,
            IFNULL(asset_name, '') AS asset_name,
            IFNULL(shift, '') AS shift,
            IFNULL(location, '') AS location,

            IFNULL(actual_hours, 0) AS actual_hours,
            IFNULL(planned_downtime, 0) AS planned_downtime,
            IFNULL(shift_required_hours, 0) AS shift_required_hours,
            IFNULL(shift_working_hours, 0) AS shift_working_hours,
            IFNULL(shift_available_hours, 0) AS shift_available_hours,
            IFNULL(mechanical_downtime, 0) AS mechanical_downtime,
            IFNULL(actual_breakdown, 0) AS actual_breakdown,
            IFNULL(actual_inspection, 0) AS actual_inspection,
            IFNULL(actual_service_time, 0) AS actual_service_time,
            IFNULL(other_lost_hours, 0) AS other_lost_hours,
            IFNULL(general_and, 0) AS general_and,
            IFNULL(other_lost_hours_variance, 0) AS other_lost_hours_variance

        FROM `tabAvailability and Utilisation`
        {where_clause}
        ORDER BY
            asset_category,
            shift_date,
            asset_name,
            FIELD(shift, 'Day', 'Night')
        """,
        values,
        as_dict=True,
    )

    for row in rows:
        row["plant_shift_availability"] = calc_availability(
            row.get("shift_required_hours"),
            row.get("shift_available_hours"),
        )
        row["plant_shift_utilisation"] = calc_utilisation(
            row.get("shift_working_hours"),
            row.get("shift_available_hours"),
        )

    grouped = build_tree(rows)
    return grouped


def build_tree(rows):
    by_category = {}

    for row in rows:
        cat = row.get("asset_category") or "Uncategorised"
        dt = row.get("shift_date")
        asset = row.get("asset_name") or ""

        by_category.setdefault(cat, {})
        by_category[cat].setdefault(dt, {})
        by_category[cat][dt].setdefault(asset, [])
        by_category[cat][dt][asset].append(row)

    out = []

    for category in sorted(by_category.keys()):
        category_rows = []
        for shift_date in by_category[category]:
            for asset_name in by_category[category][shift_date]:
                category_rows.extend(by_category[category][shift_date][asset_name])

        category_total = make_total_row(category_rows)
        category_total["asset_category"] = category
        category_total["shift_date"] = None
        category_total["asset_name"] = ""
        category_total["shift"] = ""
        category_total["location"] = ""
        category_total["indent"] = 0
        out.append(category_total)

        for shift_date in sorted(by_category[category].keys()):
            day_rows = []
            for asset_name in by_category[category][shift_date]:
                day_rows.extend(by_category[category][shift_date][asset_name])

            day_total = make_total_row(day_rows)
            day_total["asset_category"] = category
            day_total["shift_date"] = shift_date
            day_total["asset_name"] = ""
            day_total["shift"] = ""
            day_total["location"] = ""
            day_total["indent"] = 1
            out.append(day_total)

            for asset_name in sorted(by_category[category][shift_date].keys()):
                asset_rows = by_category[category][shift_date][asset_name]

                asset_total = make_total_row(asset_rows)
                asset_total["asset_category"] = category
                asset_total["shift_date"] = shift_date
                asset_total["asset_name"] = asset_name
                asset_total["shift"] = ""
                asset_total["location"] = asset_rows[0].get("location") if asset_rows else ""
                asset_total["indent"] = 2
                out.append(asset_total)

                for row in asset_rows:
                    leaf = dict(row)
                    leaf["indent"] = 3
                    out.append(leaf)

    return out


def make_total_row(rows):
    total = {
        "actual_hours": 0.0,
        "planned_downtime": 0.0,
        "shift_required_hours": 0.0,
        "shift_working_hours": 0.0,
        "shift_available_hours": 0.0,
        "mechanical_downtime": 0.0,
        "actual_breakdown": 0.0,
        "actual_inspection": 0.0,
        "actual_service_time": 0.0,
        "other_lost_hours": 0.0,
        "general_and": 0.0,
        "other_lost_hours_variance": 0.0,
    }

    for row in rows:
        total["actual_hours"] += flt(row.get("actual_hours"))
        total["planned_downtime"] += flt(row.get("planned_downtime"))
        total["shift_required_hours"] += flt(row.get("shift_required_hours"))
        total["shift_working_hours"] += flt(row.get("shift_working_hours"))
        total["shift_available_hours"] += flt(row.get("shift_available_hours"))
        total["mechanical_downtime"] += flt(row.get("mechanical_downtime"))
        total["actual_breakdown"] += flt(row.get("actual_breakdown"))
        total["actual_inspection"] += flt(row.get("actual_inspection"))
        total["actual_service_time"] += flt(row.get("actual_service_time"))
        total["other_lost_hours"] += flt(row.get("other_lost_hours"))
        total["general_and"] += flt(row.get("general_and"))
        total["other_lost_hours_variance"] += flt(row.get("other_lost_hours_variance"))

    for key in list(total.keys()):
        total[key] = r1(total[key])

    total["plant_shift_availability"] = calc_availability(
        total["shift_required_hours"],
        total["shift_available_hours"],
    )
    total["plant_shift_utilisation"] = calc_utilisation(
        total["shift_working_hours"],
        total["shift_available_hours"],
    )

    return total