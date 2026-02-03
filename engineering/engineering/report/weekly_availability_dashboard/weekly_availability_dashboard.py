# Copyright (c) 2026, Isambane Mining (Pty) Ltd
# CEO Dashboard Two – Hourly Excavator Production
#
# STRUCTURE-ONLY VERSION
# - SAME OUTPUT SHAPE: (columns, data, html)
# - SAME VISUAL LAYOUT (cards + grid + table)
# - NO DATA SOURCING (YOU WILL PLUG IN YOUR OWN)
# - SHARED CSS ONLY (NO INLINE STYLES EXCEPT header colour map -> CSS var)

import frappe
from datetime import datetime, timedelta


# =========================================================
# OPERATIONAL DAY (06:00 → 05:59)
# =========================================================
def get_operational_day():
    now = datetime.now()
    return now.date() - timedelta(days=1) if now.hour < 6 else now.date()


# =========================================================
# SITE HEADER COLOURS (UNCHANGED)
# =========================================================
SITE_HEADER_COLOURS = {
    "Klipfontein": "#55A7FF",
    "Gwab": "#ECE6F5",
    "Kriel Rehabilitation": "#2ECC71",
    "Koppie": "#F5A623",
    "Uitgevallen": "#1ABC9C",
    "Bankfontein": "#9E9E9E",
}


# =========================================================
# HEADER SLOT LABELS (UNCHANGED – 24 SLOTS)
# =========================================================
SLOT_LABELS = [
    "06-07", "07-08", "08-09", "09-10", "10-11", "11-12",
    "12-13", "13-14", "14-15", "15-16", "16-17", "17-18",
    "18-19", "19-20", "20-21", "21-22", "22-23", "23-24",
    "24-01", "01-02", "02-03", "03-04", "04-05", "05-06",
]


# =========================================================
# HOUR SLOT → COLUMN INDEX MAP (UNCHANGED)
# =========================================================
HOUR_SLOT_MAP = {
    "6:00-7:00": 1,
    "7:00-8:00": 2,
    "8:00-9:00": 3,
    "9:00-10:00": 4,
    "10:00-11:00": 5,
    "11:00-12:00": 6,
    "12:00-13:00": 7,
    "13:00-14:00": 8,
    "14:00-15:00": 9,
    "15:00-16:00": 10,
    "16:00-17:00": 11,
    "17:00-18:00": 12,
    "18:00-19:00": 13,
    "19:00-20:00": 14,
    "20:00-21:00": 15,
    "21:00-22:00": 16,
    "22:00-23:00": 17,
    "23:00-0:00": 18,
    "0:00-1:00": 19,
    "1:00-2:00": 20,
    "2:00-3:00": 21,
    "3:00-4:00": 22,
    "4:00-5:00": 23,
    "5:00-6:00": 24,
}


