import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, cint
import calendar
import math
from datetime import timedelta

class ServiceSchedule(Document):
    pass


@frappe.whitelist()
def rebuild_service_schedule(name):
    doc = frappe.get_doc("Service Schedule", name)

    # 🔥 ONLY clear MSR-related fields, keep rows and all other logic intact
    for r in doc.service_schedule_child:
        r.date_of_previous_service = None
        r.hours_previous_service = 0
        r.last_service_interval = 0

        r.date_of_next_service_1 = None
        r.planned_hours_next_service_1 = None
        r.next_service_interval_1 = ""

        r.date_of_next_service_2 = None
        r.planned_hours_next_service_2 = None
        r.next_service_interval_2 = ""

        r.date_of_next_service_3 = None
        r.planned_hours_of_service_3 = None
        r.next_service_interval_3 = ""

        # keep MSR link fields clean but stable
        r.msr_reference_number = ""
        r.msr_record_name = ""

    doc.save(ignore_permissions=True)
    return "Service Schedule MSR fields cleared"



def clamp_daily_usage(val, min_val=0.0, max_val=24.0):
    try:
        v = float(val or 0)
    except Exception:
        v = 0.0
    return max(float(min_val), min(v, float(max_val)))


@frappe.whitelist()
def queue_service_schedule_update(schedule_name=None, daily_usage_default=15):
    """Scheduler/async entrypoint.

    Exists because hooks/scheduler events reference it.
    If called without schedule_name (as scheduler often does), it does nothing
    to avoid overwriting user-edited schedules.
    """
    if not schedule_name:
        frappe.logger(__name__).info(
            "queue_service_schedule_update called without schedule_name; skipping."
        )
        return {"status": "skipped", "reason": "no schedule_name"}

    frappe.enqueue(
        "engineering.engineering.doctype.service_schedule.service_schedule.generate_schedule_backend",
        queue="long",
        timeout=1800,
        schedule_name=schedule_name,
        daily_usage_default=clamp_daily_usage(daily_usage_default or 15),
    )
    return {"status": "queued", "schedule_name": schedule_name}


def as_date(d):
    return getdate(d) if d else None

def parse_month_label(month_label):
    """Convert 'January 2025' -> (2025, 1)."""
    if not month_label:
        frappe.throw("Month label is required, e.g. 'January 2025'.")

    parts = str(month_label).strip().split()
    if len(parts) != 2:
        frappe.throw("Invalid month format. Use 'January 2025'.")

    month_name, year_str = parts[0], parts[1]
    try:
        year = int(year_str)
        month_index = list(calendar.month_name).index(month_name)
        if month_index <= 0:
            raise ValueError
        return year, month_index
    except Exception:
        frappe.throw(f"Invalid month label: {month_label}")

def parse_month_bounds(month_label):
    year, month_index = parse_month_label(month_label)
    last_day = calendar.monthrange(year, month_index)[1]
    month_start = getdate(f"{year}-{month_index:02d}-01")
    month_end = getdate(f"{year}-{month_index:02d}-{last_day:02d}")
    return year, month_index, month_start, month_end

def ceiling_to_250(value):
    v = cint(value) or 0
    if v <= 0:
        return 0
    return int(math.ceil(v / 250.0) * 250)

def adjust_sunday_to_saturday(d, month_start=None):
    """If d is Sunday, move it back to Saturday. If that moves before month_start, keep original."""
    if not d:
        return None
    dd = getdate(d)
    if dd.weekday() == 6:  # Sunday
        sat = dd - timedelta(days=1)
        if month_start and sat < getdate(month_start):
            return dd
        return sat
    return dd

def get_assets_for_site(site):
    return frappe.get_all(
        "Asset",
        filters={
            "location": site,
            "asset_category": ["in", ["ADT", "Diesel Bowsers", "Excavator", "Dozer", "Service Truck"]],
        },
        fields=["name", "asset_category", "item_name", "item_code"],
        order_by="name asc",
    )

