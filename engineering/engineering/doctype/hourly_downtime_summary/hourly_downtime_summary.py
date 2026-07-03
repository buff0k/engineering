# Copyright (c) 2026, Isambane Mining (Pty) Ltd
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from frappe.utils import now_datetime
from datetime import timedelta


SITE_CHANNELS = {
    "Koppie": "Isambane Mining-kop-hourly-downtime-reporting",
}


class HourlyDowntimeSummary(Document):
    def validate(self):
        if self.summary_message:
            self.summary_message = self.summary_message.strip()


def get_completed_hour_slot():
    now = now_datetime()

    current_hour_start = now.replace(minute=0, second=0, microsecond=0)
    previous_hour_start = current_hour_start - timedelta(hours=1)

    report_date = previous_hour_start.date()
    start_text = previous_hour_start.strftime("%H:00")
    end_text = current_hour_start.strftime("%H:00")

    return report_date, f"{start_text}-{end_text}"


def create_koppie_hourly_downtime_summary():
    return create_hourly_downtime_summary("Koppie")


def create_hourly_downtime_summary(site):
    report_date, hour_slot = get_completed_hour_slot()
    channel_id = SITE_CHANNELS.get(site)

    if not channel_id:
        frappe.throw(f"No Raven channel configured for site: {site}")

    filters = {
        "report_date": str(report_date),
        "hour_slot": hour_slot,
        "site": site,
    }

    from engineering.engineering.report.hourly_downtime_report.hourly_downtime_report import execute

    columns, data = execute(filters)

    summary_message = build_summary_message(
        site=site,
        report_date=report_date,
        hour_slot=hour_slot,
        data=data,
    )

    doc = frappe.get_doc({
        "doctype": "Hourly Downtime Summary",
        "site": site,
        "report_date": report_date,
        "hour_slot": hour_slot,
        "channel_id": channel_id,
        "summary_message": summary_message,
        "report_data_json": json.dumps(data, default=str),
        "sent_to_raven": 0,
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return doc.name


def build_summary_message(site, report_date, hour_slot, data):
    open_rows = [row for row in data if row.get("status_key") == "open"]

    total = len(data)
    open_count = len(open_rows)
    available_count = total - open_count

    lines = []

    lines.append(f"{site.upper()} HOURLY BREAKDOWN REPORT")
    lines.append(str(report_date))
    lines.append(hour_slot.replace("-", " TO "))
    lines.append("")

    if not open_rows:
        lines.append("No open breakdowns for this hour.")
        lines.append("")
        lines.append(f"Open: {open_count}")
        lines.append(f"Available: {available_count}")
        lines.append(f"Total: {total}")
        return "\n".join(lines)

    grouped = {}

    for row in open_rows:
        category = row.get("category_group") or row.get("asset_category") or "OTHER"

        if category not in grouped:
            grouped[category] = []

        grouped[category].append(row)

    category_order = [
        "ADT",
        "Excavator",
        "Dozer",
        "Water Bowser",
        "Diesel Bowser",
        "Service Truck",
        "FEL",
        "Grader",
    ]

    for category in category_order:
        rows = grouped.get(category)

        if not rows:
            continue

        lines.append(category.upper())

        for row in rows:
            plant_no = row.get("plant_no") or "-"
            reason = row.get("reason") or "-"
            lines.append(f"{plant_no} - {str(reason).upper()}")

        lines.append("")

    lines.append(f"Open: {open_count}")
    lines.append(f"Available: {available_count}")
    lines.append(f"Total: {total}")

    return "\n".join(lines)