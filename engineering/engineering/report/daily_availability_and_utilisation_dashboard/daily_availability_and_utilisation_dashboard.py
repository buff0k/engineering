import frappe


CATEGORY_MAP = {
    "ADT": "ADT's",
    "Excavator": "Excavator's",
    "Dozer": "Dozer's",
    "Grader": "Grader",
    "Service Truck": "Service Truck",
    "TLB": "TLB",
    "Water Bowser": "Water Bowser",
    "Diesel Bowsers": "Diesel Bowsers",
    "Drills": "Drills",
}

UI_TITLES = {
    "ADT's": "ADTS",
    "Excavator's": "EXCAVATOR",
    "Dozer's": "DOZER",
    "Grader": "GRADER",
    "Service Truck": "SERVICE TRUCK",
    "TLB": "TLB",
    "Water Bowser": "WATER BOWSER",
    "Diesel Bowsers": "DIESEL BOWSERS",
    "Drills": "DRILLS",
}

UI_CATEGORIES = [
    "ADT's",
    "Excavator's",
    "Dozer's",
    "Grader",
    "Service Truck",
    "TLB",
    "Water Bowser",
    "Diesel Bowsers",
    "Drills",
]

SITE_HEADER_COLOURS = {
    "Klipfontein": "#EBF9FF",
    "Gwab": "#F7D8FF",
    "Kriel Rehabilitation": "#E6D3B1",
    "Koppie": "#FEFF8D",
    "Uitgevallen": "#FFD37F",
    "Bankfontein": "#E3E3E3",
}


DASH_CSS = """
.isd-hourly-dashboard {
  padding: 8px 6px;
}

.isd-note {
  margin: 0 0 10px;
  padding: 8px 10px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #fafafa;
  font-size: 12px;
  font-weight: 700;
}

.isd-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.isd-site {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  overflow: hidden;
}

.isd-site-title {
  padding: 10px 12px 8px;
  font-weight: 900;
  font-size: 13px;
}

.isd-band {
  padding: 10px 12px 12px;
  background: var(--site-colour, #f7f7f7);
  border-bottom: 1px solid #e8e8e8;
}

.isd-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, max-content));
  gap: 18px;
  justify-content: start;
  align-items: start;
}

.isd-metric {
  display: grid;
  gap: 6px;
  justify-items: center;
}

.isd-metric-title {
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  opacity: 0.75;
  line-height: 1;
  text-align: center;
}

.isd-pill-row {
  display: grid;
  grid-template-columns: max-content max-content;
  gap: 8px;
  align-items: center;
}

.isd-mbubble {
  border-radius: 999px;
  border: 3px solid rgba(0,0,0,0.14);
  padding: 6px 10px;
  display: grid;
  gap: 2px;
  min-width: 72px;
  overflow: hidden;
  color: #fff;
}

.isd-mbubble-green {
  border-color: rgba(30, 142, 62, 0.95);
  background: rgba(30, 142, 62, 0.95);
}

.isd-mbubble-yellow {
  border-color: rgba(26, 115, 232, 0.98);
  background: rgba(26, 115, 232, 0.98);
}

.isd-mbubble-red {
  border-color: rgba(217, 48, 37, 0.96);
  background: rgba(217, 48, 37, 0.96);
}

.isd-mbubble-label {
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.2px;
  line-height: 1;
  white-space: nowrap;
}

.isd-mbubble-value {
  font-size: 12px;
  font-weight: 900;
  line-height: 1.05;
  color: #fff;
}

.isd-contentrow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 150px;
  gap: 10px;
  align-items: start;
  border-top: 1px solid #e8e8e8;
}

.isd-chart-stack {
  display: grid;
  gap: 16px;
  padding: 10px;
  overflow-x: auto;
  overflow-y: visible;
}

.isd-chart-section {
  border: 1px solid #e5e5e5;
  border-radius: 10px;
  background: #fff;
  overflow-x: auto;
  overflow-y: hidden;
}

.isd-chart-section-title {
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.4px;
  background: #f7f7f7;
  border-bottom: 1px solid #e5e5e5;
}

.isd-chart {
  padding: 10px 10px 16px;
  position: relative;
}

.isd-yaxis {
  position: absolute;
  left: 10px;
  top: 10px;
  bottom: 58px;
  width: 34px;
  font-size: 10px;
  font-weight: 700;
  color: #666;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  pointer-events: none;
}

.isd-chart-grid {
  display: grid;
  align-items: end;
  gap: 2px;
  margin-left: 34px;
  height: 140px;
  position: relative;
  border-bottom: 1px solid #ddd;
}

.isd-bar {
  width: 100%;
  border-radius: 2px 2px 0 0;
  min-height: 2px;
}

.isd-bar.avail {
  background: #f39c12;
}

.isd-bar.util {
  background: #6b6b6b;
}

.isd-bar.nodata {
  opacity: 0.18;
}

.isd-avgline {
  position: absolute;
  left: 44px;
  right: 10px;
  height: 2px;
  opacity: 0.55;
  pointer-events: none;
}

.isd-avgline.isd-avg-85 {
  background: #f39c12;
  top: 31px;
}

.isd-avgline.isd-avg-80 {
  background: #6b6b6b;
  top: 38px;
}

.isd-machinelabels {
  display: grid;
  gap: 2px;
  margin-left: 34px;
  margin-top: 4px;
  font-size: 9px;
  font-weight: 800;
  color: #666;
}

.isd-machinelab {
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transform: rotate(-35deg);
  transform-origin: top center;
  min-height: 42px;
  padding-top: 4px;
}

.isd-no-machine-data {
  padding: 14px;
  font-size: 12px;
  font-weight: 700;
  color: #666;
}

.isd-side {
  display: grid;
  gap: 8px;
  padding: 10px 10px 12px;
  border-left: 1px solid #e8e8e8;
}

.isd-cards {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.isd-circle {
  width: 74px;
  height: 74px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  font-size: 10.5px;
  font-weight: 900;
  text-align: center;
  line-height: 1.05;
  padding: 10px 8px;
  letter-spacing: 0.2px;
  border: 2px solid rgba(0,0,0,0.22);
  box-shadow: inset 0 0 0 3px rgba(255,255,255,0.35), 0 6px 14px rgba(0,0,0,0.08);
}

.isd-circle-green {
  border-color: rgba(30, 142, 62, 0.85);
  background: rgba(30, 142, 62, 0.18);
}

.isd-legend {
  display: grid;
  gap: 6px;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  opacity: 0.75;
}

.isd-legitem {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.isd-legswatch {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  display: inline-block;
}

.isd-leg-avail {
  background: #f39c12;
}

.isd-leg-util {
  background: #6b6b6b;
}

@media (max-width: 900px) {
  .isd-metrics {
    grid-template-columns: 1fr;
    justify-content: stretch;
  }

  .isd-contentrow {
    grid-template-columns: 1fr;
  }

  .isd-side {
    border-left: none;
    border-top: 1px solid #e8e8e8;
  }
}
"""