# =========================================================
# SHARED CSS (MATCHES YOUR SCREENSHOT LAYOUT)
# =========================================================
DASH_CSS = """
.isd-hourly-dashboard { padding: 8px 6px; }

.isd-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(360px, 1fr));
  gap: 12px;
}
@media (max-width: 1200px){
  .isd-grid { grid-template-columns: repeat(2, minmax(360px, 1fr)); }
}
@media (max-width: 820px){
  .isd-grid { grid-template-columns: 1fr; }
}

.isd-site{
  background: #fff;
  border: 1px solid #e7e7e7;
  border-radius: 10px;
  overflow: hidden;
}

.isd-site-header{
  padding: 10px 12px;
  font-weight: 700;
  font-size: 12px;
  line-height: 1.35;
  background: var(--site-colour, #f7f7f7);
}

.isd-site-sub{
  font-weight: 700;
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
  border: 1px solid #d0d0d0;
  padding: 6px 4px;
  text-align: center;
  vertical-align: middle;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* stronger day column separators */
.isd-hourly-table th:not(:first-child),
.isd-hourly-table td:not(:first-child){
  border-left: 1px solid #c2c2c2;
}

.isd-hourly-table th{
  background: #f7f7f7;
  font-weight: 700;
}

.isd-hourly-table th:first-child,
.isd-hourly-table td:first-child{
  text-align: left;
  font-weight: 700;
  width: 120px;
  padding-left: 10px;
}

.isd-hourly-table th:nth-child(2),
.isd-hourly-table td:nth-child(2){
  text-align: left;
  font-weight: 700;
  width: 60px;
}

.isd-shift{
  display: block;
  line-height: 1.15;
  padding: 2px 0;
}

/* highlight 0% */
.isd-zero{
  background: #ffdddd;
  font-weight: 700;
  border-radius: 4px;
}

.isd-day{
  border-bottom: 1px solid #ececec;
  font-weight: 700;
}

.isd-night{
  opacity: 0.8;
}

.isd-dn-head{
  display: flex;
  justify-content: space-between;
  gap: 6px;
  font-size: 10px;
  opacity: 0.8;
  margin-top: 2px;
}
.isd-dn-head span{
  display: inline-block;
  min-width: 10px;
}

/* Machine cell: EX011 on left, D(top-right) + N(bottom-right) */
.isd-machine-cell{
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-rows: auto auto;
  align-items: center;
  column-gap: 10px;
  row-gap: 2px;
}
.isd-machine-name{
  grid-column: 1 / 2;
  grid-row: 1 / 3; /* spans both rows */
}
.isd-machine-d{
  grid-column: 2 / 3;
  grid-row: 1 / 2;
  font-size: 10px;
  opacity: 0.8;
}
.isd-machine-n{
  grid-column: 2 / 3;
  grid-row: 2 / 3;
  font-size: 10px;
  opacity: 0.8;
}


"""


# =========================================================
# MAIN EXECUTE (UNCHANGED SIGNATURE + OUTPUT)
# =========================================================

def execute(filters=None):
    filters = filters or {}

    # Use report filters if provided, else use latest AU shift_date (data-driven)
    to_date_obj = filters.get("to_date")
    from_date_obj = filters.get("from_date")

    if to_date_obj and from_date_obj:
        from_date = str(from_date_obj)
        to_date = str(to_date_obj)
    else:
        # latest date in AU table
        max_row = frappe.db.sql(
            "select max(shift_date) from `tabAvailability and Utilisation`",
            as_list=1
        )
        latest = max_row[0][0] if max_row and max_row[0] else get_operational_day()

        to_date = str(latest)
        from_date = str(latest - timedelta(days=6))



    # Columns = dates (7 days)
    date_list = get_date_list(from_date, to_date)

    # ---- QUERY 1: Assets (Excavators + ADTs) ----
    assets_by_site = get_assets_by_site()   # {site: [asset_name,...]}

    # ---- QUERY 2: Availability rows (Day/Night) ----
    avail_map, au_debug = get_availability_map(from_date, to_date)
    # shape: avail_map[site][asset]["Day"|"Night"][date] = value

    EXCLUDED_SITES = {
        "Duplicate Assets",
        "M15",
        "Mimosa",
        "Roodepoort",
        "Grinaker",
    }

    site_blocks = []
    for site in sorted(
        s for s in assets_by_site.keys()
        if s not in EXCLUDED_SITES
    ):
        site_blocks.append(
            build_site_block_weekly(
                site=site,
                date_list=date_list,
                assets_by_site=assets_by_site,
                avail_map=avail_map,
            )
        )


    debug_payload = {
        "from_date": from_date,
        "to_date": to_date,
        "assets_sites_count": len(assets_by_site.keys()),
        "assets_total_count": sum(len(v) for v in assets_by_site.values()),
        "au": au_debug,
        "site_blocks_count": len(site_blocks),
        "sample_assets_by_site": {
            k: (v[:5] if isinstance(v, list) else v)
            for k, v in list(assets_by_site.items())[:5]
        },
        # expose a small slice of the actual lookup map for console testing
        "au_map": build_debug_map_slice(avail_map, limit_sites=3, limit_assets=5, limit_days=7),
    }

    html = f"""
<style>{DASH_CSS}</style>

<script>
window.__WAD_DEBUG = {frappe.as_json(debug_payload)};
console.log("WAD DEBUG (server):", window.__WAD_DEBUG);
</script>

<div class="isd-hourly-dashboard">
  <div class="isd-grid">
    {''.join(site_blocks)}
  </div>
</div>
"""

    columns = [{"fieldname": "noop", "label": "", "fieldtype": "Data", "width": 1}]
    data = [{"noop": ""}]
    return columns, data, html