def batch_get_day_shift_start_hours(asset_list, month_start, month_end):
    """Return mapping (date_iso, asset_name) -> eng_hrs_start for Day shift."""
    if not asset_list:
        return {}

    # Get Day-shift Pre-Use Hours in month
    pre_use_docs = frappe.get_all(
        "Pre-Use Hours",
        filters={
            "shift_date": ("between", [month_start, month_end]),
            "shift": "Day",
        },
        fields=["name", "shift_date"],
        order_by="shift_date asc",
    )

    if not pre_use_docs:
        return {}

    parent_names = [d["name"] for d in pre_use_docs]

    # Get child rows
    child_rows = frappe.get_all(
        "Pre-use Assets",
        filters={"parent": ["in", parent_names]},
        fields=["parent", "asset_name", "eng_hrs_start"],
    )

    parent_to_date = {d["name"]: getdate(d["shift_date"]) for d in pre_use_docs}

    out = {}
    for r in child_rows:
        asset = r.get("asset_name")
        if not asset or asset not in asset_list:
            continue

        dt = parent_to_date.get(r.get("parent"))
        if not dt:
            continue

        out[(dt.isoformat(), asset)] = float(r.get("eng_hrs_start") or 0)

    return out

def prev_month_label(month_label):
    year, month_index = parse_month_label(month_label)
    if month_index == 1:
        return f"December {year - 1}"
    return f"{calendar.month_name[month_index - 1]} {year}"


def get_last_30_day_avg_daily_usage(asset, anchor_date):
    """
    Compute average daily usage over the last 30 days ending at anchor_date (inclusive).
    Uses Day-shift Pre-Use Hours (eng_hrs_start) deltas between consecutive days.
    Includes 0 as valid start_hours (but delta requires consecutive days).
    Returns a float clamped to 0..24. Falls back to 15 if insufficient data.
    """
    if not asset or not anchor_date:
        return 15.0

    end = getdate(anchor_date)
    start = end - timedelta(days=29)

    # Pull day-shift pre-use docs for the window
    pre_use_docs = frappe.get_all(
        "Pre-Use Hours",
        filters={
            "shift_date": ("between", [start, end]),
            "shift": "Day",
        },
        fields=["name", "shift_date"],
        order_by="shift_date asc",
    )
    if not pre_use_docs:
        return 15.0

    parent_names = [d["name"] for d in pre_use_docs]
    parent_to_date = {d["name"]: getdate(d["shift_date"]) for d in pre_use_docs}

    # Pull only this asset's child rows
    child_rows = frappe.get_all(
        "Pre-use Assets",
        filters={
            "parent": ["in", parent_names],
            "asset_name": asset
        },
        fields=["parent", "eng_hrs_start"],
    )
    if not child_rows:
        return 15.0

    # Build date -> start_hours mapping (one per day)
    day_map = {}
    for r in child_rows:
        dt = parent_to_date.get(r.get("parent"))
        if not dt:
            continue
        try:
            day_map[dt] = float(r.get("eng_hrs_start") or 0)
        except Exception:
            day_map[dt] = 0.0

    # Calculate deltas on consecutive days only
    dates = sorted(day_map.keys())
    deltas = []
    prev_date = None
    prev_val = None

    for dt in dates:
        val = day_map.get(dt, 0.0)

        if prev_date is not None and prev_val is not None:
            if (dt - prev_date).days == 1:
                delta = val - prev_val
                # keep non-negative only (ignore resets / bad data)
                if delta >= 0:
                    deltas.append(delta)

        prev_date = dt
        prev_val = val

    if not deltas:
        return 15.0

    avg = sum(deltas) / float(len(deltas))
    return int(round(clamp_daily_usage(avg)))


def get_prev_month_seed(site, month_label, fleet_number):
    if not site or not month_label or not fleet_number:
        return (None, None)

    pm_label = prev_month_label(month_label)

    prev_sched_name = frappe.db.get_value(
        "Service Schedule",
        {"site": site, "month": pm_label},
        "name"
    )
    if not prev_sched_name:
        return (None, None)

    last_row = frappe.db.get_value(
        "Service Schedule Child",
        {"parent": prev_sched_name, "fleet_number": fleet_number},
        ["estimate_hours", "daily_estimated_hours_usage"],
        order_by="date desc"
    )
    if not last_row:
        return (None, None)

    prev_est = float(last_row[0] or 0)
    prev_daily = float(last_row[1] or 0)
    return (prev_est, prev_daily)






