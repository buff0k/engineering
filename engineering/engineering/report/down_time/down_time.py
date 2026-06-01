# Copyright (c) 2026, Isambane Mining (Pty) Ltd
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, now_datetime, time_diff_in_hours
from datetime import timedelta


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 110},
        {"label": _("Site"), "fieldname": "site", "fieldtype": "Data", "width": 150},
        {"label": _("Plant No."), "fieldname": "plant_no", "fieldtype": "Data", "width": 130},
        {"label": _("Breakdown/Maintenance Reason"), "fieldname": "breakdown_reason", "fieldtype": "Small Text", "width": 260},
        {"label": _("Resolution Summary"), "fieldname": "resolution_summary", "fieldtype": "Small Text", "width": 210},
        {"label": _("Breakdown/Maintenance Start Time"), "fieldname": "breakdown_start_datetime", "fieldtype": "Datetime", "width": 230},
        {"label": _("Datetime back in production"), "fieldname": "resolved_datetime", "fieldtype": "Datetime", "width": 210},
        {"label": _("Breakdown/Maintenance Hours"), "fieldname": "breakdown_hours", "fieldtype": "Float", "precision": 2, "width": 210},
        {"label": _("Open/Closed"), "fieldname": "open_closed", "fieldtype": "Data", "width": 120},
    ]


def is_filter_set(value):
    value = str(value or "").strip()

    if not value:
        return False

    if value.lower() in ("all", "all sites", "undefined", "none", "null", "site"):
        return False

    return True


def normalise_shift(shift):
    shift = (shift or "").strip().lower()

    if shift in ("day", "day shift"):
        return "Day"

    if shift in ("night", "night shift"):
        return "Night"

    return ""


def get_report_windows(report_date, shift=None):
    shift = normalise_shift(shift)

    day_start = get_datetime(str(report_date) + " 06:00:00")
    day_end = get_datetime(str(report_date) + " 18:00:00")

    night_start = get_datetime(str(report_date) + " 18:00:00")
    night_end = get_datetime(str(report_date + timedelta(days=1)) + " 06:00:00")

    if shift == "Day":
        return [("Day", day_start, day_end)]

    if shift == "Night":
        return [("Night", night_start, night_end)]

    return [
        ("Day", day_start, day_end),
        ("Night", night_start, night_end),
    ]


def overlap_hours(a_start, a_end, b_start, b_end):
    start = max(a_start, b_start)
    end = min(a_end, b_end)

    if end <= start:
        return 0.0

    return float(time_diff_in_hours(end, start))


def exclusion_windows(shift, window_start, window_end):
    shift = normalise_shift(shift)
    windows = []

    shift_date = getdate(window_start)
    next_date = getdate(window_end)

    if shift == "Day":
        windows.append((
            get_datetime(str(shift_date) + " 06:00:00"),
            get_datetime(str(shift_date) + " 08:00:00"),
        ))
        windows.append((
            get_datetime(str(shift_date) + " 13:00:00"),
            get_datetime(str(shift_date) + " 14:00:00"),
        ))

    if shift == "Night":
        windows.append((
            get_datetime(str(shift_date) + " 18:00:00"),
            get_datetime(str(shift_date) + " 20:00:00"),
        ))
        windows.append((
            get_datetime(str(next_date) + " 01:00:00"),
            get_datetime(str(next_date) + " 02:00:00"),
        ))

    filtered = []

    for start, end in windows:
        if end <= window_start or start >= window_end:
            continue

        filtered.append((max(start, window_start), min(end, window_end)))

    return filtered


def get_breakdown_history_intervals(site, plant_no, window_start, window_end):
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

    events_in_window = frappe.get_all(
        "Breakdown History",
        filters={**base_filters, "update_date_time": ["between", [window_start, window_end]]},
        fields=["update_date_time", "breakdown_status"],
        order_by="update_date_time asc",
    )

    intervals = []
    in_breakdown = False
    current_start = None

    if last_before and str(last_before[0].get("breakdown_status")) != "3":
        in_breakdown = True
        current_start = window_start

    for event in events_in_window:
        event_time = get_datetime(event.get("update_date_time"))
        event_status = str(event.get("breakdown_status") or "")

        if event_status != "3" and not in_breakdown:
            in_breakdown = True
            current_start = event_time

        elif event_status == "3" and in_breakdown:
            clip_start = max(current_start, window_start)
            clip_end = min(event_time, window_end)

            if clip_end > clip_start:
                intervals.append((clip_start, clip_end))

            in_breakdown = False
            current_start = None

    if in_breakdown and current_start:
        clip_start = max(current_start, window_start)
        clip_end = window_end

        if clip_end > clip_start:
            intervals.append((clip_start, clip_end))

    return intervals


def calculate_au_engine_breakdown_hours(site, plant_no, shift, window_start, window_end):
    intervals = get_breakdown_history_intervals(site, plant_no, window_start, window_end)
    excluded = exclusion_windows(shift, window_start, window_end)

    effective_hours = 0.0

    for interval_start, interval_end in intervals:
        interval_hours = float(time_diff_in_hours(interval_end, interval_start))
        excluded_hours = 0.0

        for excluded_start, excluded_end in excluded:
            excluded_hours += overlap_hours(interval_start, interval_end, excluded_start, excluded_end)

        excluded_hours = min(excluded_hours, interval_hours)
        effective_hours += max(interval_hours - excluded_hours, 0.0)

    return round(max(effective_hours, 0), 2)


