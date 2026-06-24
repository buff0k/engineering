import frappe
from urllib.parse import quote
from frappe.utils import flt, getdate, add_days, date_diff

from engineering.engineering.report.availability_and_utilisation_month_end_report import (
    availability_and_utilisation_month_end_report as month_end,
)


_ = frappe._

CATEGORY_MAP = {
    "ADT": "ADT",
    "ADT's": "ADT",
    "Dozer": "Dozer",
    "Dozer's": "Dozer",
    "Excavator": "Excavator",
    "Excavator's": "Excavator",
    "Grader": "Grader",
    "Service Truck": "Service Truck",
    "TLB": "TLB",
    "Water Bowser": "Water Bowser",
    "Diesel Bowsers": "Diesel Bowsers",
    "Drills": "Drills",
    "Loader": "Loader",
}

UI_CATEGORIES = [
    "ADT",
    "Dozer",
    "Excavator",
    "Grader",
    "Service Truck",
    "TLB",
    "Water Bowser",
    "Diesel Bowsers",
    "Drills",
    "Loader",
]

UI_TITLES = {
    "ADT": "ADT",
    "Dozer": "DOZER",
    "Excavator": "EXCAVATOR",
    "Grader": "GRADER",
    "Service Truck": "SERVICE TRUCK",
    "TLB": "TLB",
    "Water Bowser": "WATER BOWSER",
    "Diesel Bowsers": "DIESEL BOWSERS",
    "Drills": "DRILLS",
    "Loader": "LOADER",
}



def get_site_colour_map():
    """Return site header colours from Production Dashboard Setup singleton.

    This keeps the Daily Availability Dashboard aligned with the shared
    dashboard colour setup instead of hardcoding colours in this page.
    """
    try:
        setup = frappe.get_single("Production Dashboard Setup")
    except Exception:
        frappe.clear_messages()
        return {}

    colour_map = {}

    for row in setup.get("site_colour_mapping") or []:
        site = (row.location or "").strip()
        colour = (row.colour or "").strip()

        if site and colour:
            colour_map[site] = colour

    return colour_map


def get_site_header_colour(location):
    if not location:
        return "#f7f7f7"

    return get_site_colour_map().get(str(location).strip()) or "#f7f7f7"






def get_spare_swing_asset_map(filters):
    filters = filters or {}

    start_date = filters.get("start_date") or filters.get("from_date")
    end_date = filters.get("end_date") or filters.get("to_date")
    location = filters.get("location") or filters.get("site")

    if not start_date or not end_date:
        return {}

    args = {
        "start_date": start_date,
        "end_date": end_date,
    }

    conditions = [
        "mpp.docstatus < 2",
        "mpp.prod_month_start_date <= %(end_date)s",
        "mpp.prod_month_end_date >= %(start_date)s",
    ]

    if location:
        conditions.append("mpp.location = %(location)s")
        args["location"] = location

    condition_sql = " AND ".join(conditions)
    spare_map = {}

    def add_reason(asset_name, reason):
        if not asset_name:
            return

        asset_name = str(asset_name).strip()

        if not asset_name:
            return

        spare_map.setdefault(asset_name, set()).add(reason)

    try:
        truck_rows = frappe.db.sql(f"""
            SELECT DISTINCT etl.truck AS asset_name
            FROM `tabMonthly Production Planning` mpp
            INNER JOIN `tabExcavator Truck Link` etl
                ON etl.parent = mpp.name
               AND etl.parenttype = 'Monthly Production Planning'
            WHERE {condition_sql}
              AND IFNULL(etl.truck, '') != ''
              AND IFNULL(etl.excavator, '') = ''
        """, args, as_dict=True)

        for row in truck_rows:
            add_reason(row.get("asset_name"), "Spare/Swing unit Truck")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Daily Dashboard Spare/Swing Trucks")
        frappe.clear_messages()

    try:
        excavator_rows = frappe.db.sql(f"""
            SELECT DISTINCT etl.excavator AS asset_name
            FROM `tabMonthly Production Planning` mpp
            INNER JOIN `tabExcavator Truck Link` etl
                ON etl.parent = mpp.name
               AND etl.parenttype = 'Monthly Production Planning'
            WHERE {condition_sql}
              AND IFNULL(etl.excavator, '') != ''
              AND IFNULL(etl.truck, '') = ''
              AND NOT EXISTS (
                  SELECT 1
                  FROM `tabExcavator Truck Link` assigned_etl
                  WHERE assigned_etl.parent = etl.parent
                    AND assigned_etl.parenttype = etl.parenttype
                    AND assigned_etl.excavator = etl.excavator
                    AND IFNULL(assigned_etl.truck, '') != ''
              )
        """, args, as_dict=True)

        for row in excavator_rows:
            add_reason(row.get("asset_name"), "Spare/Swing unit Excavator")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Daily Dashboard Spare/Swing Excavators")
        frappe.clear_messages()

    try:
        dozer_meta = frappe.get_meta("Dozers Planned")

        dozer_asset_field = None

        for fieldname in ("asset_name", "dozer", "asset"):
            if dozer_meta.has_field(fieldname):
                dozer_asset_field = fieldname
                break

        dozer_type_field = "dozing_type" if dozer_meta.has_field("dozing_type") else None

        if dozer_asset_field and dozer_type_field:
            dozer_rows = frappe.db.sql(f"""
                SELECT DISTINCT dp.`{dozer_asset_field}` AS asset_name
                FROM `tabMonthly Production Planning` mpp
                INNER JOIN `tabDozers Planned` dp
                    ON dp.parent = mpp.name
                   AND dp.parenttype = 'Monthly Production Planning'
                WHERE {condition_sql}
                  AND IFNULL(dp.`{dozer_asset_field}`, '') != ''
                  AND IFNULL(dp.`{dozer_type_field}`, '') = ''
            """, args, as_dict=True)

            for row in dozer_rows:
                add_reason(row.get("asset_name"), "Spare/Swing unit Dozer")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Daily Dashboard Spare/Swing Dozers")
        frappe.clear_messages()

    return {
        asset_name: ", ".join(sorted(reasons))
        for asset_name, reasons in spare_map.items()
    }