def execute(filters=None):
    filters = filters or {}

    start_date = frappe.utils.getdate(filters.get("start_date") or filters.get("from_date"))
    end_date = frappe.utils.getdate(filters.get("end_date") or filters.get("to_date"))
    location = filters.get("location")

    if not start_date:
        frappe.throw("Please select Start Date.")

    if not end_date:
        frappe.throw("Please select End Date.")

    if start_date > end_date:
        frappe.throw("Start Date cannot be after End Date.")

    if not location:
        frappe.throw("Please select Site.")

    source_rows = fetch_month_end_report_data(location, start_date, end_date)

    avgs = build_summary_averages_from_source_rows(source_rows)
    machine_series = build_machine_series_from_source_rows(source_rows)

    html = build_dashboard_html(location, start_date, end_date, avgs, machine_series)

    return [{"label": "", "fieldname": "noop", "fieldtype": "Data", "width": 1}], [{"noop": ""}], html


def fetch_month_end_report_data(location, start_date, end_date):
    import importlib

    month_end_report = importlib.import_module("engineering.engineering.report.availability_and_utilisation_month_end_report.availability_and_utilisation_month_end_report")

    result = month_end_report.get_data({
        "from_date": start_date,
        "to_date": end_date,
        "location": location,
    })

    return normalise_report_rows(result)


def normalise_report_rows(result):
    if not result:
        return []

    if isinstance(result, dict):
        for key in ("data", "result", "rows", "message"):
            value = result.get(key)
            if isinstance(value, list):
                return value
        return []

    if isinstance(result, tuple):
        for item in result:
            if isinstance(item, list):
                return item
        return []

    if isinstance(result, list):
        return result

    return []


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
        "equipment_category",
        "Equipment Category",
        "plant_category",
        "Plant Category",
    ])

    if value in CATEGORY_MAP:
        return value

    if isinstance(row, dict):
        for val in row.values():
            if val in CATEGORY_MAP:
                return val

    return None