def batch_get_service_reports(asset_list, month_start, month_end):
    """Fetch all MSRs where service_breakdown='Service' up to month_end."""
    if not asset_list:
        return {}

    rows = frappe.get_all(
        "Mechanical Service Report",
        filters={
            "asset": ["in", asset_list],
            "service_breakdown": "Service",
            "service_date": ("<=", month_end),
        },
        fields=["name", "asset", "service_date", "current_hours", "service_interval", "reference_number"],
        order_by="asset asc, service_date asc",
    )

    out = {a: {"before": None, "within": []} for a in asset_list}
    for r in rows:
        asset = r.get("asset")
        if asset not in out:
            continue
        sdate = as_date(r.get("service_date"))
        if not sdate:
            continue
        if sdate < month_start:
            out[asset]["before"] = r  # keep last before month start
        else:
            out[asset]["within"].append(r)
    return out

def compute_next_service_label(planned_hours):
    """
    Excel rule: next_service_interval_* is derived from planned_hours_next_service_*
    using the repeating pattern:
    250->500, 500->750, 750->1000, 1000->250, 1250->500, 1500->750, 1750->2000, 2000->250 (repeat)

    Returns a STRING like "500 Hours" (Data field friendly).
    """
    h = cint(planned_hours) or 0
    if h <= 0:
        return ""

    rem = int(h) % 2000

    mapping = {
        250: 500,
        500: 750,
        750: 1000,
        1000: 250,
        1250: 500,
        1500: 750,
        1750: 2000,
        0: 250,   # 2000, 4000, etc.
    }

    nxt = mapping.get(rem, 0)
    return f"{nxt} Hours" if nxt else ""

def find_threshold_crossing_date(series, planned_hours):
    """series: list of (date, estimate_hours) sorted asc.
    Returns first date where estimate crosses planned (>= planned and previous < planned).
    """
    if not planned_hours:
        return None
    prev_est = None
    for d, est in series:
        if est is None:
            continue
        try:
            est_v = float(est)
        except Exception:
            continue
        if prev_est is None:
            if est_v >= planned_hours:
                return d
        else:
            if prev_est < planned_hours <= est_v:
                return d
        prev_est = est_v
    return None

