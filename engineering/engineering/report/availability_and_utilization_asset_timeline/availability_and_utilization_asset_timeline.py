from collections import defaultdict
from datetime import timedelta

import frappe
from frappe.utils import add_days, get_datetime, getdate


# Default window start
START_HOUR = 6

# Based on your AU engine: breakdown_status == "3" means resolved
RESOLVED_STATUS = "3"

# Saturday site rules
SATURDAY_15_00_SITES = {
    "uitgevallen",
    "koppie",
    "kriel rehabilitation",
    "bankfontein",
}

SATURDAY_18_06_SITES = {
    "klipfontein",
    "gwab",
}

# Fatigue rules
FATIGUE_13_1330 = {"uitgevallen", "koppie", "bankfontein"}
FATIGUE_13_14 = {"gwab", "klipfontein", "kriel", "kriel rehabilitation"}


def execute(filters=None):
    filters = filters or {}

    site = (
        (
            filters.get("site")
            or filters.get("location")
            or frappe.defaults.get_user_default("location")
            or ""
        )
    ).strip()
    if not site:
        frappe.throw("Site is required (set the Site filter at the top of the report).")

    asset_category = (filters.get("asset_category") or "").strip()

    start_date = getdate(filters.get("start_date"))
    end_date = getdate(filters.get("end_date") or filters.get("start_date"))
    if end_date < start_date:
        frappe.throw("End Date must be >= Start Date")

    # Determine max slot count across selected dates
    max_slots = _get_max_slots_for_range(site, start_date, end_date)
    columns = _get_columns(max_slots)

    data = []
    row_no = 1

    # Load assets once for speed
    asset_list = _get_assets(site, asset_category)
    show_date_in_asset = start_date != end_date

    d = start_date
    while d <= end_date:
        window_cfg = _get_window_config(site, d)
        window_start = window_cfg["window_start"]
        window_end = window_cfg["window_end"]
        slot_count = window_cfg["slot_count"]

        shift_system = _get_shift_system(site, d)
        fixed = _fixed_windows(site, d, window_start, shift_system)

        # Load all PBM intervals for all assets in one go for speed
        intervals_map = _get_breakdown_intervals_map(
            site=site,
            asset_list=asset_list,
            window_start=window_start,
            window_end=window_end,
        )

        for plant_no in asset_list:
            breakdown_intervals = intervals_map.get(plant_no) or []

            asset_label = plant_no
            if show_date_in_asset:
                asset_label = f"{plant_no} ({d})"

            row = {"no": row_no, "asset": asset_label}

            # Fill only active slots for this day/site config
            for i, (hs, he) in enumerate(_hour_slots(window_start, slot_count)):
                cell_value = ""

                # Fixed windows always win:
                # Startup > Fatigue > Breakdown > Blank
                if _overlaps_any(hs, he, fixed["startup"]):
                    cell_value = "S"
                elif _overlaps_any(hs, he, fixed["fatigue"]):
                    cell_value = "F"
                else:
                    breakdown_docname = _get_breakdown_doc_for_slot(
                        hs, he, breakdown_intervals
                    )
                    if breakdown_docname:
                        cell_value = f"B::{breakdown_docname}"

                row[f"h_{i:02d}"] = cell_value

            # Blank out unused trailing columns if this date has fewer slots
            for i in range(slot_count, max_slots):
                row[f"h_{i:02d}"] = ""

            row["end_marker"] = ""
            data.append(row)
            row_no += 1

        d = add_days(d, 1)

    return columns, data


def _get_max_slots_for_range(site, start_date, end_date):
    max_slots = 0
    d = start_date
    while d <= end_date:
        cfg = _get_window_config(site, d)
        max_slots = max(max_slots, cfg["slot_count"])
        d = add_days(d, 1)
    return max_slots or 24


def _get_window_config(site, shift_date):
    """
    Saturday special:
      Uitgevallen / Koppie / Kriel Rehabilitation / Bankfontein
        06:00 -> 00:00  (18 slots)

      Klipfontein / Gwab
        06:00 -> 06:00 next day (24 slots)

    Other days:
        06:00 -> 06:00 next day (24 slots)
    """
    loc = (site or "").strip().lower()
    window_start = get_datetime(f"{shift_date} {START_HOUR:02d}:00:00")

    # Saturday = 5
    if shift_date.weekday() == 5 and loc in SATURDAY_15_00_SITES:
        return {
            "window_start": window_start,
            "window_end": get_datetime(f"{shift_date} 23:59:59"),
            "slot_count": 18,  # 06:00 -> 00:00
        }

    return {
        "window_start": window_start,
        "window_end": get_datetime(f"{add_days(shift_date, 1)} {START_HOUR:02d}:00:00"),
        "slot_count": 24,
    }