def get_machine(row):
    machine = get_any(row, [
        "asset_name",
        "Asset Name",
        "asset",
        "Asset",
        "equipment",
        "Equipment",
        "machine",
        "Machine",
        "machine_no",
        "Machine No",
        "plant_no",
        "Plant No",
        "fleet_number",
        "Fleet Number",
        "availability_and_utilisation",
        "Availability and Utilisation",
    ])

    if not machine:
        return ""

    machine = str(machine).strip()

    if machine in CATEGORY_MAP:
        return ""

    return machine


def get_avail(row):
    return to_float(get_any(row, [
        "avail_percent",
        "Avail (%)",
        "availability_percent",
        "availability_percentage",
        "available_percentage",
        "avail_percentage",
        "plant_shift_availability",
        "Avail",
        "Availability",
        "avail",
        "availability",
    ]))


def get_util(row):
    return to_float(get_any(row, [
        "util_percent",
        "Util (%)",
        "utilisation_percent",
        "utilization_percent",
        "utilisation_percentage",
        "utilization_percentage",
        "util_percentage",
        "plant_shift_utilisation",
        "plant_shift_utilization",
        "Util",
        "Utilisation",
        "Utilization",
        "util",
        "utilisation",
        "utilization",
    ]))


def is_separator_row(row):
    if not isinstance(row, dict):
        return True

    if row.get("is_separator"):
        return True

    category = get_category(row)
    machine = get_machine(row)
    av = get_avail(row)
    ut = get_util(row)

    return not category and not machine and av is None and ut is None


def is_category_total_row(row):
    if not isinstance(row, dict):
        return False

    if row.get("is_category_total"):
        return True

    category = get_category(row)
    machine = get_machine(row)

    return bool(category) and not machine


def build_summary_averages_from_source_rows(rows):
    out = {ui_label: {"avail": None, "util": None} for ui_label in UI_CATEGORIES}

    for row in rows:
        if is_separator_row(row):
            continue

        if not is_category_total_row(row):
            continue

        category = get_category(row)

        if category not in CATEGORY_MAP:
            continue

        ui_label = CATEGORY_MAP[category]

        out[ui_label] = {
            "avail": get_avail(row),
            "util": get_util(row),
        }

    for db_category, ui_label in CATEGORY_MAP.items():
        if out[ui_label]["avail"] is not None or out[ui_label]["util"] is not None:
            continue

        machine_rows = [
            row for row in rows
            if isinstance(row, dict)
            and not is_separator_row(row)
            and not is_category_total_row(row)
            and get_category(row) == db_category
        ]

        avail_values = [get_avail(row) for row in machine_rows if get_avail(row) is not None]
        util_values = [get_util(row) for row in machine_rows if get_util(row) is not None]

        out[ui_label] = {
            "avail": (sum(avail_values) / len(avail_values)) if avail_values else None,
            "util": (sum(util_values) / len(util_values)) if util_values else None,
        }

    return out


