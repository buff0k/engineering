# Copyright (c) 2026, Isambane Mining (Pty) Ltd

import frappe
from datetime import timedelta


DT = "Availability and Utilisation"

CATEGORY_MAP = {
    "ADT": "ADT's",
    "Excavator": "Excavator's",
    "Dozer": "Dozer's",
}

DB_CATEGORIES = list(CATEGORY_MAP.keys())
UI_CATEGORIES = list(CATEGORY_MAP.values())


SITE_HEADER_COLOURS = {
    "Klipfontein": "#EBF9FF",
    "Gwab": "#F7D8FF",
    "Kriel Rehabilitation": "#E6D3B1",
    "Koppie": "#FEFF8D",
    "Uitgevallen": "#FFD37F",
    "Bankfontein": "#E3E3E3",
}



DASH_CSS = """
.isd-hourly-dashboard { padding: 8px 6px; }

.isd-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(360px, 1fr));
  gap: 12px;
}

.isd-site{
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  overflow: hidden;
}

.isd-site-header{
  padding: 10px 12px;
  font-weight: 700;
  font-size: 12px;
  background: var(--site-colour, #f7f7f7);
}

.isd-site-sub{
  margin-top: 2px;
}


.isd-site-title{
  padding: 10px 12px 8px;
  font-weight: 900;
  font-size: 13px;
}

.isd-band{
  padding: 10px 12px 12px;
  background: var(--site-colour, #f7f7f7);
  border-bottom: 1px solid #e8e8e8;
}

/* let each pill size itself; still 3 per row when space allows */
.isd-metrics{
  display: grid;
  grid-template-columns: repeat(3, max-content);
  gap: 10px;
  justify-content: start;
  align-items: start;
}

.isd-metric{
  display: grid;
  gap: 6px;
  justify-items: center;
}

.isd-metric-title{
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  opacity: 0.75;
  line-height: 1;
  text-align: center;
}


.isd-pill{
  background: rgba(255,255,255,0.86);
  border: 1px solid rgba(0,0,0,0.10);
  border-radius: 999px;
  padding: 8px 10px;
  display: grid;
  gap: 6px;

  width: fit-content;          /* adapt pill width to content */
  max-width: 100%;             /* never overflow container */
}

.isd-pill-title{
  white-space: nowrap;         /* never wrap "DOZER (AVG)" */
}


.isd-pill-title{
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  opacity: 0.75;
  line-height: 1;
}

/* smaller pill + two mini-bubbles inside */
.isd-pill{
  padding: 8px 10px;
  gap: 6px;
}

.isd-pill-title{
  font-size: 10px;
}

/* ensure inner bubbles NEVER overflow the big pill */
.isd-pill-row{
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 8px;
  align-items: center;
}

.isd-mbubble{
  border-radius: 999px;
  border: 3px solid rgba(0,0,0,0.14);
  background: transparent;
  padding: 6px 10px;
  display: grid;
  gap: 2px;

  width: 100%;
  max-width: 100%;
  overflow: hidden;

  color: #fff;               /* default white text */
}



.isd-mbubble-label,
.isd-mbubble-value{
  color: #fff;
  opacity: 1;
}

.isd-mbubble-label,
.isd-mbubble-value{
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}




/* Availability uses the AV colour family (orange) */
.isd-mbubble.av.isd-mbubble-green{ border-color: rgba(30, 142, 62, 0.95); background: rgba(30, 142, 62, 0.95); }
.isd-mbubble.av.isd-mbubble-yellow{ border-color: rgba(26, 115, 232, 0.98); background: rgba(26, 115, 232, 0.98); }
.isd-mbubble.av.isd-mbubble-red{ border-color: rgba(217, 48, 37, 0.96); background: rgba(217, 48, 37, 0.96); }

/* Utilisation uses the Util colour family (grey) but traffic border still signals state */
.isd-mbubble.ut.isd-mbubble-green{ border-color: rgba(30, 142, 62, 0.95); background: rgba(30, 142, 62, 0.95); }
.isd-mbubble.ut.isd-mbubble-yellow{ border-color: rgba(26, 115, 232, 0.98); background: rgba(26, 115, 232, 0.98); }
.isd-mbubble.ut.isd-mbubble-red{ border-color: rgba(217, 48, 37, 0.96); background: rgba(217, 48, 37, 0.96); }


.isd-mbubble-label{
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.2px;
  opacity: 1;
  line-height: 1;
}

.isd-mbubble-value{
  font-size: 12px;
  font-weight: 900;
  line-height: 1.05;
}

.isd-mbubble.av .isd-mbubble-value{ color: #fff; }
.isd-mbubble.ut .isd-mbubble-value{ color: #fff; }



.isd-pill-sub{
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  opacity: 0.55;
  line-height: 1;
}


.isd-hourly-table{
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 11px;
}

.isd-hourly-table th,
.isd-hourly-table td{
  border: 1px solid #cfcfcf;
  padding: 6px 4px;
  text-align: center;
}

.isd-hourly-table th:first-child,
.isd-hourly-table td:first-child{
  text-align: left;
  width: 140px;
}

.isd-axis-head{
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  background: #f3f3f3;
}

.isd-axis-sub{
  font-size: 10px;
  font-weight: 600;
  opacity: 0.75;
  margin-left: 6px;
}

.isd-trendcell{
  background: #fff;
  padding: 0;
}

.isd-trend2{
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.isd-trend-half{
  padding: 6px 10px;
}

.isd-trend-half.isd-up{
  background: rgba(30, 142, 62, 0.12); /* light green */
}

.isd-trend-half.isd-down{
  background: rgba(217, 48, 37, 0.12); /* light red */
}

.isd-trend-half + .isd-trend-half{
  border-left: 2px solid #d0d0d0;
}

.isd-trend-title{
  font-size: 10px;
  font-weight: 800;
  opacity: 0.75;
  margin-bottom: 2px;
  text-transform: uppercase;
}

.isd-trend-words{
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.3px;
}

.isd-trend-down{ color: #d93025; } /* red */
.isd-trend-up{ color: #1e8e3e; }   /* green */

.isd-strip{
  padding: 6px 10px;
  display: grid;
  gap: 4px;
}

.isd-strip-row{
  display: grid;
  grid-template-columns: 90px 1fr;
  align-items: center;
  gap: 10px;
}

.isd-strip-label{
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  opacity: 0.6;
}

.isd-strip-dots{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.isd-strip-word{
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.2px;
  opacity: 0.55;
  margin-right: 6px;
}

.isd-mini{
  width: 12px;
  height: 12px;
  border-radius: 999px;
  border: 2px solid rgba(0,0,0,0.12);
  display: inline-block;
}

.isd-mini-inactive{
  opacity: 0.25;
}

.isd-mini-active{
  opacity: 1;
  box-shadow: 0 3px 10px rgba(0,0,0,0.10);
}

.isd-mini-fill{
  background: currentColor;
}

.isd-mini-red{ color: rgba(217, 48, 37, 0.85); border-color: rgba(217, 48, 37, 0.55); }
.isd-mini-green{ color: rgba(30, 142, 62, 0.85); border-color: rgba(30, 142, 62, 0.55); }
.isd-mini-blue{ color: rgba(26, 115, 232, 0.85); border-color: rgba(26, 115, 232, 0.55); }


.isd-subhead th{
  font-size: 11px;
  font-weight: 700;
  background: #fafafa;
}

.isd-yhead{
  font-weight: 800;
}

.isd-chart{
  padding: 10px 10px 12px;
  border-top: 1px solid #e8e8e8;
}

.isd-avgline{
  position: absolute;
  left: 34px;
  right: 10px;
  height: 2px;
  opacity: 0.55;
  pointer-events: none;
}

/* match legend colours */
.isd-avgline.isd-avg-85{ background: #f39c12; } /* Availability (orange) */
.isd-avgline.isd-avg-80{ background: #6b6b6b; } /* Utilisation (grey) */

.isd-avgline.isd-avg-80{ top: 38px; } /* 10 + (100-80)*1.4 */
.isd-avgline.isd-avg-85{ top: 31px; } /* 10 + (100-85)*1.4 */


.isd-yaxis{
  position: absolute;
  left: 10px;
  top: 10px;
  bottom: 34px; /* leave room for X labels */
  width: 34px;
  font-size: 10px;
  font-weight: 700;
  color: #666;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  pointer-events: none;
}



.isd-chart-grid{
  display: grid;
  grid-template-columns: repeat(44, 1fr); /* 14 + sep + 14 + sep + 14 = 44 */
  align-items: end;
  gap: 2px;
  margin-left: 34px; /* space for Y axis labels */
  height: 140px;
  position: relative;
}

.isd-bar{
  width: 100%;
  border-radius: 2px 2px 0 0;
  min-height: 2px;
}

.isd-bar.avail{ background: #f39c12; }
.isd-bar.util{ background: #6b6b6b; }

.isd-sep{
  height: 100%;
  border-left: 2px solid #d0d0d0;
}

.isd-chart-x{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin-top: 6px;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}

.isd-chart-x > div{
  text-align: center;
}


.isd-daylabels{
  display: grid;
  grid-template-columns: repeat(44, 1fr);
  gap: 2px;
  margin-left: 34px;
  margin-top: 4px;
  font-size: 9px;
  font-weight: 800;
  color: #666;
}

.isd-daylab{
  grid-column: span 2;   /* one label per (avail+util) pair */
  text-align: center;
  white-space: nowrap;
  opacity: 0.9;
}

.isd-daysep{
  height: 100%;
  border-left: 2px solid #d0d0d0;
}




/* tighter table spacing */
.isd-hourly-table th,
.isd-hourly-table td{
  padding: 3px 4px !important;
}

.isd-hourly-table th:first-child,
.isd-hourly-table td:first-child{
  width: 110px !important;
}

/* badges row above table */
.isd-badges{
  display: flex;
  gap: 8px;
  padding: 6px 10px;
  border-bottom: 1px solid #e8e8e8;
  align-items: center;
}

.isd-badge{
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(0,0,0,0.10);
  background: #fff;
  position: relative;
}

/* state colouring using your existing av_state / ut_state classes */
.isd-badge.isd-up{
  background: rgba(30, 142, 62, 0.10);
  border-color: rgba(30, 142, 62, 0.35);
}

.isd-badge.isd-down{
  background: rgba(217, 48, 37, 0.10);
  border-color: rgba(217, 48, 37, 0.35);
}

/* neutral (when class is empty) */
.isd-badge:not(.isd-up):not(.isd-down){
  background: rgba(26, 115, 232, 0.08);
  border-color: rgba(26, 115, 232, 0.25);
}


.isd-contentrow{
  display: grid;
  grid-template-columns: 1fr 260px;
  gap: 10px;
  align-items: start;
  border-top: 1px solid #e8e8e8;
}

.isd-side{
  display: grid;
  gap: 8px;
  padding: 10px 10px 12px;
  border-left: 1px solid #e8e8e8;
}




.isd-cards{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.isd-circlecard{
  display: grid;
  gap: 0;
  justify-items: center;
}

.isd-circlelink{
  text-decoration: none;
  color: inherit;
}

.isd-circlelink:hover .isd-circle{
  transform: translateY(-1px);
  box-shadow: inset 0 0 0 3px rgba(255,255,255,0.35), 0 10px 18px rgba(0,0,0,0.12);
}

.isd-circlelabel{
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  opacity: 0.65;
}

.isd-circle{
  width: 74px;
  height: 74px;
  border-radius: 999px;
  display: grid;
  place-items: center;

  /* text fit */
  font-size: 10.5px;
  font-weight: 900;
  text-align: center;
  line-height: 1.05;
  padding: 10px 8px;
  letter-spacing: 0.2px;

  /* darker ring + more presence */
  border: 2px solid rgba(0,0,0,0.22);
  box-shadow: inset 0 0 0 3px rgba(255,255,255,0.35), 0 6px 14px rgba(0,0,0,0.08);
  background: rgba(255,255,255,0.78);
}

.isd-circle-red{
  border-color: rgba(217, 48, 37, 0.85);
  background: rgba(217, 48, 37, 0.18);
}

.isd-circle-green{
  border-color: rgba(30, 142, 62, 0.85);
  background: rgba(30, 142, 62, 0.18);
}

.isd-circle-blue{
  border-color: rgba(26, 115, 232, 0.85);
  background: rgba(26, 115, 232, 0.18);
}

.isd-legend{
  display: flex;
  gap: 12px;
  justify-content: center;
  align-items: center;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  opacity: 0.75;
}

.isd-legitem{
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.isd-legswatch{
  width: 12px;
  height: 12px;
  border-radius: 3px;
  display: inline-block;
}

.isd-leg-avail{ background: #f39c12; } /* matches your bar */
.isd-leg-util{ background: #6b6b6b; }  /* matches your bar */


"""




