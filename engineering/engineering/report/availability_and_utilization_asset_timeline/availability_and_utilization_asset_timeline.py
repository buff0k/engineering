from datetime import timedelta

import frappe
from frappe.utils import add_days, get_datetime, getdate


# Window: 06:00 today -> 06:00 next day
START_HOUR = 6

# Based on your AU engine: breakdown_status == "3" means resolved
RESOLVED_STATUS = "3"

# Site fatigue rules (same pattern as your AU code)
FATIGUE_13_1330 = {"uitgevallen", "koppie", "bankfontein"}
FATIGUE_13_14 = {"gwab", "klipfontein", "kriel"}


def execute(filters=None):
    filters = filters or {}

    # Site fallback
    site = (
        (filters.get("site") or filters.get("location") or frappe.defaults.get_user_default("location") or "")
    ).strip()
    if not site:
        frappe.throw("Site is required (set the Site filter at the top of the report).")

    asset_category = (filters.get("asset_category") or "").strip()

    start_date = getdate(filters.get("start_date"))
    end_date = getdate(filters.get("end_date") or filters.get("start_date"))
    if end_date < start_date:
        frappe.throw("End Date must be >= Start Date")

    columns = _get_columns()
    data = []
    row_no = 1

    d = start_date
    while d <= end_date:
        window_start = get_datetime(f"{d} {START_HOUR:02d}:00:00")
        window_end = get_datetime(f"{add_days(d, 1)} {START_HOUR:02d}:00:00")

        shift_system = _get_shift_system(site, d)
        fixed = _fixed_windows(site, window_start, shift_system)

        # Asset list filtered by site + category
        asset_list = _get_assets(site, asset_category)

        # If multiple days, append date so rows stay unique per day
        show_date_in_asset = start_date != end_date

        for plant_no in asset_list:
            breakdown_intervals = _get_breakdown_intervals(
                site=site,
                plant_no=plant_no,
                window_start=window_start,
                window_end=window_end,
            )

            asset_label = plant_no
            if show_date_in_asset:
                asset_label = f"{plant_no} ({d})"

            row = {"no": row_no, "asset": asset_label}

            for i, (hs, he) in enumerate(_hour_slots(window_start)):
                # Priority:
                # Startup > Fatigue > Breakdown > Blank
                status = ""
                if _overlaps_any(hs, he, fixed["startup"]):
                    status = "S"
                elif _overlaps_any(hs, he, fixed["fatigue"]):
                    status = "F"
                elif _overlaps_any(hs, he, breakdown_intervals):
                    status = "B"

                row[f"h_{i:02d}"] = status

            # Right-side boundary label "06:00" (blank cell, only for look)
            row["end_0600"] = ""

            data.append(row)
            row_no += 1

        d = add_days(d, 1)

    return columns, data


def _get_columns():
    cols = [
        {"label": "No", "fieldname": "no", "fieldtype": "Int", "width": 50},
        {"label": "ASSETS", "fieldname": "asset", "fieldtype": "Data", "width": 180},
    ]

    # Wider columns + full range labels: 06:00 - 07:00, etc.
    for i in range(24):
        start_h = (START_HOUR + i) % 24
        end_h = (start_h + 1) % 24
        label = f"{start_h:02d}:00 - {end_h:02d}:00"
        cols.append(
            {"label": label, "fieldname": f"h_{i:02d}", "fieldtype": "Data", "width": 95}
        )

    # boundary (like Excel)
    cols.append({"label": "06:00", "fieldname": "end_0600", "fieldtype": "Data", "width": 60})
    return cols


def _get_assets(site, asset_category):
    """
    Returns plant numbers (Asset.asset_name) filtered by:
      - Asset.location == site (if field exists)
      - Asset.asset_category == asset_category (if provided)
    Fallback: if Asset not usable, returns distinct Breakdown History.asset_name for the site.
    """
    # Best: use Asset doctype so we can filter by category
    if frappe.db.exists("DocType", "Asset"):
        try:
            meta = frappe.get_meta("Asset")
            filters = {"docstatus": 1}

            if meta.has_field("location"):
                filters["location"] = site

            if asset_category and meta.has_field("asset_category"):
                filters["asset_category"] = asset_category

            rows = frappe.get_all(
                "Asset",
                filters=filters,
                fields=["asset_name", "name"],
                order_by="asset_name asc",
            )

            out = []
            for r in rows:
                plant_no = (r.get("asset_name") or r.get("name") or "").strip()
                if plant_no:
                    out.append(plant_no)

            if out:
                return out
        except Exception:
            pass

    # Fallback: cannot filter by category here because Breakdown History doesn't store category
    rows = frappe.db.sql(
        """
        select distinct asset_name
        from `tabBreakdown History`
        where location = %s
          and ifnull(asset_name,'') != ''
        order by asset_name asc
        """,
        (site,),
        as_dict=True,
    )
    return [r["asset_name"] for r in rows]