def build_machine_series_from_source_rows(rows):
    buckets = {ui_label: {} for ui_label in UI_CATEGORIES}

    for row in rows:
        if is_separator_row(row):
            continue

        if is_category_total_row(row):
            continue

        category = get_category(row)

        if category not in CATEGORY_MAP:
            continue

        ui_label = CATEGORY_MAP[category]
        machine = get_machine(row)

        if not machine:
            continue

        if machine not in buckets[ui_label]:
            buckets[ui_label][machine] = {
                "avail_values": [],
                "util_values": [],
            }

        av = get_avail(row)
        ut = get_util(row)

        if av is not None:
            buckets[ui_label][machine]["avail_values"].append(av)

        if ut is not None:
            buckets[ui_label][machine]["util_values"].append(ut)

    output = {}

    for ui_label in UI_CATEGORIES:
        output[ui_label] = []

        for machine, vals in sorted(buckets[ui_label].items()):
            av_values = vals["avail_values"]
            ut_values = vals["util_values"]

            output[ui_label].append({
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


def build_dashboard_html(location, start_date, end_date, avgs, machine_series):
    site_safe = frappe.utils.escape_html(location)
    header_colour = SITE_HEADER_COLOURS.get(location, "#f7f7f7")

    metric_cards = []

    for ui_label in UI_CATEGORIES:
        values = avgs.get(ui_label) or {}
        av = values.get("avail")
        ut = values.get("util")

        metric_cards.append(f"""
<div class="isd-metric">
  <div class="isd-metric-title">{frappe.utils.escape_html(ui_label)} Avg</div>

  <div class="isd-pill-row">
    <div class="isd-mbubble {bubble_colour("avail", av)}">
      <div class="isd-mbubble-label">Availability</div>
      <div class="isd-mbubble-value">{fmt_percent(av)}</div>
    </div>

    <div class="isd-mbubble {bubble_colour("util", ut)}">
      <div class="isd-mbubble-label">Utilisation</div>
      <div class="isd-mbubble-value">{fmt_percent(ut)}</div>
    </div>
  </div>
</div>
""")

    chart_html = build_chart_html(machine_series)
    trend_html = build_trend_html(location, start_date, end_date)

    return f"""
<style>{DASH_CSS}</style>

<div class="isd-hourly-dashboard">
  <div class="isd-note">
    Showing: {site_safe} | {start_date} to {end_date}. Averages and graphs are read from Availability and Utilisation Month End Report.
  </div>

  <div class="isd-grid">
    <div class="isd-site">
      <div class="isd-site-title">{site_safe} | {start_date} to {end_date}</div>

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
</div>
"""


def build_trend_html(location, start_date, end_date):
    report_href = (
        "/app/query-report/Availability%20and%20Utilisation%20Month%20End%20Report"
        f"?from_date={frappe.utils.quote(str(start_date))}"
        f"&to_date={frappe.utils.quote(str(end_date))}"
        f"&location={frappe.utils.quote(str(location))}"
    )

    return f"""
<div class="isd-side">
  <div class="isd-cards">
    <a
      href="{report_href}"
      class="isd-circle isd-circle-green"
      style="text-decoration:none;color:inherit;cursor:pointer;"
    >
      Open<br>Report
    </a>
  </div>

  <div class="isd-legend">
    <span class="isd-legitem"><i class="isd-legswatch isd-leg-avail"></i>Availability</span>
    <span class="isd-legitem"><i class="isd-legswatch isd-leg-util"></i>Utilisation</span>
  </div>
</div>
"""


def build_chart_html(machine_series):
    def height(value):
        if value is None:
            return 2

        value = max(0.0, min(100.0, float(value)))
        return max(2, int(round(value * 1.35)))

    def chart_section(ui_label):
        title = UI_TITLES[ui_label]
        items = machine_series.get(ui_label) or []

        if not items:
            return f"""
<div class="isd-chart-section">
  <div class="isd-chart-section-title">{title}</div>
  <div class="isd-no-machine-data">No machines found for {title} in the selected date range.</div>
</div>
"""

        count = max(len(items), 1)
        grid_template = f"repeat({count * 2}, minmax(14px, 1fr))"
        label_template = f"repeat({count}, minmax(44px, 2fr))"
        min_width = max(620, count * 72)

        bars = []
        labels = []

        for item in items:
            machine = frappe.utils.escape_html(item.get("machine") or "")
            av = item.get("avail")
            ut = item.get("util")

            av_class = "isd-bar avail" + (" nodata" if av is None else "")
            ut_class = "isd-bar util" + (" nodata" if ut is None else "")

            bars.append(
                f"<div class='{av_class}' title='{machine} Availability: {fmt_percent(av)}' style='height:{height(av)}px'></div>"
            )

            bars.append(
                f"<div class='{ut_class}' title='{machine} Utilisation: {fmt_percent(ut)}' style='height:{height(ut)}px'></div>"
            )

            labels.append(
                f"<div class='isd-machinelab' title='{machine}'>{machine}</div>"
            )

        return f"""
<div class="isd-chart-section">
  <div class="isd-chart-section-title">{title}</div>

  <div class="isd-chart" style="min-width:{min_width}px;">
    <div class="isd-yaxis">
      <div>100%</div>
      <div>80%</div>
      <div>60%</div>
      <div>40%</div>
      <div>20%</div>
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
"""

    sections = "".join(chart_section(ui_label) for ui_label in UI_CATEGORIES)

    return f"""
<div class="isd-chart-stack">
  {sections}
</div>
"""