def _get_columns(slot_count):
    cols = [
        {"label": "No", "fieldname": "no", "fieldtype": "Int", "width": 50},
        {"label": "ASSETS", "fieldname": "asset", "fieldtype": "Data", "width": 180},
    ]

    for i in range(slot_count):
        start_h = (START_HOUR + i) % 24
        end_h = (start_h + 1) % 24
        label = f"{start_h:02d}:00 - {end_h:02d}:00"
        cols.append(
            {
                "label": label,
                "fieldname": f"h_{i:02d}",
                "fieldtype": "Data",
                "width": 130,
            }
        )

    cols.append(
        {"label": "", "fieldname": "end_marker", "fieldtype": "Data", "width": 30}
    )
    return cols


def _get_assets(site, asset_category):
    """
    Returns Asset document names filtered by:
      - Asset.location == site (if field exists)
      - Asset.asset_category == asset_category (if provided)

    PBM.asset_name is a Link to Asset, so matching uses Asset.name.
    """
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
                fields=["name", "asset_name"],
                order_by="asset_name asc",
            )

            out = []
            for r in rows:
                plant_no = (r.get("name") or "").strip()
                if plant_no:
                    out.append(plant_no)

            if out:
                return out
        except Exception:
            pass

    rows = frappe.db.sql(
        """
        select distinct asset_name
        from `tabPlant Breakdown or Maintenance`
        where location = %s
          and ifnull(asset_name, '') != ''
        order by asset_name asc
        """,
        (site,),
        as_dict=True,
    )
    return [r["asset_name"] for r in rows]


def _get_shift_system(site, shift_date):
    """
    Saturday overrides:
      Uitgevallen / Koppie / Kriel Rehabilitation / Bankfontein
        startup at 06:00 and 15:00

      Klipfontein / Gwab
        startup at 06:00 and 18:00
    """
    loc = (site or "").strip().lower()

    if shift_date.weekday() == 5:
        if loc in SATURDAY_15_00_SITES:
            return "SATURDAY_2X9"
        if loc in SATURDAY_18_06_SITES:
            return "SATURDAY_2X12"

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


def _fixed_windows(site, shift_date, window_start, shift_system):
    loc = (site or "").strip().lower()
    d0 = getdate(window_start).strftime("%Y-%m-%d")
    d1 = getdate(window_start + timedelta(days=1)).strftime("%Y-%m-%d")

    def dt(d, t):
        return get_datetime(f"{d} {t}")

    startup = []
    fatigue = []

    # Always startup 06:00–07:00
    startup.append((dt(d0, "06:00:00"), dt(d0, "07:00:00")))

    shift_system_key = (shift_system or "").strip().lower()

    # Saturday overrides
    if shift_system_key == "saturday_2x9":
        startup.append((dt(d0, "15:00:00"), dt(d0, "16:00:00")))
    elif shift_system_key == "saturday_2x12":
        startup.append((dt(d0, "18:00:00"), dt(d0, "19:00:00")))
    # Normal rules
    elif shift_system_key == "2x12hour":
        startup.append((dt(d0, "18:00:00"), dt(d0, "19:00:00")))
    elif shift_system_key == "3x8hour":
        startup.append((dt(d0, "14:00:00"), dt(d0, "15:00:00")))
        startup.append((dt(d0, "22:00:00"), dt(d0, "23:00:00")))

    # Fatigue
    if loc in FATIGUE_13_1330:
        fatigue.append((dt(d0, "13:00:00"), dt(d0, "13:30:00")))
    elif loc in FATIGUE_13_14:
        fatigue.append((dt(d0, "13:00:00"), dt(d0, "14:00:00")))

    # Night fatigue 01:00–02:00
    fatigue.append((dt(d1, "01:00:00"), dt(d1, "02:00:00")))

    # Clip to actual report window
    return {
        "startup": _clip_to_window(startup, window_start, _get_window_end(site, shift_date)),
        "fatigue": _clip_to_window(fatigue, window_start, _get_window_end(site, shift_date)),
    }


def _get_window_end(site, shift_date):
    return _get_window_config(site, shift_date)["window_end"]


def _clip_to_window(intervals, w_start, w_end):
    out = []
    for s, e in intervals:
        if e <= w_start or s >= w_end:
            continue
        out.append((max(s, w_start), min(e, w_end)))
    return out