def build_debug_map_slice(avail_map, limit_sites=3, limit_assets=5, limit_days=7):
    # keep payload small so it doesn't bloat the report
    out = {}
    for site in list(avail_map.keys())[:limit_sites]:
        out[site] = {}
        for asset in list(avail_map[site].keys())[:limit_assets]:
            out[site][asset] = {}
            for shift in ("Day", "Night"):
                days = avail_map[site][asset].get(shift, {})
                out[site][asset][shift] = {k: days[k] for k in list(days.keys())[:limit_days]}
    return out


def get_date_list(from_date: str, to_date: str):
    start = datetime.strptime(from_date, "%Y-%m-%d").date()
    end = datetime.strptime(to_date, "%Y-%m-%d").date()
    out = []
    d = start
    while d <= end:
        out.append(str(d))
        d += timedelta(days=1)
    return out


def get_assets_by_site():
    # IMPORTANT: use Asset.asset_name (Plant No.) so it matches AU.asset_name
    rows = frappe.get_all(
        "Asset",
        filters={
            "docstatus": 1,
            "asset_category": "Excavator",
        },
        fields=["asset_name", "location"],
        order_by="location asc, asset_name asc",
    )

    result = {}
    for r in rows:
        loc = (r.location or "").strip()
        asset = (r.asset_name or "").strip().upper()
        if loc and asset:
            result.setdefault(loc, []).append(asset)
    return result



def _pick_field(meta, candidates):
    # choose first field that exists
    fieldnames = {f.fieldname for f in meta.fields}
    for c in candidates:
        if c in fieldnames:
            return c
    return None