def apply_machine_scope_filter_to_dashboard_rows(rows, filters, spare_swing_asset_map):
    filters = filters or {}
    machine_scope = filters.get("machine_scope") or "Include Swing/Spare"

    if machine_scope == "Include Swing/Spare":
        return rows

    filtered_rows = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        machine = get_machine(row)

        if not machine:
            continue

        is_spare = bool(machine in (spare_swing_asset_map or {}))

        if machine_scope == "Production Machines" and not is_spare:
            filtered_rows.append(row)

        elif machine_scope == "Swing/Spare Machines" and is_spare:
            filtered_rows.append(row)

    return filtered_rows



def build_summary_averages_from_machine_series(machine_series):
    out = {category: {"avail": None, "util": None} for category in UI_CATEGORIES}

    for category in UI_CATEGORIES:
        machines = machine_series.get(category) or []

        avail_values = [
            float(row.get("avail"))
            for row in machines
            if isinstance(row, dict) and row.get("avail") is not None
        ]

        util_values = [
            float(row.get("util"))
            for row in machines
            if isinstance(row, dict) and row.get("util") is not None
        ]

        out[category] = {
            "avail": (sum(avail_values) / len(avail_values)) if avail_values else None,
            "util": (sum(util_values) / len(util_values)) if util_values else None,
        }

    return out

def execute(filters=None):
    filters = frappe._dict(filters or {})

    if filters.get("site") and not filters.get("location"):
        filters["location"] = filters.get("site")

    if filters.get("location") and not filters.get("site"):
        filters["site"] = filters.get("location")

    summary_type = filters.get("summary_type") or "Daily Summary"
    start_date = filters.get("start_date") or filters.get("from_date")
    end_date = filters.get("end_date") or filters.get("to_date")
    location = filters.get("location") or filters.get("site")
    machine_scope = filters.get("machine_scope") or "Include Swing/Spare"

    if not start_date:
        frappe.throw("Please select Start Date.")

    if not end_date:
        frappe.throw("Please select End Date.")

    if not location:
        frappe.throw("Please select Site.")

    source_rows = fetch_grouped_data(location, start_date, end_date, machine_scope)

    spare_swing_asset_map = get_spare_swing_asset_map(filters)
    source_rows = apply_machine_scope_filter_to_dashboard_rows(source_rows, filters, spare_swing_asset_map)

    machine_series = build_machine_series_from_source_rows(source_rows)
    avgs = build_summary_averages_from_source_rows(source_rows)


    dashboard_html = build_dashboard_html(
        location,
        start_date,
        end_date,
        avgs,
        machine_series,
        source_rows,
        summary_type,
        machine_scope,
        spare_swing_asset_map
    )

    columns = [{"label": "", "fieldname": "noop", "fieldtype": "Data", "width": 1}]
    data = [{"noop": ""}]

    return columns, data, dashboard_html


def fetch_grouped_data(location, start_date, end_date, machine_scope=None):
    result = month_end.execute(
        frappe._dict({
            "from_date": start_date,
            "to_date": end_date,
            "start_date": start_date,
            "end_date": end_date,
            "location": location,
            "site": location,
            "machine_scope": machine_scope or "Include Swing/Spare",
            "include_excluded_asset_categories": 1,
        })
    )

    columns = []
    rows = []

    if isinstance(result, (list, tuple)):
        if len(result) > 0:
            columns = result[0] or []

        if len(result) > 1:
            rows = result[1] or []

    else:
        rows = result or []

    return rows


def to_float(value):
    if value in (None, ""):
        return None

    if isinstance(value, str):
        value = value.replace("%", "").replace(",", "").strip()

    try:
        return float(value)
    except Exception:
        return None


def get_any(row, keys):
    for key in keys:
        if isinstance(row, dict) and row.get(key) not in (None, ""):
            return row.get(key)
    return None


def get_category(row):
    value = get_any(row, [
        "asset_category",
        "Asset Category",
        "category",
        "Category",
    ])

    if value in CATEGORY_MAP:
        return CATEGORY_MAP[value]

    return value


def get_indent(row):
    try:
        return int(row.get("indent") or 0)
    except Exception:
        return 0


def get_machine(row):
    machine = get_any(row, [
        "asset_name",
        "Asset Name",
        "asset",
        "Asset",
        "machine",
        "Machine",
        "plant_no",
        "Plant No",
    ])

    if not machine:
        return ""

    machine = str(machine).strip()

    if machine in CATEGORY_MAP:
        return ""

    return machine


def get_avail(row):
    return to_float(get_any(row, [
        "plant_shift_availability",
        "avail_percent",
        "Avail",
        "availability",
        "Availability",
    ]))


def get_util(row):
    return to_float(get_any(row, [
        "plant_shift_utilisation",
        "util_percent",
        "Util",
        "utilisation",
        "Utilisation",
    ]))