def _get_breakdown_intervals_map(site, asset_list, window_start, window_end):
    """
    Fast path:
      1) Load PBM rows for all assets in one query
      2) Group intervals by asset
      3) Fallback to Breakdown History only for assets with no PBM interval
    """
    out = defaultdict(list)

    if not asset_list:
        return out

    # 1) Primary source: PBM
    if frappe.db.exists("DocType", "Plant Breakdown or Maintenance"):
        pbm_rows = frappe.get_all(
            "Plant Breakdown or Maintenance",
            filters={
                "location": site,
                "asset_name": ["in", asset_list],
                "exclude_from_au": 0,
                "breakdown_start_datetime": ["<", window_end],
            },
            fields=[
                "name",
                "asset_name",
                "downtime_type",
                "breakdown_start_datetime",
                "resolved_datetime",
                "open_closed",
                "breakdown_reason",
                "resolution_summary",
                "hours_breakdown_starts",
                "shift",
                "item_name",
                "asset_category",
            ],
            order_by="asset_name asc, breakdown_start_datetime asc",
        )

        now_dt = get_datetime()

        for r in pbm_rows:
            plant_no = r.get("asset_name")
            start_dt = r.get("breakdown_start_datetime")
            end_dt = r.get("resolved_datetime")
            open_closed = (r.get("open_closed") or "").strip().lower()

            if not plant_no or not start_dt:
                continue

            start_dt = get_datetime(start_dt)

            if not end_dt and open_closed == "open":
                if window_start <= now_dt < window_end:
                    end_dt = min(now_dt, window_end)
                else:
                    end_dt = window_end
            elif not end_dt:
                continue
            else:
                end_dt = get_datetime(end_dt)

            if end_dt > window_start and start_dt < window_end:
                out[plant_no].append(
                    {
                        "start": max(start_dt, window_start),
                        "end": min(end_dt, window_end),
                        "parent_breakdown": r.get("name"),
                    }
                )

    # 2) Fallback: Breakdown History only for missing assets
    if frappe.db.exists("DocType", "Breakdown History"):
        missing_assets = [a for a in asset_list if not out.get(a)]
        for plant_no in missing_assets:
            fallback_intervals = _get_breakdown_history_intervals(
                site=site,
                plant_no=plant_no,
                window_start=window_start,
                window_end=window_end,
            )
            if fallback_intervals:
                out[plant_no].extend(fallback_intervals)

    return out


def _get_breakdown_history_intervals(site, plant_no, window_start, window_end):
    base_filters = {
        "location": site,
        "asset_name": plant_no,
        "exclude_from_au": 0,
    }

    last_before = frappe.get_all(
        "Breakdown History",
        filters={**base_filters, "update_date_time": ["<", window_start]},
        fields=["update_date_time", "breakdown_status", "parent_breakdown"],
        order_by="update_date_time desc",
        limit=1,
    )

    events = frappe.get_all(
        "Breakdown History",
        filters={
            **base_filters,
            "update_date_time": ["between", [window_start, window_end]],
        },
        fields=["update_date_time", "breakdown_status", "parent_breakdown"],
        order_by="update_date_time asc",
    )

    if not last_before and not events:
        return []

    in_breakdown = False
    current_start = None
    current_parent_breakdown = None
    intervals = []

    if last_before and str(last_before[0].get("breakdown_status") or "") != RESOLVED_STATUS:
        in_breakdown = True
        current_start = window_start
        current_parent_breakdown = last_before[0].get("parent_breakdown")

    for ev in events:
        ev_time = ev.get("update_date_time")
        if not ev_time:
            continue

        ev_status = str(ev.get("breakdown_status") or "")
        ev_parent_breakdown = ev.get("parent_breakdown")

        if ev_status != RESOLVED_STATUS and not in_breakdown:
            in_breakdown = True
            current_start = ev_time
            current_parent_breakdown = ev_parent_breakdown

        elif ev_status == RESOLVED_STATUS and in_breakdown:
            s = max(current_start, window_start)
            e = min(ev_time, window_end)

            if e > s:
                intervals.append(
                    {
                        "start": s,
                        "end": e,
                        "parent_breakdown": current_parent_breakdown,
                    }
                )

            in_breakdown = False
            current_start = None
            current_parent_breakdown = None

    if in_breakdown and current_start:
        now_dt = get_datetime()
        s = max(current_start, window_start)

        if window_start <= now_dt < window_end:
            e = min(now_dt, window_end)
        else:
            e = window_end

        if e > s:
            intervals.append(
                {
                    "start": s,
                    "end": e,
                    "parent_breakdown": current_parent_breakdown,
                }
            )

    return intervals


def _hour_slots(window_start, slot_count):
    for i in range(slot_count):
        hs = window_start + timedelta(hours=i)
        he = hs + timedelta(hours=1)
        yield hs, he


def _overlaps_any(a_start, a_end, intervals):
    for item in intervals:
        if isinstance(item, dict):
            s = item.get("start")
            e = item.get("end")
        else:
            s, e = item

        if e > a_start and s < a_end:
            return True
    return False


def _get_breakdown_doc_for_slot(a_start, a_end, intervals):
    for item in intervals:
        s = item.get("start")
        e = item.get("end")
        parent_breakdown = item.get("parent_breakdown")

        if e > a_start and s < a_end and parent_breakdown:
            return parent_breakdown

    return None