def get_availability_map(from_date: str, to_date: str):
    # 1) Bench-style: prove data exists at all (no date filter)
    total_rows = frappe.db.count("Availability and Utilisation") or 0

    # 2) Bench-style: min/max shift_date in DB
    min_max = frappe.db.sql(
        """
        select
            min(shift_date) as min_date,
            max(shift_date) as max_date
        from `tabAvailability and Utilisation`
        """,
        as_dict=1,
    )
    min_date = str(min_max[0].get("min_date")) if min_max else None
    max_date = str(min_max[0].get("max_date")) if min_max else None

    # 3) Actual fetch for the report week
    rows = frappe.get_all(
        "Availability and Utilisation",
        filters={
            "shift_date": ["between", [from_date, to_date]],
            "shift": ["in", ["Day", "Morning", "Afternoon", "Night"]],
        },
        fields=[
            "name",
            "location",
            "asset_name",
            "shift_date",
            "shift",
            "plant_shift_availability",
            "shift_required_hours",
            "shift_available_hours",
            "shift_working_hours",
        ],
        order_by="location asc, asset_name asc, shift_date asc",
        limit_page_length=5000,
    )

    def _calc(required, available, working):
        req = float(required or 0)
        av = float(available or 0)
        wk = float(working or 0)
        if req > 0:
            return (max(wk, av) / req) * 100.0
        return 0.0

    def _norm(shift):
        if shift in ("Day", "Morning"):
            return "Day"
        if shift in ("Night", "Afternoon"):
            return "Night"
        return None

    out = {}
    samples = []
    skipped = {"missing_site": 0, "missing_asset": 0, "bad_shift": 0}

    for r in rows:
        site_raw = r.get("location")
        asset_raw = r.get("asset_name")
        site = (site_raw or "").strip()
        asset = (asset_raw or "").strip().upper()
        day = str(r.get("shift_date"))
        shift_raw = r.get("shift")
        shift = _norm(shift_raw)

        if not site:
            skipped["missing_site"] += 1
            continue
        if not asset:
            skipped["missing_asset"] += 1
            continue
        if shift not in ("Day", "Night"):
            skipped["bad_shift"] += 1
            continue

        val = r.get("plant_shift_availability")
        if val in (None, ""):
            val = _calc(
                r.get("shift_required_hours"),
                r.get("shift_available_hours"),
                r.get("shift_working_hours"),
            )

        out.setdefault(site, {}).setdefault(asset, {}).setdefault(shift, {})[day] = val

        if len(samples) < 10:
            samples.append({
                "doc": r.get("name"),
                "site_raw": site_raw,
                "site": site,
                "asset_raw": asset_raw,
                "asset": asset,
                "date": day,
                "shift_raw": shift_raw,
                "shift_norm": shift,
                "val": val,
            })

    debug = {
        "bench_total_rows": total_rows,
        "bench_min_shift_date": min_date,
        "bench_max_shift_date": max_date,
        "rows_count": len(rows),
        "sites_count": len(out.keys()),
        "sample_rows": samples,
        "skipped": skipped,
    }

    return out, debug




def build_site_block_weekly(site, date_list, assets_by_site, avail_map):
    header_colour = SITE_HEADER_COLOURS.get(site, "#FFFFFF")
    site_safe = frappe.utils.escape_html(site)

    # Header: Date with D / N indicator
    header = "<tr><th>Machine</th>" + "".join(
        (
            "<th>"
            f"<div>{frappe.utils.escape_html(d[5:])}</div>"
            "</th>"
        )
        for d in date_list
    ) + "</tr>"

    rows = []
    for machine in assets_by_site.get(site, []):
        machine_safe = frappe.utils.escape_html(machine)
        cells = [(
            "<td>"
            "<div class='isd-machine-cell'>"
            f"<div class='isd-machine-name'>{machine_safe}</div>"
            "<div class='isd-machine-d'>D</div>"
            "<div class='isd-machine-n'>N</div>"
            "</div>"
            "</td>"
        )]

        for d in date_list:
            day_val = (
                avail_map.get(site, {})
                         .get(machine, {})
                         .get("Day", {})
                         .get(d, "")
            )
            night_val = (
                avail_map.get(site, {})
                         .get(machine, {})
                         .get("Night", {})
                         .get(d, "")
            )

            def _fmt(v):
                if v in (None, ""):
                    return ""
                try:
                    return f"{int(round(float(v)))}%"
                except Exception:
                    return ""

            day_txt = _fmt(day_val)
            night_txt = _fmt(night_val)

            day_zero = (day_txt == "0%")
            night_zero = (night_txt == "0%")

            day_cls = "isd-shift isd-day" + (" isd-zero" if day_zero else "")
            night_cls = "isd-shift isd-night" + (" isd-zero" if night_zero else "")

            cells.append(
                "<td>"
                f"<div class='{day_cls}'>{day_txt}</div>"
                f"<div class='{night_cls}'>{night_txt}</div>"
                "</td>"
            )


        rows.append("<tr>" + "".join(cells) + "</tr>")

    return f"""
<div class="isd-site">
  <div class="isd-site-header" style="--site-colour:{header_colour}">
    <div>Site: {site_safe}</div>
    <div class="isd-site-sub">Week: {date_list[0]} to {date_list[-1]}</div>
  </div>

  <table class="isd-hourly-table">
    <thead>
      {header}
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</div>
"""