def _get_shift_system(site, shift_date):
    # Optional: use Monthly Production Planning if it exists
    if frappe.db.exists("DocType", "Monthly Production Planning"):
        row = frappe.get_all(
            "Monthly Production Planning",
            filters={
                "location": site,
                "site_status": "Producing",
                "prod_month_start_date": ["<=", shift_date],
                "prod_month_end_date": [">=", shift_date],
            },
            fields=["shift_system"],
            limit=1,
        )
        if row and row[0].get("shift_system"):
            return (row[0]["shift_system"] or "").strip()

    return "2x12Hour"


def _fixed_windows(site, window_start, shift_system):
    loc = (site or "").strip().lower()
    d0 = getdate(window_start).strftime("%Y-%m-%d")
    d1 = getdate(window_start + timedelta(days=1)).strftime("%Y-%m-%d")

    def dt(d, t):
        return get_datetime(f"{d} {t}")

    startup = []
    fatigue = []

    # Startup always 06:00–07:00
    startup.append((dt(d0, "06:00:00"), dt(d0, "07:00:00")))

    # Extra startup by shift system
    if (shift_system or "").lower() == "2x12hour":
        startup.append((dt(d0, "18:00:00"), dt(d0, "19:00:00")))
    elif (shift_system or "").lower() == "3x8hour":
        startup.append((dt(d0, "14:00:00"), dt(d0, "15:00:00")))
        startup.append((dt(d0, "22:00:00"), dt(d0, "23:00:00")))

    # Fatigue day window by site rules
    if loc in FATIGUE_13_1330:
        fatigue.append((dt(d0, "13:00:00"), dt(d0, "13:30:00")))
    elif loc in FATIGUE_13_14:
        fatigue.append((dt(d0, "13:00:00"), dt(d0, "14:00:00")))

    # Night fatigue always 01:00–02:00
    fatigue.append((dt(d1, "01:00:00"), dt(d1, "02:00:00")))

    window_end = window_start + timedelta(days=1)
    return {
        "startup": _clip_to_window(startup, window_start, window_end),
        "fatigue": _clip_to_window(fatigue, window_start, window_end),
    }


def _clip_to_window(intervals, w_start, w_end):
    out = []
    for s, e in intervals:
        if e <= w_start or s >= w_end:
            continue
        out.append((max(s, w_start), min(e, w_end)))
    return out


def _get_breakdown_intervals(site, plant_no, window_start, window_end):
    if not frappe.db.exists("DocType", "Breakdown History"):
        return []

    base_filters = {
        "location": site,
        "asset_name": plant_no,
        "exclude_from_au": 0,
    }

    last_before = frappe.get_all(
        "Breakdown History",
        filters={**base_filters, "update_date_time": ["<", window_start]},
        fields=["update_date_time", "breakdown_status"],
        order_by="update_date_time desc",
        limit=1,
    )

    events = frappe.get_all(
        "Breakdown History",
        filters={**base_filters, "update_date_time": ["between", [window_start, window_end]]},
        fields=["update_date_time", "breakdown_status"],
        order_by="update_date_time asc",
    )

    if not last_before and not events:
        return []

    in_breakdown = False
    current_start = None
    intervals = []

    # Active at window start?
    if last_before and str(last_before[0].get("breakdown_status") or "") != RESOLVED_STATUS:
        in_breakdown = True
        current_start = window_start

    for ev in events:
        ev_time = ev.get("update_date_time")
        if not ev_time:
            continue

        ev_status = str(ev.get("breakdown_status") or "")

        # Start
        if ev_status != RESOLVED_STATUS and not in_breakdown:
            in_breakdown = True
            current_start = ev_time

        # End
        elif ev_status == RESOLVED_STATUS and in_breakdown:
            s = max(current_start, window_start)
            e = min(ev_time, window_end)
            if e > s:
                intervals.append((s, e))
            in_breakdown = False
            current_start = None

    # Still active at window end
    if in_breakdown and current_start:
        s = max(current_start, window_start)
        e = window_end
        if e > s:
            intervals.append((s, e))

    return intervals


def _hour_slots(window_start):
    for i in range(24):
        hs = window_start + timedelta(hours=i)
        he = hs + timedelta(hours=1)
        yield hs, he


def _overlaps_any(a_start, a_end, intervals):
    for s, e in intervals:
        if e > a_start and s < a_end:
            return True
    return False