@frappe.whitelist()
def generate_schedule_backend(schedule_name, daily_usage_default=15):
    """Populate Service Schedule Child exactly as per Task 1 (based on latest DocTypes)."""
    doc = frappe.get_doc("Service Schedule", schedule_name)

    if not doc.month or not doc.site:
        frappe.throw("Please select Month and Site before generating the schedule.")

    _, _, month_start, month_end = parse_month_bounds(doc.month)

    assets = get_assets_for_site(doc.site)
    asset_list = [a["name"] for a in assets]

    # all dates in month
    date_list = []
    cur = month_start
    while cur <= month_end:
        date_list.append(cur)
        cur = cur + timedelta(days=1)

    start_hours_map = batch_get_day_shift_start_hours(asset_list, month_start, month_end)
    msr_map = batch_get_service_reports(asset_list, month_start, month_end)

    # clear
    doc.set("service_schedule_child", [])

    rows_index = {}   # (asset, date_iso) -> row
    est_series = {a: [] for a in asset_list}

    daily_usage_default = clamp_daily_usage(daily_usage_default or 0)

    # We'll compute per-asset default daily usage from last 30 days (rolling window)
    asset_daily_default = {}
    anchor = month_start - timedelta(days=1)  # same anchor for all assets
    for a in assets:
        asset_name = a["name"]
        asset_daily_default[asset_name] = get_last_30_day_avg_daily_usage(asset_name, anchor)



    # --- Now generate rows per asset ---
    for a in assets:
        asset = a["name"]

        prev_estimate = None  # track previous day's estimate per asset

        # per-asset default daily usage (rolling 30 days)
        daily_use_asset = asset_daily_default.get(asset, daily_usage_default)

        before_row = (msr_map.get(asset) or {}).get("before")
        within_rows = (msr_map.get(asset) or {}).get("within") or []
        within_rows = sorted(within_rows, key=lambda r: as_date(r.get("service_date")) or month_start)
        ptr = 0
        latest_within = None

        for d in date_list:
            d_iso = d.isoformat()

            # start_hours from Day-shift pre-use (or 0)
            start_hours = start_hours_map.get((d_iso, asset), 0) or 0
            try:
                start_hours = float(start_hours)
            except Exception:
                start_hours = 0.0

            # estimate_hours per Task 1 (+ Day 1 carry-over rule)
            if start_hours > 0:
                estimate_hours = start_hours
            else:
                if d == month_start:
                    # day 1 with 0 start hours seeds from previous month last estimate + prev month daily usage
                    prev_est, prev_daily = get_prev_month_seed(doc.site, doc.month, asset)
                    if prev_est is not None and prev_daily is not None:
                        estimate_hours = float(prev_est) + clamp_daily_usage(prev_daily)
                    else:
                        estimate_hours = float(daily_use_asset)
                else:
                    prev_val = prev_estimate if prev_estimate is not None else 0.0
                    estimate_hours = float(prev_val) + float(daily_use_asset)

            prev_estimate = float(estimate_hours or 0.0)

            # previous service per Task 1
            if d == month_start:
                chosen = before_row
            else:
                while ptr < len(within_rows):
                    sr = within_rows[ptr]
                    sr_date = as_date(sr.get("service_date"))
                    if sr_date and sr_date <= d:
                        latest_within = sr
                        ptr += 1
                    else:
                        break
                chosen = latest_within

            date_of_previous_service = as_date(chosen.get("service_date")) if chosen else None
            hours_previous_service = cint(chosen.get("current_hours")) if chosen else 0
            last_service_interval = (chosen.get("service_interval") or "") if chosen else ""
            msr_reference_number = ""
            msr_record_name = ""

            if chosen:
                msr_reference_number = chosen.get("reference_number") or ""
                # IMPORTANT: this is the MSR document name (docname) used in the URL
                msr_record_name = chosen.get("name") or ""

            msr_reference_number = str(msr_reference_number or "")
            msr_record_name = str(msr_record_name or "")







            row = doc.append("service_schedule_child", {
                "date": d,
                "fleet_number": asset,
                "asset_category": a.get("asset_category"),
                "model": a.get("item_name") or a.get("item_code"),
                "start_hours": start_hours if start_hours else 0,
                "daily_estimated_hours_usage": daily_use_asset,
                "estimate_hours": estimate_hours,
                "date_of_previous_service": date_of_previous_service,
                "hours_previous_service": hours_previous_service or 0,
                "last_service_interval": last_service_interval or 0,
                "msr_reference_number": msr_reference_number,
                "msr_record_name": msr_record_name,

            })

            rows_index[(asset, d_iso)] = row
            est_series[asset].append((d, estimate_hours))




    # Next service markers (1/2/3). Latest JSON has date_of_next_service_1 and _2, but NOT _3.
    for asset in asset_list:
        # Use the FIRST row in the month where hours_previous_service > 0
        base_hours = 0
        for d in date_list:
            r0 = rows_index.get((asset, d.isoformat()))
            if not r0:
                continue
            bh = cint(getattr(r0, "hours_previous_service", 0)) or 0
            if bh > 0:
                base_hours = bh
                break

        if base_hours <= 0:
            continue


        planned1 = ceiling_to_250(base_hours)
        planned2 = planned1 + 250
        planned3 = planned2 + 250

        # Populate planned hours on EVERY row for this asset (child table visibility)
        for d in date_list:
            r_all = rows_index.get((asset, d.isoformat()))
            if not r_all:
                continue

            r_all.planned_hours_next_service_1 = planned1
            r_all.planned_hours_next_service_2 = planned2
            r_all.planned_hours_of_service_3 = planned3


        d1 = find_threshold_crossing_date(est_series[asset], planned1)
        d2 = find_threshold_crossing_date(est_series[asset], planned2)
        d3 = find_threshold_crossing_date(est_series[asset], planned3)

        d1 = adjust_sunday_to_saturday(d1, month_start=month_start)
        d2 = adjust_sunday_to_saturday(d2, month_start=month_start)
        d3 = adjust_sunday_to_saturday(d3, month_start=month_start)







        if d1:
            r = rows_index.get((asset, d1.isoformat()))
            if r:
                r.date_of_next_service_1 = d1
                r.planned_hours_next_service_1 = planned1
                r.next_service_interval_1 = "250"

        if d2:
            r = rows_index.get((asset, d2.isoformat()))
            if r:
                r.date_of_next_service_2 = d2
                r.planned_hours_next_service_2 = planned2
                r.next_service_interval_2 = "500"

        if d3:
            r = rows_index.get((asset, d3.isoformat()))
            if r:
                r.date_of_next_service_3 = d3
                r.planned_hours_of_service_3 = planned3
                r.next_service_interval_3 = "750"


    doc.save()
    frappe.db.commit()
    return {"ok": True, "rows": len(doc.service_schedule_child)}

