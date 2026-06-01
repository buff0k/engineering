import frappe
from frappe.utils import getdate, get_datetime, now_datetime, time_diff_in_hours
from datetime import datetime, time, timedelta


def calculate_hours(breakdown_start, resolved_datetime, window_start, window_end):
    if not breakdown_start:
        return 0

    actual_start = get_datetime(breakdown_start)
    actual_end = get_datetime(resolved_datetime) if resolved_datetime else now_datetime()

    downtime_start = max(actual_start, window_start)
    downtime_end = min(actual_end, window_end)

    if downtime_end <= downtime_start:
        return 0

    return round(float(time_diff_in_hours(downtime_end, downtime_start)), 2)


def execute(start_date=None, end_date=None, site=None, asset_category=None):
    start_date = getdate(start_date) if start_date else getdate(now_datetime())
    end_date = getdate(end_date) if end_date else start_date

    report_start_datetime = datetime.combine(start_date, time.min)
    report_end_datetime = datetime.combine(end_date + timedelta(days=1), time.min)

    conditions = [
        "pbm.breakdown_start_datetime is not null",
        "pbm.breakdown_start_datetime < %(report_end_datetime)s",
        "(pbm.resolved_datetime is null or pbm.resolved_datetime > %(report_start_datetime)s)",
        """(
            lower(coalesce(pbm.breakdown_reason, '')) like %(start_up_pattern)s
            or lower(coalesce(pbm.breakdown_reason, '')) like %(startup_pattern)s
            or lower(coalesce(pbm.breakdown_reason, '')) like %(fatique_pattern)s
            or lower(coalesce(pbm.breakdown_reason, '')) like %(fatigue_pattern)s
        )"""
    ]

    values = {
        "report_start_datetime": report_start_datetime,
        "report_end_datetime": report_end_datetime,
        "start_up_pattern": "%start up%",
        "startup_pattern": "%startup%",
        "fatique_pattern": "%fatique%",
        "fatigue_pattern": "%fatigue%",
    }

    if site:
        conditions.append("pbm.location = %(site)s")
        values["site"] = site

    if asset_category:
        conditions.append("upper(pbm.asset_category) = %(asset_category)s")
        values["asset_category"] = asset_category.upper()

    rows = frappe.db.sql(
        f"""
        select
            pbm.name,
            pbm.location as site,
            pbm.asset_name as plant_no,
            pbm.asset_category,
            pbm.breakdown_reason,
            pbm.breakdown_start_datetime,
            pbm.resolved_datetime
        from `tabPlant Breakdown or Maintenance` pbm
        where {" and ".join(conditions)}
        order by pbm.breakdown_start_datetime asc
        """,
        values,
        as_dict=True,
    )

    total_start_up = 0
    total_fatique = 0

    print("")
    print("START UP / FATIQUE TIME CHECK")
    print("FROM:", start_date, "TO:", end_date)
    print("")

    for row in rows:
        current_day = start_date

        while current_day <= end_date:
            window_start = datetime.combine(current_day, time.min)
            window_end = window_start + timedelta(days=1)

            hours = calculate_hours(
                row.breakdown_start_datetime,
                row.resolved_datetime,
                window_start,
                window_end,
            )

            if hours > 0:
                reason = (row.breakdown_reason or "").lower()

                if "start up" in reason or "startup" in reason:
                    category = "START UP"
                    total_start_up += hours
                else:
                    category = "FATIQUE/FATIGUE"
                    total_fatique += hours

                print(
                    str(current_day),
                    "|",
                    row.site,
                    "|",
                    row.plant_no,
                    "|",
                    row.asset_category,
                    "|",
                    category,
                    "|",
                    str(hours),
                    "hrs",
                    "|",
                    row.breakdown_reason,
                    "|",
                    row.breakdown_start_datetime,
                    "to",
                    row.resolved_datetime or "OPEN",
                )

            current_day = current_day + timedelta(days=1)

    print("")
    print("START UP HOURS:", round(total_start_up, 2))
    print("FATIQUE/FATIGUE HOURS:", round(total_fatique, 2))
    print("TOTAL EXCLUDED HOURS:", round(total_start_up + total_fatique, 2))
    print("")

    return {
        "start_up_hours": round(total_start_up, 2),
        "fatique_fatigue_hours": round(total_fatique, 2),
        "total_excluded_hours": round(total_start_up + total_fatique, 2),
    }