def build_summary_averages_from_source_rows(rows):
    out = {category: {"avail": None, "util": None} for category in UI_CATEGORIES}

    for row in rows:
        if not isinstance(row, dict):
            continue

        category = get_category(row)

        if category not in out:
            continue

        machine = get_machine(row)

        if machine:
            continue

        out[category] = {
            "avail": get_avail(row),
            "util": get_util(row),
        }

    for category in UI_CATEGORIES:
        if out[category]["avail"] is not None or out[category]["util"] is not None:
            continue

        category_rows = [
            row for row in rows
            if isinstance(row, dict) and get_category(row) == category
        ]

        if not category_rows:
            continue

        min_indent = min(get_indent(row) for row in category_rows)
        parent_rows = [row for row in category_rows if get_indent(row) == min_indent]

        if parent_rows:
            row = parent_rows[0]
            out[category] = {
                "avail": get_avail(row),
                "util": get_util(row),
            }

    return out


def build_machine_series_from_source_rows(rows):
    buckets = {category: {} for category in UI_CATEGORIES}

    for row in rows:
        if not isinstance(row, dict):
            continue

        category = get_category(row)

        if category not in buckets:
            continue

        machine = get_machine(row)

        if not machine:
            continue

        if machine not in buckets[category]:
            buckets[category][machine] = {
                "avail_values": [],
                "util_values": [],
            }

        av = get_avail(row)
        ut = get_util(row)

        if av is not None:
            buckets[category][machine]["avail_values"].append(av)

        if ut is not None:
            buckets[category][machine]["util_values"].append(ut)

    output = {}

    for category in UI_CATEGORIES:
        output[category] = []

        for machine, vals in sorted(buckets[category].items()):
            av_values = vals["avail_values"]
            ut_values = vals["util_values"]

            output[category].append({
                "machine": machine,
                "avail": (sum(av_values) / len(av_values)) if av_values else None,
                "util": (sum(ut_values) / len(ut_values)) if ut_values else None,
            })

    return output


def bubble_colour(metric, value):
    if value is None:
        return "isd-mbubble-red"

    value = float(value)

    if metric == "avail":
        if value >= 85:
            return "isd-mbubble-green"
        if value >= 75:
            return "isd-mbubble-yellow"
        return "isd-mbubble-red"

    if value >= 80:
        return "isd-mbubble-green"
    if value >= 70:
        return "isd-mbubble-yellow"
    return "isd-mbubble-red"


def fmt_percent(value):
    if value is None:
        return "0.0%"
    return f"{float(value):.1f}%"


def esc(value):
    return frappe.utils.escape_html(str(value or ""))