@frappe.whitelist()
def set_daily_usage_and_recompute(schedule_name, fleet_number, daily_usage):
    """Capture daily usage edits from HTML and recompute estimates + next service markers for that asset."""
    doc = frappe.get_doc("Service Schedule", schedule_name)
    if not doc.month:
        frappe.throw("Month is required.")
    _, _, month_start, _ = parse_month_bounds(doc.month)

    daily_use = clamp_daily_usage(daily_usage or 0)

    rows = [r for r in doc.service_schedule_child if r.fleet_number == fleet_number]
    rows.sort(key=lambda r: getdate(r.date))

    prev_estimate = None
    series = []
    for r in rows:
        r.daily_estimated_hours_usage = daily_use
        start_hours = float(r.start_hours or 0)
        # keep MSR link fields stable (never None)
        r.msr_reference_number = str(r.msr_reference_number or "")
        r.msr_record_name = str(r.msr_record_name or "")

        if start_hours > 0:
            r.estimate_hours = start_hours
        else:
            if getdate(r.date) == month_start:
                # NEW: day 1 with 0 start hours seeds from previous month
                prev_est, prev_daily = get_prev_month_seed(doc.site, doc.month, fleet_number)
                if prev_est is not None and prev_daily is not None:
                    r.estimate_hours = float(prev_est) + clamp_daily_usage(prev_daily)
                else:
                    # fallback to old behavior
                    r.estimate_hours = float(daily_use)
            else:
                prev_val = prev_estimate if prev_estimate is not None else 0.0
                r.estimate_hours = float(prev_val) + float(daily_use)


        prev_estimate = float(r.estimate_hours or 0.0)
        series.append((getdate(r.date), float(r.estimate_hours or 0.0)))


        # clear markers
        r.date_of_next_service_1 = None
        r.planned_hours_next_service_1 = None
        r.next_service_interval_1 = ""

        r.date_of_next_service_2 = None
        r.planned_hours_next_service_2 = None
        r.next_service_interval_2 = ""

        r.date_of_next_service_3 = None
        r.planned_hours_of_service_3 = None
        r.next_service_interval_3 = ""


    if rows:
        # Use the FIRST row where hours_previous_service > 0 (rows already sorted by date)
        base_hours = 0
        for r0 in rows:
            bh = cint(r0.hours_previous_service) or 0
            if bh > 0:
                base_hours = bh
                break

        if base_hours > 0:

            planned1 = ceiling_to_250(base_hours)
            planned2 = planned1 + 250
            planned3 = planned2 + 250

            # Populate planned hours on EVERY row for this fleet (child table visibility)
            for r in rows:
                r.planned_hours_next_service_1 = planned1
                r.planned_hours_next_service_2 = planned2
                r.planned_hours_of_service_3 = planned3


            d1 = adjust_sunday_to_saturday(find_threshold_crossing_date(series, planned1), month_start=month_start)
            d2 = adjust_sunday_to_saturday(find_threshold_crossing_date(series, planned2), month_start=month_start)
            d3 = adjust_sunday_to_saturday(find_threshold_crossing_date(series, planned3), month_start=month_start)

            if d1:
                for r in rows:
                    if getdate(r.date) == d1:
                        r.date_of_next_service_1 = d1
                        r.planned_hours_next_service_1 = planned1
                        r.next_service_interval_1 = "250"
                        break
            if d2:
                for r in rows:
                    if getdate(r.date) == d2:
                        r.date_of_next_service_2 = d2
                        r.planned_hours_next_service_2 = planned2
                        r.next_service_interval_2 = "500"
                        break
            if d3:
                for r in rows:
                    if getdate(r.date) == d3:
                        r.date_of_next_service_3 = d3
                        r.planned_hours_of_service_3 = planned3
                        r.next_service_interval_3 = "750"
                        break

    doc.save()
    frappe.db.commit()
    return {"ok": True, "rows": len(rows)}