def execute(filters=None):
    filters = filters or {}

    from ..availability_util_shared import dashboard_date_range, dashboard_sites

    # Force dashboard window: yesterday -> back 6 days (ignore manual date filters)
    from_date, to_date = dashboard_date_range()
    filters["from_date"] = from_date
    filters["to_date"] = to_date

    sites = dashboard_sites(filters)

    # Cache final HTML for faster open
    cache_key = f"weekly_avail_dash::{sites}::{from_date}::{to_date}"
    cached = frappe.cache().get_value(cache_key)
    if cached:
        return [{"label": "", "fieldname": "noop"}], [{"noop": ""}], cached

    date_list = get_date_list(from_date, to_date)

    site_blocks = []
    for site in sites:
        rows = fetch_site_rows(site, from_date, to_date)
        series = build_daily_series(rows, date_list)
        avgs = build_7day_averages(series)
        site_blocks.append(build_site_block_weekly(site, date_list, avgs, series, from_date, to_date))


    html = f"""
<style>{DASH_CSS}</style>
<div class="isd-hourly-dashboard">
  <div class="isd-grid">
    {''.join(site_blocks)}
  </div>
</div>
"""

    frappe.cache().set_value(cache_key, html, expires_in_sec=300)

    return [{"label": "", "fieldname": "noop"}], [{"noop": ""}], html



