import frappe
from frappe.utils import flt, getdate
import datetime

# Map technical metric names to user-friendly display names.
metrics_mapping = {
    "shift_required_hours": "Shift Required Hours",
    "shift_working_hours": "Shift Working Hours",
    "shift_breakdown_hours": "Shift Breakdown Hours",
    "shift_available_hours": "Shift Available Hours",
    "shift_other_lost_hours": "Shift Other Lost Hours"
}

def get_month_key(shift_date):
    """
    Convert shift_date to a month-year key in the format 'feb_2025'.
    """
    d = getdate(shift_date) if not isinstance(shift_date, datetime.date) else shift_date
    return d.strftime("%b_%Y").lower()

def get_months_from_entries(entries):
    """
    Build a sorted list of month dictionaries from Availability records using shift_date.
    Each dictionary has:
      - key: a lowercase month-year string (e.g., "feb_2025")
      - label: a display label (e.g., "Feb 2025")
    """
    month_set = {}
    month_dates = {}
    for entry in entries:
        if entry.get("shift_date"):
            d = getdate(entry.get("shift_date"))
            key = d.strftime("%b_%Y").lower()
            label = d.strftime("%b %Y")
            month_set[key] = label
            if key not in month_dates or d < month_dates[key]:
                month_dates[key] = d
    sorted_keys = sorted(month_dates, key=lambda k: month_dates[k])
    months = [{"key": k, "label": month_set[k]} for k in sorted_keys]
    return months

def compute_monthly_sum(entries, field, months):
    """
    Compute summed values for a given field (e.g., shift_required_hours) across the provided months.
    Returns a dict mapping month keys to sums.
    """
    sums = {m["key"]: 0 for m in months}
    for entry in entries:
        if entry.get("shift_date"):
            mk = get_month_key(entry.get("shift_date"))
            if mk in sums:
                sums[mk] += flt(entry.get(field) or 0)
    return sums

def build_row(label, indent, is_group, entries, months, metrics):
    """
    Build an aggregated row for a given grouping level.
    For each metric and each month, compute the sum and store it under a composite key:
       <month_key>_<metric>
    """
    row = {"label": label, "indent": indent, "is_group": is_group}
    for metric in metrics:
        sums = compute_monthly_sum(entries, metric, months)
        for m in months:
            key = f"{m['key']}_{metric}"
            row[key] = sums[m["key"]]
    return row

def build_availability_report_data(entries, months, metrics):
    """
    Build the hierarchical report data for Availability & Utilisation.
    The hierarchy is:
      Level 0: All Sites
      Level 1: Site (grouped by location)
      Level 2: Day (grouped by day_number)
      Level 3: Shift (grouped by shift)
      Level 4: Equipment Type (grouped by asset_category)
      Level 5: Plant (grouped by asset_name)
    Each grouping row is aggregated with the provided metrics.
    """
    data = []
    # Level 0: All Sites
    data.append(build_row("All Sites", 0, True, entries, months, metrics))
    
    # Level 1: Group by Site (location)
    sites = {}
    for entry in entries:
        site = entry.get("location") or "Unknown Site"
        sites.setdefault(site, []).append(entry)
    for site, site_entries in sorted(sites.items()):
        data.append(build_row(site, 1, True, site_entries, months, metrics))
        
        # Level 2: Group by Day (day_number)
        days = {}
        for entry in site_entries:
            day = entry.get("day_number") or "Unknown Day"
            days.setdefault(day, []).append(entry)
        for day, day_entries in sorted(days.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else x[0]):
            data.append(build_row(f"Day {day}", 2, True, day_entries, months, metrics))
            
            # Level 3: Group by Shift (shift)
            shifts = {}
            for entry in day_entries:
                shift = entry.get("shift") or "Unknown Shift"
                shifts.setdefault(shift, []).append(entry)
            for shift, shift_entries in sorted(shifts.items()):
                data.append(build_row(shift, 3, True, shift_entries, months, metrics))
                
                # Level 4: Group by Equipment Type (asset_category)
                equip_types = {}
                for entry in shift_entries:
                    eq_type = entry.get("asset_category") or "Unknown Category"
                    equip_types.setdefault(eq_type, []).append(entry)
                for eq_type, eq_entries in sorted(equip_types.items()):
                    data.append(build_row(eq_type, 4, True, eq_entries, months, metrics))
                    
                    # Level 5: Group by Plant (asset_name)
                    plants = {}
                    for entry in eq_entries:
                        plant = entry.get("asset_name") or "Unknown Plant"
                        plants.setdefault(plant, []).append(entry)
                    for plant, plant_entries in sorted(plants.items()):
                        data.append(build_row(plant, 5, False, plant_entries, months, metrics))
    
    return data

def explode_rows_by_metric(rows, months, metrics):
    """
    For each hierarchical row, output a header row (with the group label) and then five rows,
    one for each metric, as children of that group.
    The header row shows the grouping label at its current indent level.
    The metric rows are indented one level further.
    Each metric row displays the aggregated value for that metric (per month).
    """
    new_rows = []
    for row in rows:
        base_label = row.get("label")
        base_indent = row.get("indent", 0)
        
        # First, output the grouping header row (without metric values)
        header_row = {
            "label": (" " * (base_indent * 4)) + base_label,
            "indent": base_indent
        }
        for m in months:
            header_row[m["key"]] = ""
        new_rows.append(header_row)
        
        # Now, output one row per metric, indented one level further.
        for metric in metrics:
            metric_row = {}
            metric_row["label"] = (" " * ((base_indent + 1) * 4)) + metrics_mapping.get(metric, metric)
            metric_row["indent"] = base_indent + 1
            for m in months:
                metric_row[m["key"]] = row.get(f"{m['key']}_{metric}", 0)
            new_rows.append(metric_row)
    return new_rows

def get_columns(months):
    """
    Build column definitions with one column per month.
    """
    columns = [{"fieldname": "label", "label": "Hierarchy", "fieldtype": "Data", "width": 300}]
    for m in months:
        columns.append({
            "fieldname": m["key"],
            "label": m["label"],
            "fieldtype": "Float",
            "width": 150
        })
    return columns

def execute(filters=None):
    filters = filters or {}
    conditions = ""
    params = {}
    if filters.get("from_date") and filters.get("to_date"):
        conditions = "WHERE shift_date BETWEEN %(from_date)s AND %(to_date)s"
        params["from_date"] = filters.get("from_date")
        params["to_date"] = filters.get("to_date")
        
    query = f"""
        SELECT location, shift_date, day_number, shift, asset_category, asset_name,
               shift_required_hours, shift_working_hours, shift_breakdown_hours,
               shift_available_hours, shift_other_lost_hours
        FROM `tabAvailability and Utilisation`
        {conditions}
        ORDER BY location, shift_date, day_number, shift, asset_category, asset_name
    """
    entries = frappe.db.sql(query, params, as_dict=True)
    months = get_months_from_entries(entries)
    
    # Define all five metrics.
    metrics = [
        "shift_required_hours",
        "shift_working_hours",
        "shift_breakdown_hours",
        "shift_available_hours",
        "shift_other_lost_hours"
    ]
    
    # Build hierarchical data (each row aggregates the metrics for that group).
    data = build_availability_report_data(entries, months, metrics)
    # Explode each grouping row into one header row plus five metric rows.
    data = explode_rows_by_metric(data, months, metrics)
    columns = get_columns(months)
    return columns, data