# ============================================================================
# ENGINE: OVERDUE EMAILS (matches current JS logic)
# - Trigger ONLY when (overdue_date == today)
# - Suppress overdue if MSR exists (green-border logic) within interval window
# - One email per asset
# - Designed for scheduler 07:00, but can be run manually in console
# ============================================================================

def _ss_today_str(today_override=None):
    d = getdate(today_override) if today_override else getdate(nowdate())
    return str(d)

def _ss_ensure_overdue_log_table():
    # simple dedupe storage without creating a DocType
    frappe.db.sql("""
        CREATE TABLE IF NOT EXISTS `tabSS Overdue Email Log` (
            `name` varchar(140) NOT NULL,
            `creation` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
            `modified` datetime(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            `fleet_number` varchar(140),
            `overdue_date` date,
            `schedule_name` varchar(140),
            PRIMARY KEY (`name`),
            UNIQUE KEY `uniq_fleet_date` (`fleet_number`, `overdue_date`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    frappe.db.commit()

def _ss_already_sent(fleet_number, overdue_date):
    _ss_ensure_overdue_log_table()
    row = frappe.db.sql("""
        SELECT name FROM `tabSS Overdue Email Log`
        WHERE fleet_number=%s AND overdue_date=%s
        LIMIT 1
    """, (fleet_number, overdue_date), as_dict=True)
    return bool(row)

def _ss_mark_sent(fleet_number, overdue_date, schedule_name):
    _ss_ensure_overdue_log_table()
    name = f"{fleet_number}-{overdue_date}"
    try:
        frappe.db.sql("""
            INSERT IGNORE INTO `tabSS Overdue Email Log` (name, fleet_number, overdue_date, schedule_name)
            VALUES (%s, %s, %s, %s)
        """, (name, fleet_number, overdue_date, schedule_name))
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "SS Overdue Email Log insert failed")

def _ss_pick_interval_anchor_interval(row):
    iv = row.get("next_service_interval_1") or row.get("next_service_interval_2") or row.get("next_service_interval_3")
    if iv is None:
        return None

    # allow values like "250 Hours"
    s = "".join(ch for ch in str(iv) if ch.isdigit())
    if not s:
        return None

    ivn = int(s)
    return ivn if ivn in (250, 500, 750, 1000, 2000) else None


def _ss_collect_msr_dates_by_fleet(rows):
    # match your JS intent: MSR event exists when date_of_previous_service + (ref or name) exists
    msr_dates = {}
    for r in rows:
        fleet = r.get("fleet_number")
        if not fleet:
            continue
        dps = r.get("date_of_previous_service")
        if not dps:
            continue
        if not (r.get("msr_record_name") or r.get("msr_reference_number")):
            continue
        msr_date = str(getdate(dps))
        msr_dates.setdefault(fleet, set()).add(msr_date)
    return msr_dates

def _ss_compute_overdue_today_events_for_schedule(doc, today_str):
    rows = [r.as_dict() for r in (doc.get("service_schedule_child") or [])]
    if not rows:
        return []

    # sort rows per fleet by date
    rows.sort(key=lambda x: (str(x.get("fleet_number") or ""), str(getdate(x.get("date")) if x.get("date") else "9999-12-31")))

    msr_dates_by_fleet = _ss_collect_msr_dates_by_fleet(rows)

    # group by fleet
    by_fleet = {}
    for r in rows:
        fleet = r.get("fleet_number")
        if not fleet or not r.get("date"):
            continue
        by_fleet.setdefault(fleet, []).append(r)

    events = []
    for fleet, frs in by_fleet.items():
        # sort by date
        frs.sort(key=lambda x: str(getdate(x.get("date"))))

        # find anchor indices (interval cells)
        anchors = []
        for idx, r in enumerate(frs):
            iv = _ss_pick_interval_anchor_interval(r)
            if iv:
                anchors.append((idx, iv))

        if not anchors:
            continue

        # evaluate each anchor window (until next anchor)
        for ai, (anchor_idx, interval_iv) in enumerate(anchors):
            window_end = anchors[ai + 1][0] if (ai + 1) < len(anchors) else len(frs)
            anchor_row = frs[anchor_idx]
            anchor_date = str(getdate(anchor_row.get("date")))

            # anchor est = interval cell est
            try:
                anchor_est = float(anchor_row.get("estimate_hours") or 0)
            except Exception:
                anchor_est = 0.0

            threshold = anchor_est + 50.0

            # JS suppression: if ANY green-border in window => suppress overdue for this interval
            # green-border == MSR date exists within this window
            serviced_in_window = False
            msr_dates = msr_dates_by_fleet.get(fleet, set())
            if msr_dates:
                for j in range(anchor_idx, window_end):
                    d = str(getdate(frs[j].get("date")))
                    if d in msr_dates:
                        serviced_in_window = True
                        break
            if serviced_in_window:
                continue

            # find first later row where est >= threshold
            overdue_date = None
            for j in range(anchor_idx + 1, window_end):
                try:
                    est = float(frs[j].get("estimate_hours") or 0)
                except Exception:
                    continue
                if est >= threshold:
                    overdue_date = str(getdate(frs[j].get("date")))
                    break

            if overdue_date and overdue_date == today_str:
                events.append({
                    "schedule_name": doc.name,
                    "site": doc.get("site") or "",
                    "fleet_number": fleet,
                    "service_interval": interval_iv,
                    "overdue_date": overdue_date,
                })

    return events

def ss_overdue_email_daily_job():
    # scheduler entrypoint (07:00 daily)
    # keep dry_run=0 for real run (it will queue/send if email account exists)
    run_overdue_email_engine(dry_run=0)


@frappe.whitelist()
def run_overdue_email_engine(dry_run=1, today_override=None, test_recipient="juan@isambane.co.za"):
    """
    dry_run=1: does NOT send, returns what WOULD send
    dry_run=0: queues/sends emails (requires Outgoing Email Account configured)
    today_override="YYYY-MM-DD": for testing without waiting for real 'today'
    """
    dry_run = cint(dry_run) or 0
    today_str = _ss_today_str(today_override)

    schedules = frappe.get_all("Service Schedule", fields=["name"])
    all_events = []

    for s in schedules:
        doc = frappe.get_doc("Service Schedule", s.name)
        events = _ss_compute_overdue_today_events_for_schedule(doc, today_str)
        all_events.extend(events)

    # one email per asset (event)
    outbound = []
    for e in all_events:
        fleet = e["fleet_number"]
        od = e["overdue_date"]

        # dedupe per fleet+date
        if _ss_already_sent(fleet, od):
            continue

        subject = f"🚨⚠️ {fleet} needs attention"
        message = f"""
        <p>🚨🚨 <b>Warning asset needs attention!</b> 🚨🚨</p>
        <ul>
          <li><b>Site:</b> {frappe.utils.escape_html(str(e.get("site") or ""))}</li>
          <li><b>Fleet Number:</b> {frappe.utils.escape_html(str(fleet))}</li>
          <li><b>Service Interval:</b> {frappe.utils.escape_html(str(e.get("service_interval")))} Hours</li>
          <li><b>Overdue Date:</b> {frappe.utils.escape_html(str(od))}</li>
          <li><b>Service Schedule:</b> {frappe.utils.escape_html(str(e.get("schedule_name")))} </li>
        </ul>
        <p><b>Sender:</b> MaintenancePlanning</p>
        """

        outbound.append({
            "to": test_recipient,
            "subject": subject,
            "message": message,
            "event": e
        })

        if not dry_run:
            try:
                frappe.sendmail(
                    recipients=[test_recipient],
                    subject=subject,
                    message=message
                )
                _ss_mark_sent(fleet, od, e.get("schedule_name"))
            except Exception:
                frappe.log_error(frappe.get_traceback(), "SS Overdue Email send failed")

    return {
        "today": today_str,
        "dry_run": bool(dry_run),
        "total_schedules": len(schedules),
        "matched_events": all_events,
        "outbound": outbound
    }