def get_date_list(start, end):
    d = start
    out = []
    while d <= end:
        out.append(str(d))
        d += timedelta(days=1)
    return out


def fetch_site_rows(site, from_date, to_date):
    # One fetch per site for the whole window (faster, same logic)
    return frappe.get_all(
        DT,
        filters={
            "location": site,
            "shift_date": ["between", [from_date, to_date]],
            "asset_category": ["in", DB_CATEGORIES],
        },
        fields=[
            "shift_date",
            "asset_category",
            "plant_shift_availability",
            "plant_shift_utilisation",
        ],
        order_by="shift_date asc",
        limit_page_length=5000,
    )


def build_daily_series(rows, date_list):
    # Collect values per category per day
    bucket = {db_cat: {d: {"avail": [], "util": []} for d in date_list} for db_cat in DB_CATEGORIES}

    for r in rows:
        day = str(r.get("shift_date"))
        db_cat = r.get("asset_category")
        if db_cat not in bucket or day not in bucket[db_cat]:
            continue

        av = r.get("plant_shift_availability")
        ut = r.get("plant_shift_utilisation")

        if av is not None:
            bucket[db_cat][day]["avail"].append(float(av))
        if ut is not None:
            bucket[db_cat][day]["util"].append(float(ut))

    out = {}
    for db_cat, ui_label in CATEGORY_MAP.items():
        series = []
        for day in date_list:
            avs = bucket[db_cat][day]["avail"]
            uts = bucket[db_cat][day]["util"]
            av_avg = (sum(avs) / len(avs)) if avs else None
            ut_avg = (sum(uts) / len(uts)) if uts else None
            series.append({"date": day, "avail": av_avg, "util": ut_avg})
        out[ui_label] = series

    return out


