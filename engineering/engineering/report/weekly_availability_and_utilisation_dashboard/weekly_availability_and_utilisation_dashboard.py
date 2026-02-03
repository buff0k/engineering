# Copyright (c) 2026, Isambane Mining (Pty) Ltd

import frappe
from datetime import datetime, timedelta




def get_site_category_daily_series(site, from_date, to_date):
    DT = "Availability and Utilisation"

    # DB values -> display label (keep your existing UI labels)
    category_map = {
        "ADT": "ADT's",
        "Excavator": "Excavators",
        "Dozer": "Dozers",
    }

    out = {}

    for db_cat, ui_label in category_map.items():
        # last 7 DISTINCT dates for this site+category
        dates = frappe.get_all(
            DT,
            filters={
                "location": site,
                "shift_date": ["between", [from_date, to_date]],
                "asset_category": db_cat,
            },
            fields=["shift_date"],
            order_by="shift_date desc",
            group_by="shift_date",
            limit_page_length=7,
        )
        dates = [d["shift_date"] for d in dates]
        dates.reverse()  # oldest -> newest for left-to-right bars

        series = []
        for d in dates:
            rows = frappe.get_all(
                DT,
                filters={
                    "location": site,
                    "shift_date": d,
                    "asset_category": db_cat,
                },
                fields=["plant_shift_availability", "plant_shift_utilisation"],
                limit_page_length=500,
            )

            av = [float(r["plant_shift_availability"]) for r in rows if r.get("plant_shift_availability") is not None]  # keep 0
            ut = [float(r["plant_shift_utilisation"]) for r in rows if r.get("plant_shift_utilisation") is not None]    # keep 0

            av_avg = (sum(av) / len(av)) if av else None
            ut_avg = (sum(ut) / len(ut)) if ut else None

            series.append({
                "date": str(d),
                "avail": av_avg,
                "util": ut_avg,
            })

        out[ui_label] = series

    return out


def get_site_category_averages(site, from_date, to_date):
    DT = "Availability and Utilisation"

    # DB category values -> UI row labels
    category_map = {
        "ADT": "ADT's",
        "Excavator": "Excavators",
        "Dozer": "Dozers",
    }

    def avg_last7(cat_value, fieldname):
        rows = frappe.get_all(
            DT,
            filters={
                "location": site,
                "shift_date": ["between", [from_date, to_date]],
                "asset_category": cat_value,
            },
            fields=[fieldname],
            order_by="shift_date desc, modified desc",
            limit_page_length=7,
        )
        vals = [float(r[fieldname]) for r in rows if r.get(fieldname) is not None]  # keep 0s
        return (sum(vals) / len(vals)) if vals else None

    out = {}
    for db_cat, ui_label in category_map.items():
        out[ui_label] = {
            "avail": avg_last7(db_cat, "plant_shift_availability"),
            "util": avg_last7(db_cat, "plant_shift_utilisation"),
        }

    return out


def get_operational_day():
    now = datetime.now()
    return now.date() - timedelta(days=1) if now.hour < 6 else now.date()