def get_adt_dozer_excavator_cards_all_summary_types(location, start_date, end_date, machine_scope):
    """
    ADT, Dozer, Excavator cards for all summary types.
    Reads Production > Avail and Util report top rows only.
    """
    out = {
        "ADT": {"avail": 0.0, "util": 0.0},
        "Dozer": {"avail": 0.0, "util": 0.0},
        "Excavator": {"avail": 0.0, "util": 0.0},
    }

    def clean_number(value):
        if value in (None, ""):
            return None
        if isinstance(value, str):
            value = value.replace("%", "").replace(",", "").strip()
        try:
            return float(value)
        except Exception:
            return None

    def norm(value):
        return (
            str(value or "")
            .strip()
            .lower()
            .replace(" ", "")
            .replace("_", "")
            .replace("-", "")
            .replace("'", "")
        )

    category_map = {
        "adt": "ADT",
        "adts": "ADT",
        "dozer": "Dozer",
        "dozers": "Dozer",
        "excavator": "Excavator",
        "excavators": "Excavator",
    }

    try:
        from frappe.desk.query_report import run

        report_data = run(
            "Avail and Util report",
            filters={
                "start_date": start_date,
                "end_date": end_date,
                "from_date": start_date,
                "to_date": end_date,
                "location": location,
                "site": location,
                "machine_scope": machine_scope or "Production Machines",
            },
            ignore_prepared_report=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Dashboard ADT Dozer Excavator Cards Error")
        return out

    rows = []

    if isinstance(report_data, dict):
        rows = report_data.get("result") or report_data.get("data") or []
    elif isinstance(report_data, (list, tuple)) and len(report_data) > 1:
        rows = report_data[1] or []
    elif isinstance(report_data, list):
        rows = report_data

    for row in rows or []:
        if not isinstance(row, dict):
            continue

        try:
            indent = int(row.get("indent") or 0)
        except Exception:
            indent = 0

        if indent != 0:
            continue

        raw_category = (
            row.get("asset_category")
            or row.get("Asset Category")
            or row.get("category")
            or row.get("Category")
            or ""
        )

        category = category_map.get(norm(raw_category))

        if category not in out:
            continue

        avail = clean_number(
            row.get("plant_shift_availability")
            if row.get("plant_shift_availability") not in (None, "")
            else row.get("Avail (%)")
        )

        util = clean_number(
            row.get("plant_shift_utilisation")
            if row.get("plant_shift_utilisation") not in (None, "")
            else row.get("Util (%)")
        )

        if avail is not None:
            out[category]["avail"] = avail

        if util is not None:
            out[category]["util"] = util

    return out



def build_dashboard_html(location, start_date, end_date, avgs, machine_series, source_rows=None, summary_type="Daily Summary", machine_scope="Include Swing/Spare", spare_swing_asset_map=None):
    site_safe = esc(location)
    summary_type_safe = esc(summary_type or "Daily Summary")
    header_colour = get_site_header_colour(location)
    adt_dozer_excavator_cards_all_summary_types = get_adt_dozer_excavator_cards_all_summary_types(
        location,
        start_date,
        end_date,
        machine_scope or "Production Machines"
    )

    # IMPORTANT:
    # Build the graph from the same ADT / Dozer / Excavator values as the cards.
    # This must happen BEFORE chart_html is created.
    avgs = dict(avgs or {})

    for _cat in ("ADT", "Dozer", "Excavator"):
        _forced_vals = adt_dozer_excavator_cards_all_summary_types.get(_cat)

        if _forced_vals:
            _current_vals = dict(avgs.get(_cat) or {})
            _current_vals["avail"] = _forced_vals.get("avail", _current_vals.get("avail"))
            _current_vals["util"] = _forced_vals.get("util", _current_vals.get("util"))
            avgs[_cat] = _current_vals

    metric_cards = []

    month_end_url = (
        "/desk/query-report/Availability%20and%20Utilisation%20Month%20End%20Report"
        f"?from_date={quote(str(start_date or ''))}"
        f"&to_date={quote(str(end_date or ''))}"
        f"&location={quote(str(location or ''))}"
        f"&machine_scope={quote(str(machine_scope or 'Include Swing/Spare'))}"
    )

    for category in UI_CATEGORIES:
        values = avgs.get(category) or {}

        if category in ("ADT", "Dozer", "Excavator"):
            values = adt_dozer_excavator_cards_all_summary_types.get(category) or values

        av = values.get("avail")
        ut = values.get("util")

        metric_cards.append(f'''
<div class="isd-metric">
    <div class="isd-metric-title">{esc(category)} Avg</div>

    <div class="isd-pill-row">
        <div class="isd-mbubble {bubble_colour('avail', av)}" onclick="window.open('{month_end_url}', '_blank')" title="Open Month End Report" style="cursor:pointer;">
            <div class="isd-mbubble-label">Availability</div>
            <div class="isd-mbubble-value">{fmt_percent(av)}</div>
        </div>

        <div class="isd-mbubble {bubble_colour('util', ut)}" onclick="window.open('{month_end_url}', '_blank')" title="Open Month End Report" style="cursor:pointer;">
            <div class="isd-mbubble-label">Utilisation</div>
            <div class="isd-mbubble-value">{fmt_percent(ut)}</div>
        </div>
    </div>
</div>
''')

    chart_html = build_selected_summary_chart_html(
        summary_type,
        location,
        source_rows or [],
        avgs,
        machine_series,
        start_date,
        end_date,
        machine_scope,
        spare_swing_asset_map
    )
    trend_html = build_trend_html(location, start_date, end_date, machine_scope)

    return f'''
<div class="isd-hourly-dashboard isd-daily-availability-dashboard">
    <div class="isd-note">
        Showing: {summary_type_safe} | {site_safe} | {start_date} to {end_date}. Averages and graphs are read from Availability and Utilisation Month End Report.
    </div>

    <div class="isd-site">
        <div class="isd-site-title">{summary_type_safe} | {site_safe} | {start_date} to {end_date}</div>

        <div class="isd-band" style="--site-colour:{header_colour}">
            <div class="isd-metrics">
                {''.join(metric_cards)}
            </div>
        </div>

        <div class="isd-contentrow">
            {chart_html}
            {trend_html}
        </div>
    </div>
</div>
'''




def get_row_date(row):
    value = get_any(row, [
        "date",
        "Date",
        "posting_date",
        "Posting Date",
        "transaction_date",
        "Transaction Date",
        "shift_date",
        "Shift Date",
        "work_date",
        "Work Date",
        "from_date",
        "From Date",
    ])

    if not value:
        return ""

    return str(value)[:10]


def avg_or_none(values):
    values = [float(v) for v in values if v is not None]
    if not values:
        return None
    return sum(values) / len(values)


def daily_height(value):
    if value is None:
        return 2

    try:
        value = float(value)
    except Exception:
        return 2

    value = max(0.0, min(100.0, value))

    if value <= 0:
        return 2

    # Align bars with Y-axis percentage scale.
    # Chart plot height is 220px:
    # 100% = 220px
    # 75%  = 165px
    # 62.5% = 138px
    return max(2, int(round((value / 100.0) * 220)))



def dashboard_bar_height(value):
    if value is None:
        return 2

    try:
        value = float(value)
    except Exception:
        return 2

    value = max(0.0, min(100.0, value))

    if value <= 0:
        return 2

    return max(2, int(round((value / 100.0) * 220)))

def build_selected_summary_chart_html(summary_type, location, source_rows, avgs, machine_series, start_date, end_date, machine_scope="Include Swing/Spare", spare_swing_asset_map=None):
    summary_type = summary_type or "Daily Summary"

    if summary_type == "Daily Summary":
        return build_daily_summary_chart_html(location, start_date, end_date, machine_scope)

    if summary_type == "Weekly Summary":
        return build_weekly_summary_chart_html(avgs, machine_scope)

    if summary_type == "Monthly Summary":
        return build_monthly_summary_chart_html(avgs, machine_scope)

    return build_chart_html(machine_series, machine_scope, spare_swing_asset_map)


def build_daily_summary_chart_html(location, start_date, end_date, machine_scope="Include Swing/Spare"):
    all_dates = []

    try:
        start = getdate(start_date)
        end = getdate(end_date)
        total_days = date_diff(end, start) + 1

        for i in range(max(total_days, 0)):
            all_dates.append(str(add_days(start, i)))
    except Exception:
        all_dates = []

    if not all_dates:
        return f'''
<div class="isd-chart-stack">
    <div class="isd-chart-section">
        <div class="isd-chart-section-title">FULL DAY AVERAGE AVAILABILITY &amp; UTILISATION - {esc(machine_scope or "Include Swing/Spare").upper()}</div>
        <div class="isd-no-machine-data">No daily summary data found for the selected date range.</div>
    </div>
</div>
'''

    daily_category_values = {}

    for date_value in all_dates:
        day_rows = fetch_grouped_data(location, date_value, date_value, machine_scope)
        day_avgs = build_summary_averages_from_source_rows(day_rows)

        for category in UI_CATEGORIES:
            values = day_avgs.get(category) or {}

            daily_category_values[(category, date_value)] = {
                "avail": values.get("avail") if values.get("avail") is not None else 0.0,
                "util": values.get("util") if values.get("util") is not None else 0.0,
            }

    bars = []
    day_labels = []
    group_labels = []
    total_day_count = 0

    for category in UI_CATEGORIES:
        for date_value in all_dates:
            day = str(date_value)[8:10]
            values = daily_category_values.get((category, date_value)) or {}

            av = values.get("avail")
            ut = values.get("util")

            if av is None:
                av = 0.0

            if ut is None:
                ut = 0.0

            bars.append(
                f"<div class='isd-bar avail' title='{esc(category)} {day} Availability: {fmt_percent(av)}' style='height:{daily_height(av)}px'></div>"
            )

            bars.append(
                f"<div class='isd-bar util' title='{esc(category)} {day} Utilisation: {fmt_percent(ut)}' style='height:{daily_height(ut)}px'></div>"
            )

            day_labels.append(f"<div class='isd-machinelab'>{esc(day)}</div>")

        group_labels.append(
            f"<div class='isd-summary-group-label' style='grid-column: span {len(all_dates)};'>{esc(UI_TITLES.get(category, category))}</div>"
        )

        total_day_count += len(all_dates)

    grid_template = f"repeat({total_day_count * 2}, minmax(18px, 1fr))"
    day_template = f"repeat({total_day_count}, minmax(44px, 1fr))"
    min_width = max(1200, total_day_count * 58)

    return f'''
<div class="isd-chart-stack">
    <div class="isd-chart-section">
        <div class="isd-chart-section-title">FULL DAY AVERAGE AVAILABILITY &amp; UTILISATION - {esc(machine_scope or "Include Swing/Spare").upper()}</div>

        <div class="isd-chart" style="min-width:{min_width}px;">
            <div class="isd-yaxis">
                <div>100%</div>
                <div>90%</div>
                <div>80%</div>
                <div>70%</div>
                <div>60%</div>
                <div>50%</div>
                <div>40%</div>
                <div>30%</div>
                <div>20%</div>
                <div>10%</div>
                <div>0%</div>
            </div>

            <div class="isd-avgline isd-avg-85"></div>
            <div class="isd-avgline isd-avg-80"></div>

            <div class="isd-chart-grid" style="grid-template-columns:{grid_template};">
                {''.join(bars)}
            </div>

            <div class="isd-machinelabels" style="grid-template-columns:{day_template};">
                {''.join(day_labels)}
                {''.join(group_labels)}
            </div>
        </div>
    </div>
</div>
'''



def build_weekly_summary_chart_html(avgs, machine_scope="Include Swing/Spare"):
    top_categories = ["ADT", "Excavator", "Dozer"]
    bottom_categories = ["Grader", "Service Truck", "TLB", "Water Bowser", "Diesel Bowsers", "Drills", "Loader"]

    machine_scope_safe = esc(machine_scope or "Include Swing/Spare")

    top_title = f"Weekly Summary- ADT / EXCAVATOR / DOZER- {machine_scope_safe}"
    bottom_title = f"Weekly Summary- SUPPORT EQUIPMENT & DRILLS- {machine_scope_safe}"

    return f'''
<div class="isd-chart-stack">
    {build_monthly_summary_section(top_title, top_categories, avgs)}
    {build_monthly_summary_section(bottom_title, bottom_categories, avgs)}
</div>
'''

def build_monthly_summary_chart_html(avgs, machine_scope="Include Swing/Spare"):
    top_categories = ["ADT", "Excavator", "Dozer"]
    bottom_categories = ["Grader", "Service Truck", "TLB", "Water Bowser", "Diesel Bowsers", "Drills", "Loader"]

    machine_scope_safe = esc(machine_scope or "Include Swing/Spare")

    top_title = f"Monthly Summary - ADT / EXCAVATOR / DOZER- {machine_scope_safe}"
    bottom_title = f"Monthly Summary - SUPPORT EQUIPMENT & DRILLS- {machine_scope_safe}"

    return f'''
<div class="isd-chart-stack">
    {build_monthly_summary_section(top_title, top_categories, avgs)}
    {build_monthly_summary_section(bottom_title, bottom_categories, avgs)}
</div>
'''

def build_monthly_summary_section(title, categories, avgs):
    bars = []
    labels = []

    for category in categories:
        values = avgs.get(category) or {}
        av = values.get("avail")
        ut = values.get("util")

        av_class = "isd-bar avail" + (" nodata" if av is None else "")
        ut_class = "isd-bar util" + (" nodata" if ut is None else "")

        bars.append(f"<div class='{av_class}' title='{esc(category)} Availability: {fmt_percent(av)}' style='height:{daily_height(av)}px'></div>")
        bars.append(f"<div class='{ut_class}' title='{esc(category)} Utilisation: {fmt_percent(ut)}' style='height:{daily_height(ut)}px'></div>")

        labels.append(f"<div class='isd-machinelab'>{esc(UI_TITLES.get(category, category))}</div>")

    grid_template = f"repeat({len(categories) * 2}, minmax(90px, 1fr))"
    label_template = f"repeat({len(categories)}, minmax(180px, 1fr))"

    return f'''
<div class="isd-chart-section">
    <div class="isd-chart-section-title">{esc(title)}</div>

    <div class="isd-chart" style="min-width:100%;">
        <div class="isd-yaxis">
            <div>100%</div><div>90%</div><div>80%</div><div>70%</div><div>60%</div>
            <div>50%</div><div>40%</div><div>30%</div><div>20%</div><div>10%</div><div>0%</div>
        </div>

        <div class="isd-avgline isd-avg-85"></div>
        <div class="isd-avgline isd-avg-80"></div>

        <div class="isd-chart-grid" style="grid-template-columns:{grid_template};">
            {''.join(bars)}
        </div>

        <div class="isd-machinelabels" style="grid-template-columns:{label_template};">
            {''.join(labels)}
        </div>
    </div>
</div>
'''


def build_trend_html(location, start_date, end_date, machine_scope="Include Swing/Spare"):

    avail_util_url = (
        "/app/query-report/Avail%20and%20Util%20report"
        f"?start_date={quote(str(start_date or ''))}"
        f"&end_date={quote(str(end_date or ''))}"
        f"&location={quote(str(location or ''))}"
        f"&machine_scope={quote(str(machine_scope or 'Include Swing/Spare'))}"
    )

    return f'''
<div class="isd-side">

    <div class="isd-targets">
        <div class="isd-target-box">


            <div id="open-avail-util-only-button" onclick="window.open('{avail_util_url}', '_blank')" style="width:120px;min-height:34px;border:2px solid #0d6efd;border-radius:6px;background:#dbeafe;color:#000000;font-size:12px;font-weight:800;line-height:1.05;text-align:center;display:flex;align-items:center;justify-content:center;cursor:pointer;padding:4px;box-sizing:border-box;">Open Avail Util</div>

<div class="isd-target-title">Availability<br>Target</div>
            <div class="isd-target-line isd-target-line-red"></div>
        </div>

        <div class="isd-target-box">
            <div class="isd-target-title">Utilization<br>Target</div>
            <div class="isd-target-line isd-target-line-green"></div>
        </div>
    </div>

    <div class="isd-legend">
        <span class="isd-legitem"><i class="isd-legswatch isd-leg-avail"></i>Availability</span>
        <span class="isd-legitem"><i class="isd-legswatch isd-leg-util"></i>Utilisation</span>
    </div>
</div>
'''


def build_chart_html(machine_series, machine_scope="Include Swing/Spare", spare_swing_asset_map=None):
    spare_swing_asset_map = spare_swing_asset_map or {}
    machine_scope = machine_scope or "Include Swing/Spare"

    def height(value):
        if value is None:
            return 2

        value = max(0.0, min(100.0, float(value)))
        return max(2, int(round(value * 2.7)))

    def chart_section(category):
        title = UI_TITLES.get(category, category)
        items = machine_series.get(category) or []

        if not items:
            return f'''
<div class="isd-chart-section">
    <div class="isd-chart-section-title">{esc(title)} AVAILABILITY &amp; UTILISATION - {esc(machine_scope or "Include Swing/Spare")}</div>
    <div class="isd-no-machine-data">No machines found for {esc(title)} in the selected date range.</div>
</div>
'''

        count = max(len(items), 1)
        grid_template = f"repeat({count * 2}, minmax(18px, 1fr))"
        label_template = f"repeat({count}, minmax(54px, 2fr))"
        min_width = max(820, count * 70)

        bars = []
        labels = []

        for item in items:
            machine_raw = str(item.get("machine") or "").strip()
            machine = esc(machine_raw)
            av = item.get("avail")
            ut = item.get("util")

            # If user selects Swing/Spare Machines, all shown machines are swing/spare.
            # If user selects Include Swing/Spare, only machines found in Monthly Planning spare map are purple.
            is_spare_swing = (
                machine_scope == "Swing/Spare Machines"
                or bool(machine_raw and machine_raw in spare_swing_asset_map)
            )

            av_class = "isd-bar avail" + (" nodata" if av is None else "")
            ut_class = "isd-bar util" + (" nodata" if ut is None else "")

            label_style = ""
            label_class = "isd-machinelab"

            if is_spare_swing:
                label_class = "isd-machinelab isd-machinelab-swing"
                label_style = "color:#d291ff !important;font-weight:900 !important;text-shadow:1px 1px 3px #000000 !important;"

            bars.append(
                f"<div class='{av_class}' title='{machine} Availability: {fmt_percent(av)}' style='height:{height(av)}px'></div>"
            )

            bars.append(
                f"<div class='{ut_class}' title='{machine} Utilisation: {fmt_percent(ut)}' style='height:{height(ut)}px'></div>"
            )

            labels.append(
                f"<div class='{label_class}' title='{machine}' style='{label_style}'><span style='{label_style}'>{machine}</span></div>"
            )

        return f'''
<div class="isd-chart-section">
    <div class="isd-chart-section-title">{esc(title)} AVAILABILITY &amp; UTILISATION - {esc(machine_scope or "Include Swing/Spare")}</div>

    <div class="isd-chart" style="min-width:{min_width}px;">
        <div class="isd-yaxis">
            <div>100%</div>
            <div>90%</div>
            <div>80%</div>
            <div>70%</div>
            <div>60%</div>
            <div>50%</div>
            <div>40%</div>
            <div>30%</div>
            <div>20%</div>
            <div>10%</div>
            <div>0%</div>
        </div>

        <div class="isd-avgline isd-avg-85"></div>
        <div class="isd-avgline isd-avg-80"></div>

        <div class="isd-chart-grid" style="grid-template-columns:{grid_template};">
            {''.join(bars)}
        </div>

        <div class="isd-machinelabels" style="grid-template-columns:{label_template};">
            {''.join(labels)}
        </div>
    </div>
</div>
'''

    return f'''
<div class="isd-chart-stack">
    {''.join(chart_section(category) for category in UI_CATEGORIES)}
</div>
'''


@frappe.whitelist()
def download_daily_dashboard_pdf(start_date=None, end_date=None, location=None, site=None, summary_type=None, machine_scope=None):
    location = location or site
    summary_type = summary_type or "Daily Summary"
    machine_scope = machine_scope or "Include Swing/Spare"

    if not start_date:
        frappe.throw("Please select Start Date.")

    if not end_date:
        frappe.throw("Please select End Date.")

    if not location:
        frappe.throw("Please select Site.")

    source_rows = fetch_grouped_data(location, start_date, end_date, machine_scope)
    spare_swing_asset_map = get_spare_swing_asset_map(frappe._dict({"start_date": start_date, "end_date": end_date, "location": location, "site": location, "machine_scope": machine_scope}))
    source_rows = apply_machine_scope_filter_to_dashboard_rows(source_rows, frappe._dict({"machine_scope": machine_scope}), spare_swing_asset_map)
    avgs = build_summary_averages_from_source_rows(source_rows)
    machine_series = build_machine_series_from_source_rows(source_rows)

    dashboard_html = build_dashboard_html(location, start_date, end_date, avgs, machine_series, source_rows, summary_type, machine_scope, spare_swing_asset_map)

    html = f'''
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @page {{
            size: A4 landscape;
            margin: 6mm;
        }}

        body {{
            margin: 0;
            padding: 0;
            background: #ffffff;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}

        * {{
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}

        .isd-contentrow {{
            display: block !important;
        }}

        .isd-side {{
            display: none !important;
        }}

        .isd-chart-stack {{
            display: block !important;
            overflow: visible !important;
            padding: 0 !important;
        }}

        .isd-chart-section {{
            page-break-inside: avoid;
            break-inside: avoid;
            overflow: visible !important;
            margin-bottom: 18px !important;
        }}

        .isd-chart {{
            overflow: visible !important;
        }}
    </style>
</head>
<body>
    {dashboard_html}
</body>
</html>
'''

    pdf = frappe.utils.pdf.get_pdf(html)

    filename = f"Daily Availability and Utilisation Dashboard - {location} - {start_date} to {end_date}.pdf"

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"



def build_pdf_dashboard_html(location, start_date, end_date, avgs, machine_series):
    sections = []

    for category in UI_CATEGORIES:
        items = machine_series.get(category) or []

        if not items:
            continue

        rows = []
        for item in items:
            machine = esc(item.get("machine") or "")
            avail = max(0, min(100, flt(item.get("avail"))))
            util = max(0, min(100, flt(item.get("util"))))

            rows.append(f'''
<tr>
    <td class="machine-label">{machine}</td>
    <td>
        <div class="bar-wrap">
            <div class="target-line avail-target"></div>
            <div class="target-line util-target"></div>
            <div class="bar availability" style="width:{avail}%;">{avail:.1f}%</div>
            <div class="bar utilisation" style="width:{util}%;">{util:.1f}%</div>
        </div>
    </td>
</tr>
''')

        sections.append(f'''
<div class="pdf-section">
    <h2>{esc(category)} AVAILABILITY &amp; UTILISATION</h2>
    <table class="pdf-chart">
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
</div>
''')

    return f'''
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
    size: A4 landscape;
    margin: 7mm;
}}

body {{
    font-family: Arial, sans-serif;
    color: #111;
    margin: 0;
    padding: 0;
}}

.header {{
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 8px;
}}

.summary {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 12px;
}}

.summary td {{
    border: 1px solid #333;
    padding: 4px 6px;
    font-size: 11px;
    font-weight: bold;
}}

.legend-line {{
    display: inline-block;
    width: 42px;
    height: 4px;
    vertical-align: middle;
    margin-left: 6px;
}}

.red {{
    background: #ff0000;
}}

.green {{
    background: #92d050;
}}

.pdf-section {{
    page-break-inside: avoid;
    margin-bottom: 14px;
    border: 1px solid #222;
    padding: 8px;
}}

h2 {{
    text-align: center;
    font-size: 18px;
    margin: 0 0 8px 0;
}}

.pdf-chart {{
    width: 100%;
    border-collapse: collapse;
}}

.pdf-chart td {{
    padding: 3px 4px;
    vertical-align: middle;
}}

.machine-label {{
    width: 90px;
    font-size: 10px;
    font-weight: bold;
    white-space: nowrap;
}}

.bar-wrap {{
    position: relative;
    height: 34px;
    border-left: 1px solid #333;
    border-bottom: 1px solid #bbb;
    background: #eeeeee;
}}

.target-line {{
    position: absolute;
    left: 0;
    right: 0;
    height: 3px;
    z-index: 5;
}}

.avail-target {{
    top: 5px;
    background: #ff0000;
}}

.util-target {{
    top: 9px;
    background: #92d050;
}}

.bar {{
    position: relative;
    height: 13px;
    line-height: 13px;
    font-size: 9px;
    font-weight: bold;
    color: #000;
    padding-left: 4px;
    box-sizing: border-box;
    white-space: nowrap;
}}

.availability {{
    background: #f4b000;
    margin-top: 3px;
}}

.utilisation {{
    background: #2f75b5;
    color: #fff;
    margin-top: 2px;
}}
</style>
</head>
<body>
    <div class="header">
        Daily Availability and Utilisation Dashboard | {esc(location)} | {esc(start_date)} to {esc(end_date)}
    </div>

    <table class="summary">
        <tr>
            <td>Availability Target <span class="legend-line red"></span></td>
            <td>85%</td>
            <td>Utilization Target <span class="legend-line green"></span></td>
            <td>80%</td>
        </tr>
    </table>

    {''.join(sections)}
</body>
</html>
'''


@frappe.whitelist()
def download_daily_dashboard_pdf_v2(start_date=None, end_date=None, location=None, site=None, machine_scope=None):
    location = location or site
    machine_scope = machine_scope or "Include Swing/Spare"

    if not start_date:
        frappe.throw("Please select Start Date.")

    if not end_date:
        frappe.throw("Please select End Date.")

    if not location:
        frappe.throw("Please select Site.")

    source_rows = fetch_grouped_data(location, start_date, end_date, machine_scope)
    spare_swing_asset_map = get_spare_swing_asset_map(frappe._dict({"start_date": start_date, "end_date": end_date, "location": location, "site": location, "machine_scope": machine_scope}))
    source_rows = apply_machine_scope_filter_to_dashboard_rows(source_rows, frappe._dict({"machine_scope": machine_scope}), spare_swing_asset_map)
    avgs = build_summary_averages_from_source_rows(source_rows)
    machine_series = build_machine_series_from_source_rows(source_rows)

    html = build_pdf_dashboard_html(location, start_date, end_date, avgs, machine_series)

    pdf = frappe.utils.pdf.get_pdf(html)

    filename = f"Daily Availability and Utilisation Dashboard - {location} - {start_date} to {end_date}.pdf"

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"

@frappe.whitelist()
def get_daily_availability_dashboard_html(start_date=None, end_date=None, location=None, site=None, summary_type=None, machine_scope=None):
    location = location or site
    summary_type = summary_type or "Daily Summary"
    machine_scope = machine_scope or "Include Swing/Spare"

    if not start_date:
        frappe.throw("Please select Start Date.")

    if not end_date:
        frappe.throw("Please select End Date.")

    if not location:
        frappe.throw("Please select Site.")

    columns, data, dashboard_html = execute(
        frappe._dict({
            "start_date": start_date,
            "end_date": end_date,
            "from_date": start_date,
            "to_date": end_date,
            "location": location,
            "site": location,
            "summary_type": summary_type,
            "machine_scope": machine_scope,
        })
    )

    return dashboard_html



@frappe.whitelist()
def get_dashboard_html(start_date=None, end_date=None, location=None, site=None, summary_type=None, machine_scope=None):
    location = location or site
    summary_type = summary_type or "Daily Summary"
    machine_scope = machine_scope or "Include Swing/Spare"

    if not start_date:
        frappe.throw("Please select Start Date.")

    if not end_date:
        frappe.throw("Please select End Date.")

    if not location:
        frappe.throw("Please select Site.")

    result = execute(
        frappe._dict({
            "start_date": start_date,
            "end_date": end_date,
            "from_date": start_date,
            "to_date": end_date,
            "location": location,
            "site": location,
            "summary_type": summary_type,
            "machine_scope": machine_scope,
        })
    )

    if isinstance(result, (list, tuple)) and len(result) >= 3:
        return result[2]

    frappe.throw("Dashboard HTML was not returned by the page.")


@frappe.whitelist()
def download_dashboard_pdf(start_date=None, end_date=None, location=None, site=None, summary_type=None, machine_scope=None):
    from frappe.utils.pdf import get_pdf
    from frappe.utils import now_datetime

    location = location or site
    summary_type = summary_type or "Daily Summary"
    machine_scope = machine_scope or "Include Swing/Spare"

    html = get_dashboard_html(
        start_date=start_date,
        end_date=end_date,
        location=location,
        site=site,
        summary_type=summary_type,
        machine_scope=machine_scope,
    )

    engineering_css = get_engineering_css_for_pdf()

    full_html = f"""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">

        <style>
            @page {{
                size: A4 landscape;
                margin: 6mm;
            }}

            body {{
                margin: 0;
                padding: 0;
                background: #ffffff;
                font-family: Arial, sans-serif;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}

            * {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}

            .layout-main-section,
            .page-container,
            .container {{
                width: 100% !important;
                max-width: none !important;
            }}
        </style>

        <style>
            {engineering_css}
        </style>
    </head>
    <body>
        <div class="eng-dashboard eng-dashboard--daily-availability">
            {html}
        </div>
    </body>
    </html>
    """

    pdf = get_pdf(
        full_html,
        options={
            "orientation": "Landscape",
            "page-size": "A4",
            "margin-top": "6mm",
            "margin-right": "6mm",
            "margin-bottom": "6mm",
            "margin-left": "6mm",
            "encoding": "UTF-8",
            "disable-smart-shrinking": None,
            "print-media-type": None,
        },
    )

    safe_location = str(location or "site").replace(" ", "_")
    safe_summary = str(summary_type or "summary").replace(" ", "_")
    safe_scope = str(machine_scope or "scope").replace(" ", "_").replace("/", "_")
    safe_start = str(start_date or "")
    safe_end = str(end_date or "")
    timestamp = now_datetime().strftime("%Y%m%d_%H%M%S")

    filename = f"Daily_Availability_Dashboard_{safe_summary}_{safe_scope}_{safe_location}_{safe_start}_to_{safe_end}_{timestamp}.pdf"

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"
    

def get_engineering_css_for_pdf():
    try:
        css_path = frappe.get_app_path(
            "engineering",
            "public",
            "css",
            "engineering.css",
        )

        with open(css_path, "r", encoding="utf-8") as css_file:
            return css_file.read()

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Daily Dashboard PDF CSS Load Error")
        frappe.clear_messages()
        return ""