def build_7day_averages(series):
    # Average the 7 daily averages (matches your chart/day logic)
    out = {}
    for ui_label in UI_CATEGORIES:
        items = series.get(ui_label, [])
        av = [float(it["avail"]) for it in items if it.get("avail") is not None]
        ut = [float(it["util"]) for it in items if it.get("util") is not None]
        out[ui_label] = {
            "avail": (sum(av) / len(av)) if av else None,
            "util": (sum(ut) / len(ut)) if ut else None,
        }
    return out


def build_site_block_weekly(site, date_list, avgs, series, from_date, to_date):
    header_colour = SITE_HEADER_COLOURS.get(site, "#f7f7f7")
    site_safe = frappe.utils.escape_html(site)

    # Avail and Util report filters are: start_date, end_date, site
    report_route = "Avail%20and%20Util%20report"

    report_href = (
        f"/app/query-report/{report_route}"
        f"?start_date={frappe.utils.quote(str(from_date))}"
        f"&end_date={frappe.utils.quote(str(to_date))}"
        f"&site={frappe.utils.quote(site)}"
    )




    def trend_opacities(series_map, metric):
        points = []
        for i in range(7):
            bucket_vals = []
            for label in UI_CATEGORIES:
                items = series_map.get(label, [])
                if len(items) < 7:
                    items = ([{"avail": None, "util": None}] * (7 - len(items))) + items
                else:
                    items = items[-7:]

                v = items[i].get(metric)
                if v is not None:
                    bucket_vals.append(float(v))
            points.append((sum(bucket_vals) / len(bucket_vals)) if bucket_vals else None)

        clean = [p for p in points if p is not None]
        if len(clean) < 2:
            return 0.35, 0.35

        delta = clean[-1] - clean[0]
        strength = min(1.0, abs(delta) / 15.0)
        base = 0.20
        bright = base + (0.80 * strength)
        dim = base

        if delta > 0.0001:
            return dim, bright
        if delta < -0.0001:
            return bright, dim
        return 0.35, 0.35

    av_down, av_up = trend_opacities(series, "avail")
    ut_down, ut_up = trend_opacities(series, "util")

    av_state = "isd-up" if av_up > av_down else ("isd-down" if av_down > av_up else "")
    ut_state = "isd-up" if ut_up > ut_down else ("isd-down" if ut_down > ut_up else "")

    def state_word(state):
        if state == "isd-down":
            return "Downtrend"
        if state == "isd-up":
            return "Uptrend"
        return "Neutral"

    def circle_class(state):
        if state == "isd-down":
            return "isd-circle isd-circle-red"
        if state == "isd-up":
            return "isd-circle isd-circle-green"
        return "isd-circle isd-circle-blue"

    def fmt(v):
        return "" if v is None else f"{v:.1f}%"
    


    def bubble_colour_class(metric, v):
        """Return CSS class for availability/utilisation thresholds."""
        if v is None:
            return ""

        v = float(v)

        if metric == "avail":
            # Green >=85, Yellow 75-<85, Red <75
            if v >= 85.0:
                return "isd-mbubble-green"
            if v >= 75.0:
                return "isd-mbubble-yellow"
            return "isd-mbubble-red"

        # metric == "util"
        # Green >=80, Yellow 70-<80, Red <70
        if v >= 80.0:
            return "isd-mbubble-green"
        if v >= 70.0:
            return "isd-mbubble-yellow"
        return "isd-mbubble-red"
   

    def short_name(ui_cat):
        if ui_cat == "ADT's":
            return "ADT's"
        if ui_cat == "Excavator's":
            return "Excavator's"
        if ui_cat == "Dozer's":
            return "Dozer's"
        return ui_cat





    pills = []
    for cat in UI_CATEGORIES:
        av_v = (avgs.get(cat) or {}).get("avail")
        ut_v = (avgs.get(cat) or {}).get("util"

        )
        a = fmt(av_v)
        u = fmt(ut_v)

        av_cls = bubble_colour_class("avail", av_v)
        ut_cls = bubble_colour_class("util", ut_v)

        pills.append(f"""
<div class="isd-metric">
  <div class="isd-metric-title">{short_name(cat)} (Avg)</div>

  <div class="isd-pill-row">
    <div class="isd-mbubble av {av_cls}">
      <div class="isd-mbubble-label">Availability</div>
      <div class="isd-mbubble-value">{a}</div>
    </div>

    <div class="isd-mbubble ut {ut_cls}">
      <div class="isd-mbubble-label">Utilisation</div>
      <div class="isd-mbubble-value">{u}</div>
    </div>
  </div>
</div>
""")


    header_band = f"""
<div class="isd-band" style="--site-colour:{header_colour}">
  <div class="isd-metrics">
    {''.join(pills)}
  </div>
</div>
"""

    avail_word = state_word(av_state)
    util_word = state_word(ut_state)

    side_html = f"""
<div class="isd-side">
  <div class="isd-cards">
    <div class="isd-circlecard">
      <a class="isd-circlelink"
         target="_blank" rel="noopener"
         href="{report_href}">
        <div class="{circle_class(av_state)}">{avail_word}</div>
      </a>
    </div>

    <div class="isd-circlecard">
      <a class="isd-circlelink"
         target="_blank" rel="noopener"
         href="{report_href}">
        <div class="{circle_class(ut_state)}">{util_word}</div>
      </a>
    </div>
  </div>

  <div class="isd-legend">
    <span class="isd-legitem"><i class="isd-legswatch isd-leg-avail"></i>Availability</span>
    <span class="isd-legitem"><i class="isd-legswatch isd-leg-util"></i>Utilisation</span>
  </div>
</div>
"""





    def h(v):
        if v is None:
            return 2
        v = max(0.0, min(100.0, float(v)))
        return max(2, int(round(v * 1.35)))

    def bars_for(label):
        items = series.get(label, [])
        if len(items) < 7:
            items = ([{"avail": None, "util": None}] * (7 - len(items))) + items
        else:
            items = items[-7:]

        out = []
        for it in items:
            out.append(f"<div class='isd-bar avail' style='height:{h(it.get('avail'))}px'></div>")
            out.append(f"<div class='isd-bar util' style='height:{h(it.get('util'))}px'></div>")
        return "".join(out)


    def day_labels_for(label):
        items = series.get(label, [])
        if len(items) < 7:
            items = ([{"date": ""}] * (7 - len(items))) + items
        else:
            items = items[-7:]

        out = []
        for it in items:
            d = (it.get("date") or "")
            # YYYY-MM-DD -> DD
            dd = d[-2:] if len(d) >= 2 else d
            out.append(f"<div class='isd-daylab'>{dd}</div>")
        return "".join(out)





    chart_html = f"""
<div class="isd-chart" style="position:relative;">
  <div class="isd-yaxis">
    <div>100%</div>
    <div>80%</div>
    <div>60%</div>
    <div>40%</div>
    <div>20%</div>
    <div>0%</div>
  </div>

  <!-- average target lines (overlay the grid) -->
  <div class="isd-avgline isd-avg-85"></div>
  <div class="isd-avgline isd-avg-80"></div>

  <div class="isd-chart-grid">
    {bars_for("ADT's")}
    <div class="isd-sep"></div>
    {bars_for("Excavator's")}
    <div class="isd-sep"></div>
    {bars_for("Dozer's")}
  </div>

  <div class="isd-daylabels">
    {day_labels_for("ADT's")}
    <div class="isd-daysep"></div>
    {day_labels_for("Excavator's")}
    <div class="isd-daysep"></div>
    {day_labels_for("Dozer's")}
  </div>

  <div class="isd-chart-x">
    <div>ADT's</div>
    <div>Excavator's</div>
    <div>Dozer's</div>
  </div>
</div>
"""

    return f"""
<div class="isd-site">
  <div class="isd-site-title">{site_safe} • {date_list[0]} → {date_list[-1]}</div>
  {header_band}

  <div class="isd-contentrow">
    {chart_html}
    {side_html}
  </div>
</div>
"""