def get_latest_pbm_details(site, plant_no, window_start, window_end):
    rows = frappe.db.sql(
        """
        select
            pbm.name,
            pbm.location as site,
            pbm.asset_name as plant_no,
            pbm.asset_category as asset_category,
            pbm.breakdown_reason as breakdown_reason,
            pbm.resolution_summary as resolution_summary,
            pbm.breakdown_start_datetime as breakdown_start_datetime,
            pbm.resolved_datetime as resolved_datetime,
            pbm.open_closed as open_closed,
            pbm.modified as modified
        from `tabPlant Breakdown or Maintenance` pbm
        where pbm.location = %(site)s
          and pbm.asset_name = %(plant_no)s
          and pbm.breakdown_start_datetime is not null
          and pbm.breakdown_start_datetime < %(window_end)s
          and (
                pbm.resolved_datetime is null
                or pbm.resolved_datetime > %(window_start)s
          )
        order by pbm.breakdown_start_datetime desc, pbm.modified desc
        limit 1
        """,
        {
            "site": site,
            "plant_no": plant_no,
            "window_start": window_start,
            "window_end": window_end,
        },
        as_dict=True,
    )

    if rows:
        return rows[0]

    return frappe._dict({
        "site": site,
        "plant_no": plant_no,
        "asset_category": None,
        "breakdown_reason": "",
        "resolution_summary": "",
        "breakdown_start_datetime": None,
        "resolved_datetime": None,
        "open_closed": "Open",
    })


def get_open_closed(site, plant_no, window_end):
    last_event = frappe.get_all(
        "Breakdown History",
        filters={
            "location": site,
            "asset_name": plant_no,
            "exclude_from_au": 0,
            "update_date_time": ["<=", window_end],
        },
        fields=["breakdown_status"],
        order_by="update_date_time desc",
        limit=1,
    )

    if last_event and str(last_event[0].get("breakdown_status")) == "3":
        return "Closed"

    return "Open"


def get_assets_from_breakdown_history(report_start_datetime, report_end_datetime, filters):
    conditions = [
        "bh.update_date_time is not null",
        "bh.update_date_time < %(report_end_datetime)s",
        "bh.exclude_from_au = 0",
        "ifnull(bh.location, '') != ''",
        "ifnull(bh.asset_name, '') != ''",
    ]

    values = {
        "report_start_datetime": report_start_datetime,
        "report_end_datetime": report_end_datetime,
    }

    # IMPORTANT:
    # If site is blank, do NOT add a site condition.
    # This allows all sites to populate.
    if is_filter_set(filters.get("site")):
        conditions.append("bh.location = %(site)s")
        values["site"] = filters.get("site")

    if is_filter_set(filters.get("asset_category")):
        conditions.append("""
            exists (
                select 1
                from `tabPlant Breakdown or Maintenance` pbm
                where pbm.location = bh.location
                  and pbm.asset_name = bh.asset_name
                  and upper(pbm.asset_category) = %(asset_category)s
            )
        """)
        values["asset_category"] = filters.get("asset_category").upper()

    return frappe.db.sql(
        f"""
        select distinct
            bh.location as site,
            bh.asset_name as plant_no
        from `tabBreakdown History` bh
        where {" and ".join(conditions)}
        order by bh.location asc, bh.asset_name asc
        """,
        values,
        as_dict=True,
    )


def get_data(filters):
    start_date = getdate(filters.get("start_date")) if filters.get("start_date") else getdate(now_datetime())
    end_date = getdate(filters.get("end_date")) if filters.get("end_date") else start_date

    report_start_datetime = get_datetime(str(start_date) + " 06:00:00")
    report_end_datetime = get_datetime(str(end_date + timedelta(days=1)) + " 06:00:00")

    assets = get_assets_from_breakdown_history(report_start_datetime, report_end_datetime, filters)

    data = []

    for asset in assets:
        current_day = start_date

        while current_day <= end_date:
            total_day_hours = 0.0
            first_window_start = None
            last_window_end = None

            for shift, window_start, window_end in get_report_windows(current_day, filters.get("shift")):
                if first_window_start is None:
                    first_window_start = window_start

                last_window_end = window_end

                total_day_hours += calculate_au_engine_breakdown_hours(
                    asset.site,
                    asset.plant_no,
                    shift,
                    window_start,
                    window_end,
                )

            total_day_hours = round(min(total_day_hours, 24), 2)

            if total_day_hours > 0:
                details = get_latest_pbm_details(
                    asset.site,
                    asset.plant_no,
                    first_window_start,
                    last_window_end,
                )

                data.append({
                    "date": current_day,
                    "site": asset.site,
                    "plant_no": asset.plant_no,
                    "breakdown_reason": details.breakdown_reason,
                    "resolution_summary": details.resolution_summary,
                    "breakdown_start_datetime": details.breakdown_start_datetime,
                    "resolved_datetime": details.resolved_datetime,
                    "breakdown_hours": total_day_hours,
                    "open_closed": get_open_closed(asset.site, asset.plant_no, last_window_end),
                })

            current_day = current_day + timedelta(days=1)

    data.sort(key=lambda d: (d.get("date"), d.get("site") or "", d.get("plant_no") or ""), reverse=True)

    return data