SITE_HEADER_COLOURS = {
    "Klipfontein": "#55A7FF",
    "Gwab": "#ECE6F5",
    "Kriel Rehabilitation": "#2ECC71",
    "Koppie": "#F5A623",
    "Uitgevallen": "#1ABC9C",
    "Bankfontein": "#9E9E9E",
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



.isd-subhead th{
  font-size: 11px;
  font-weight: 700;
  background: #fafafa;
}

.isd-yhead{
  font-weight: 800;
}

.isd-shift{
  display: block;
  line-height: 1.15;
}

.isd-day{
  font-weight: 700;
  border-bottom: 1px solid #e5e5e5;
}

.isd-night{
  opacity: 0.75;
}

.isd-dn-head{
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  opacity: 0.8;
}

.isd-chart{
  padding: 10px 10px 12px;
  border-top: 1px solid #e8e8e8;
}



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



.isd-target-line{
  position: absolute;
  left: 44px;          /* 10px left padding + 34px y-axis width */
  right: 10px;
  height: 2px;
  opacity: 0.9;
  pointer-events: none;
}

.isd-target-line.util{
  top: calc(10px + (140px * (1 - 0.80))); /* chart top + height*(1-0.80) */
  background: #333;
}

.isd-target-line.avail{
  top: calc(10px + (140px * (1 - 0.85)));
  background: #f39c12;
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

"""


def execute(filters=None):
    filters = filters or {}

    to_date = filters.get("to_date") or get_operational_day()
    from_date = filters.get("from_date") or (to_date - timedelta(days=6))

    date_list = get_date_list(from_date, to_date)
    sites = get_sites_stub()

    site_blocks = []
    for site in sites:
        avgs = get_site_category_averages(site, from_date, to_date)
        series = get_site_category_daily_series(site, from_date, to_date)
        site_blocks.append(build_site_block_weekly(site, date_list, avgs, series))

    html = f"""
<style>{DASH_CSS}</style>
<div class="isd-hourly-dashboard">
  <div class="isd-grid">
    {''.join(site_blocks)}
  </div>
</div>
"""

    return [{"label": "", "fieldname": "noop"}], [{"noop": ""}], html


def get_date_list(start, end):
    d = start
    out = []
    while d <= end:
        out.append(str(d))
        d += timedelta(days=1)
    return out


def get_sites_stub():
    return [
        "Bankfontein",
        "Gwab",
        "Klipfontein",
        "Koppie",
        "Kriel Rehabilitation",
        "Uitgevallen",
    ]


def build_site_block_weekly(site, date_list, avgs, series):
    header_colour = SITE_HEADER_COLOURS.get(site, "#f7f7f7")
    site_safe = frappe.utils.escape_html(site)



    def trend_opacities(series, metric):
        # metric is "avail" or "util"
        labels = ["ADT's", "Excavators", "Dozers"]

        points = []
        for i in range(7):
            bucket = []
            for label in labels:
                items = series.get(label, [])
                if len(items) < 7:
                    items = ([{"avail": None, "util": None}] * (7 - len(items))) + items
                else:
                    items = items[-7:]

                v = items[i].get(metric)
                if v is not None:
                    bucket.append(float(v))

            points.append((sum(bucket) / len(bucket)) if bucket else None)

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


    header = f"""
<tr>
  <th class="isd-trendcell">
    <div class="isd-trend2">
      <div class="isd-trend-half {av_state}">
        <div class="isd-trend-title">Availability</div>
        <div class="isd-trend-words">
          <span class="isd-trend-down" style="opacity:{av_down:.2f};">Downtrend</span>
          <span class="isd-trend-up" style="opacity:{av_up:.2f};">Uptrend</span>
        </div>
      </div>

      <div class="isd-trend-half {ut_state}">
        <div class="isd-trend-title">Utilisation</div>
        <div class="isd-trend-words">
          <span class="isd-trend-down" style="opacity:{ut_down:.2f};">Downtrend</span>
          <span class="isd-trend-up" style="opacity:{ut_up:.2f};">Uptrend</span>
        </div>
      </div>
    </div>
  </th>

  <th class="isd-axis-head">Availability <span class="isd-axis-sub">(7 Day Average)</span></th>
  <th class="isd-axis-head">Utilisation <span class="isd-axis-sub">(7 Day Average)</span></th>
</tr>
"""



    def fmt(v):
        return "" if v is None else f"{v:.1f}%"

    rows = []
    for cat in ["ADT's", "Excavators", "Dozers"]:
        a = fmt((avgs.get(cat) or {}).get("avail"))
        u = fmt((avgs.get(cat) or {}).get("util"))
        rows.append(f"""
<tr>
  <td class="isd-yhead">{cat}</td>
  <td>{a}</td>
  <td>{u}</td>
</tr>
""")


    # chart: 7 days * (A,U) per category => 14 bars per category
    def h(v):
        if v is None:
            return 2
        v = max(0.0, min(100.0, float(v)))
        return max(2, int(round(v * 1.35)))  # 0-100 -> ~0-135px

    def bars_for(label):
        items = series.get(label, [])
        # pad left if less than 7 days
        if len(items) < 7:
            items = ([{"avail": None, "util": None}] * (7 - len(items))) + items
        else:
            items = items[-7:]

        out = []
        for it in items:
            out.append(f"<div class='isd-bar avail' style='height:{h(it.get('avail'))}px'></div>")
            out.append(f"<div class='isd-bar util' style='height:{h(it.get('util'))}px'></div>")
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

  <div class="isd-target-line util"></div>
  <div class="isd-target-line avail"></div>


  <div class="isd-chart-grid">
    {bars_for("ADT's")}
    <div class="isd-sep"></div>
    {bars_for("Excavators")}
    <div class="isd-sep"></div>
    {bars_for("Dozers")}
  </div>

  <div class="isd-chart-x">
    <div>ADT</div>
    <div>Excavator</div>
    <div>Dozer</div>
  </div>
</div>
"""



    return f"""
<div class="isd-site">
  <div class="isd-site-header" style="--site-colour:{header_colour}">
    <div>Site: {site_safe}</div>
    <div class="isd-site-sub">Week: {date_list[0]} to {date_list[-1]}</div>
  </div>

  <table class="isd-hourly-table">
    <thead>{header}</thead>
    <tbody>{''.join(rows)}</tbody>
  </table>

  {chart_html}
</div>
"""
