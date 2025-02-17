import frappe
from frappe.utils import flt, getdate
import datetime

# Updated mapping of technical metric names to display labels.
metrics_mapping = {
    "shift_required_hours": "Req Hrs",
    "shift_working_hours": "Work Hrs",
    "shift_breakdown_hours": "BD Hrs",
    "shift_available_hours": "Avail Hrs",
    "shift_other_lost_hours": "Oth Lost Hrs"
}

# Define the hierarchy levels (removed Day Number)
# Level 0: Root ("All Sites")
# Level 1: Site (grouped by "location")
# Level 2: Equipment Type (grouped by "asset_category")
# Level 3: Shift (grouped by "shift")
# Level 4: Asset Name (grouped by "asset_name")
hierarchy_levels = [
    (None, None, "All Sites"),
    ("location", "Unknown Site", None),
    ("asset_category", "Unknown Category", None),
    ("shift", "Unknown Shift", None),
    ("asset_name", "Unknown Plant", None)
]

def get_month_key(shift_date):
    """Convert shift_date to a month-year key, e.g. 'feb_2025'."""
    d = getdate(shift_date) if not isinstance(shift_date, datetime.date) else shift_date
    return d.strftime("%b_%Y").lower()

def get_months_from_entries(entries):
    """
    Build a sorted list of month dictionaries from entries.
    Each dict has:
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
    return [{"key": k, "label": month_set[k]} for k in sorted_keys]

def get_week_key(shift_date):
    """Return a week key in the format 'YYYY_wkWW'."""
    d = getdate(shift_date) if not isinstance(shift_date, datetime.date) else shift_date
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}_wk{iso_week:02d}"

def get_week_label(shift_date):
    """Return a week label, e.g. 'Week 06, 2025'."""
    d = getdate(shift_date) if not isinstance(shift_date, datetime.date) else shift_date
    iso_year, iso_week, _ = d.isocalendar()
    return f"Week {iso_week}, {iso_year}"

def get_weeks_from_entries(entries):
    """
    Build a sorted list of week dictionaries from entries.
    Each dict has:
      - key: a string like "2025_wk06"
      - label: e.g. "Week 06, 2025"
      - month: the month key (e.g., "feb_2025") from shift_date
    """
    week_set = {}
    week_dates = {}
    for entry in entries:
        if entry.get("shift_date"):
            d = getdate(entry.get("shift_date"))
            wk_key = get_week_key(d)
            wk_label = get_week_label(d)
            mo_key = get_month_key(d)
            week_set[wk_key] = {"label": wk_label, "month": mo_key}
            if wk_key not in week_dates or d < week_dates[wk_key]:
                week_dates[wk_key] = d
    sorted_keys = sorted(week_dates, key=lambda k: week_dates[k])
    return [{"key": k, "label": week_set[k]["label"], "month": week_set[k]["month"]} for k in sorted_keys]

def get_day_key(shift_date):
    """Return a day key in the format 'YYYY-mm-dd'."""
    d = getdate(shift_date) if not isinstance(shift_date, datetime.date) else shift_date
    return d.strftime("%Y-%m-%d")

def get_day_label(shift_date):
    """Return a day label, e.g. '17 Feb 2025'."""
    d = getdate(shift_date) if not isinstance(shift_date, datetime.date) else shift_date
    return d.strftime("%d %b %Y")

def get_days_from_entries(entries):
    """
    Build a sorted list of day dictionaries from entries.
    Each dict has:
      - key: a string like "2025-02-17"
      - label: e.g. "17 Feb 2025"
    """
    day_set = {}
    day_dates = {}
    for entry in entries:
        if entry.get("shift_date"):
            d = getdate(entry.get("shift_date"))
            key = get_day_key(d)
            label = get_day_label(d)
            day_set[key] = label
            if key not in day_dates or d < day_dates[key]:
                day_dates[key] = d
    sorted_keys = sorted(day_dates, key=lambda k: day_dates[k])
    return [{"key": k, "label": day_set[k]} for k in sorted_keys]

def compute_monthly_sums(entries, periods, metrics):
    """
    For a list of entries, compute the sum for each metric per month.
    Returns a dict with keys "<period_key>_<metric>".
    """
    sums = {}
    for p in periods:
        for metric in metrics:
            sums[f"{p['key']}_{metric}"] = 0
    for entry in entries:
        if entry.get("shift_date"):
            mk = get_month_key(entry.get("shift_date"))
            for metric in metrics:
                key = f"{mk}_{metric}"
                sums[key] += flt(entry.get(metric) or 0)
    return sums

def compute_weekly_sums(entries, periods, metrics):
    """
    For a list of entries, compute the sum for each metric per week.
    Returns a dict with keys "<period_key>_<metric>".
    """
    sums = {}
    for p in periods:
        for metric in metrics:
            sums[f"{p['key']}_{metric}"] = 0
    for entry in entries:
        if entry.get("shift_date"):
            wk = get_week_key(entry.get("shift_date"))
            for metric in metrics:
                key = f"{wk}_{metric}"
                sums[key] += flt(entry.get(metric) or 0)
    return sums

def compute_daily_sums(entries, periods, metrics):
    """
    For a list of entries, compute the sum for each metric per day.
    Returns a dict with keys "<period_key>_<metric>".
    """
    sums = {}
    for p in periods:
        for metric in metrics:
            sums[f"{p['key']}_{metric}"] = 0
    for entry in entries:
        if entry.get("shift_date"):
            dk = get_day_key(entry.get("shift_date"))
            for metric in metrics:
                key = f"{dk}_{metric}"
                sums[key] += flt(entry.get(metric) or 0)
    return sums

def build_tree(entries, level_index, periods, metrics, compute_sums_fn, parent_indent=0):
    """
    Recursively build a tree for the grouping hierarchy.
    Each node is a dict with:
      - label, indent, sums, children
    """
    node = {}
    indent = parent_indent

    if level_index == 0:
        node["label"] = hierarchy_levels[0][2]  # "All Sites"
        filtered = entries
    else:
        filtered = entries

    node["sums"] = compute_sums_fn(filtered, periods, metrics)
    node["indent"] = indent
    node["children"] = []

    if level_index + 1 < len(hierarchy_levels):
        group_field, default_value, label_prefix = hierarchy_levels[level_index + 1]
        groups = {}
        for entry in filtered:
            key = entry.get(group_field) or default_value
            groups.setdefault(key, []).append(entry)
        for group_value in sorted(groups):
            child_node = build_tree(groups[group_value], level_index + 1, periods, metrics, compute_sums_fn, indent + 1)
            child_node["label"] = f"{label_prefix}{group_value}" if label_prefix else group_value
            child_node["indent"] = indent + 1
            node["children"].append(child_node)
    return node

def flatten_tree_exploded(nodes, periods, metrics):
    """
    Flatten the tree into a list of rows.
    For each node, add a header row, then one row per metric,
    then process children recursively.
    """
    rows = []
    for node in nodes:
        base_label = node.get("label", "")
        base_indent = node.get("indent", 0)
        header = {
            "label": base_label,
            "indent": base_indent,
            "is_group": True
        }
        for p in periods:
            header[p["key"]] = ""
        rows.append(header)
        for metric in metrics:
            row = {
                "label": (" " * ((base_indent + 1) * 4)) + metrics_mapping[metric],
                "indent": base_indent + 1,
                "is_group": False
            }
            for p in periods:
                row[p["key"]] = node["sums"].get(f"{p['key']}_{metric}", 0)
            rows.append(row)
        if node.get("children"):
            rows.extend(flatten_tree_exploded(node["children"], periods, metrics))
    return rows

def get_columns(periods, main_header="Hierarchy"):
    """
    Build column definitions based on periods.
    """
    columns = [{"fieldname": "label", "label": main_header, "fieldtype": "Data", "width": 300}]
    for p in periods:
        columns.append({
            "fieldname": p["key"],
            "label": p["label"],
            "fieldtype": "Float",
            "width": 150
        })
    return columns

def execute(filters=None):
    filters = filters or {}
    conditions = ""
    params = {}

    # Date filters
    if filters.get("from_date") and filters.get("to_date"):
        conditions = "WHERE shift_date BETWEEN %(from_date)s AND %(to_date)s"
        params["from_date"] = filters.get("from_date")
        params["to_date"] = filters.get("to_date")

    # Site filter
    if filters.get("site"):
        if conditions:
            conditions += " AND location = %(site)s"
        else:
            conditions = "WHERE location = %(site)s"
        params["site"] = filters.get("site")

    # Asset Category filter
    if filters.get("asset_category"):
        if conditions:
            conditions += " AND asset_category = %(asset_category)s"
        else:
            conditions = "WHERE asset_category = %(asset_category)s"
        params["asset_category"] = filters.get("asset_category")
    
    # Asset Name filter
    if filters.get("asset_name"):
        if conditions:
            conditions += " AND asset_name = %(asset_name)s"
        else:
            conditions = "WHERE asset_name = %(asset_name)s"
        params["asset_name"] = filters.get("asset_name")

    query = f"""
        SELECT location, shift_date, shift, asset_category, asset_name,
               shift_required_hours, shift_working_hours, shift_breakdown_hours,
               shift_available_hours, shift_other_lost_hours
        FROM `tabAvailability and Utilisation`
        {conditions}
        ORDER BY location, shift_date, shift, asset_category, asset_name
    """
    entries = frappe.db.sql(query, params, as_dict=True)
    metrics = [
        "shift_required_hours",
        "shift_working_hours",
        "shift_breakdown_hours",
        "shift_available_hours",
        "shift_other_lost_hours"
    ]

    # Determine display mode: Days, Weeks, or Months (default)
    display_by = (filters.get("display_by") or "Months").lower()
    if display_by in ["week", "weeks"]:
        weeks = get_weeks_from_entries(entries)
        # Optionally, you can add a month filter logic here if needed
        periods = weeks
        compute_sums_fn = compute_weekly_sums
        main_header = "Hierarchy (Weeks)"
    elif display_by in ["day", "days"]:
        days = get_days_from_entries(entries)
        periods = days
        compute_sums_fn = compute_daily_sums
        main_header = "Hierarchy (Days)"
    else:
        # Default to Months
        periods = get_months_from_entries(entries)
        compute_sums_fn = compute_monthly_sums
        main_header = "Hierarchy (Months)"

    tree = build_tree(entries, 0, periods, metrics, compute_sums_fn)
    data = flatten_tree_exploded([tree], periods, metrics)
    columns = get_columns(periods, main_header=main_header)

    # Build chart data for BD Hrs, Avail Hrs and Other Lost Hrs using root node sums.
    chart_data = {
        "data": {
            "labels": [p["label"] for p in periods],
            "datasets": [
                {
                    "name": "BD Hrs",
                    "values": [tree["sums"].get(f"{p['key']}_shift_breakdown_hours", 0) for p in periods]
                },
                {
                    "name": "Avail Hrs",
                    "values": [tree["sums"].get(f"{p['key']}_shift_available_hours", 0) for p in periods]
                },
                {
                    "name": "Other Lost Hrs",
                    "values": [tree["sums"].get(f"{p['key']}_shift_other_lost_hours", 0) for p in periods]
                }
            ]
        },
        "type": "line",
        "fieldtype": "Float"
    }

    return columns, data, None, chart_data, [], None
