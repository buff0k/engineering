# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

import frappe
from frappe.email.doctype.email_account.email_account import EmailAccount

# OEM Booking recipients (unchanged)
OEM_BOOKING_RECIPIENTS = ["juan@isambane.co.za"]

# Plant Breakdown / Maintenance digest recipients per site/location
# NOTE: "msani@isambane.co.za" must always be included for all sites
OPEN_BREAKDOWN_SITE_RECIPIENTS = {
    "Koppie": ["wimpie@isambane.co.za", "dian@isambane.co.za", "msani@isambane.co.za", "juan@isambane.co.za"],
    "Klipfontein": ["kobus@isambane.co.za", "richard@isambane.co.za", "werner.french@isambane.co.za", "msani@isambane.co.za"],
    "Uitgevallen": ["charles@excavo.co.za", "saul@isambane.co.za", "msani@isambane.co.za"],
    "Gwab": ["shawn@isambane.co.za", "matimba@isambane.co.za", "msani@isambane.co.za"],
    "Bankfontein": ["noel@isambane.co.za", "j.semelane@excavo.co.za", "msani@isambane.co.za"],
    "Kriel Rehabilitation": ["carel@isambane.co.za", "xolani@isambane.co.za", "ishmael@isambane.co.za", "msani@isambane.co.za"],
}

# Fallback if a Location name doesn't match any key above
OPEN_BREAKDOWN_DEFAULT_RECIPIENTS = ["msani@isambane.co.za"]


def send_open_breakdowns_digest():
    """Twice daily digest: send separate emails per Site/Location for Open records."""
    # pick ANY outgoing account (same pattern as OEM Booking)
    email_account = EmailAccount.find_outgoing(match_by_doctype="Plant Breakdown or Maintenance", _raise_error=False)
    if not email_account:
        row = frappe.get_all("Email Account", filters={"enable_outgoing": 1}, pluck="name", limit=1)
        email_account = row and frappe.get_doc("Email Account", row[0]) or None

    if not email_account or not getattr(email_account, "email_id", None):
        frappe.log_error(
            "No outgoing Email Account configured/enabled. Skipping Open Breakdown digest.",
            "Open Breakdown Digest",
        )
        return

    sender = email_account.email_id

    # Pull ALL open records, including the Site field ("location" is labelled "Site" in the DocType)
    rows = frappe.get_all(
        "Plant Breakdown or Maintenance",
        filters={"open_closed": "Open"},
        fields=["name", "asset_name", "breakdown_start_datetime", "location"],
        order_by="location asc, breakdown_start_datetime asc",
        limit_page_length=5000,
    )

    def _recipients_for_location(location_name: str):
        location_name = (location_name or "").strip()
        return OPEN_BREAKDOWN_SITE_RECIPIENTS.get(location_name) or OPEN_BREAKDOWN_DEFAULT_RECIPIENTS

    # Group by location/site
    by_location = {}
    for r in rows:
        loc = (r.get("location") or "").strip() or "Unknown"
        by_location.setdefault(loc, []).append(r)

    # If nothing open, send only to default recipients (so at least someone knows)
    if not rows:
        subject = "Open Plant Breakdowns / Maintenance (0)"
        message = "<br>".join(
            [
                "Hi Team",
                "",
                "Open Plant Breakdown or Maintenance records: 0",
                "",
                "No open records found.",
            ]
        )
        try:
            frappe.sendmail(
                recipients=OPEN_BREAKDOWN_DEFAULT_RECIPIENTS,
                sender=sender,
                subject=subject,
                message=message,
            )
        except frappe.OutgoingEmailError:
            frappe.log_error(frappe.get_traceback(), "Open Breakdown Digest OutgoingEmailError")
        return

    # Send one email per location
    for loc, loc_rows in by_location.items():
        recipients = _recipients_for_location(loc)

        subject = f"Open Plant Breakdowns / Maintenance - {loc} ({len(loc_rows)})"

        lines = [
            "Hi Team",
            "",
            f"Site: {loc}",
            f"Open Plant Breakdown or Maintenance records: {len(loc_rows)}",
            "",
        ]

        lines += ["<b>Open Records</b>", ""]
        for r in loc_rows:
            doc_url = frappe.utils.get_url_to_form("Plant Breakdown or Maintenance", r["name"])
            asset_url = frappe.utils.get_url_to_form("Asset", r["asset_name"]) if r.get("asset_name") else ""
            asset_link = f'<a href="{asset_url}">{r["asset_name"]}</a>' if asset_url else (r.get("asset_name") or "")
            dt = r.get("breakdown_start_datetime") or ""
            lines.append(f'• {asset_link} | {dt} | <a href="{doc_url}">{r["name"]}</a>')

        message = "<br>".join(lines)

        try:
            frappe.sendmail(
                recipients=recipients,
                sender=sender,
                subject=subject,
                message=message,
            )
        except frappe.OutgoingEmailError:
            frappe.log_error(frappe.get_traceback(), f"Open Breakdown Digest OutgoingEmailError ({loc})")
        lines += ["No open records found."]
    else:
        lines += ["<b>Open Records</b>", ""]
        for r in rows:
            doc_url = frappe.utils.get_url_to_form("Plant Breakdown or Maintenance", r["name"])
            asset_url = frappe.utils.get_url_to_form("Asset", r["asset_name"]) if r.get("asset_name") else ""
            asset_link = f'<a href="{asset_url}">{r["asset_name"]}</a>' if asset_url else (r.get("asset_name") or "")
            dt = r.get("breakdown_start_datetime") or ""
            lines.append(f'• {asset_link} | {dt} | <a href="{doc_url}">{r["name"]}</a>')

    message = "<br>".join(lines)

    try:
        frappe.sendmail(
            recipients=OEM_BOOKING_RECIPIENTS,
            sender=sender,
            subject=subject,
            message=message,
        )
    except frappe.OutgoingEmailError:
        frappe.log_error(frappe.get_traceback(), "Open Breakdown Digest OutgoingEmailError")


def oem_booking_on_update(doc, method=None):
    # Fires on every SAVE (create + edit)
    _send_oem_booking_email(doc, action="saved")


def _send_oem_booking_email(doc, action: str):
    # pick ANY outgoing account (even if default is not set)
    email_account = EmailAccount.find_outgoing(match_by_doctype=doc.doctype, _raise_error=False)
    if not email_account:
        row = frappe.get_all("Email Account", filters={"enable_outgoing": 1}, pluck="name", limit=1)
        email_account = row and frappe.get_doc("Email Account", row[0]) or None

    if not email_account or not getattr(email_account, "email_id", None):
        frappe.log_error("No outgoing Email Account configured/enabled. Skipping OEM Booking email.", "OEM Booking Email")
        return

    sender = email_account.email_id
    url = frappe.utils.get_url(doc.get_url())

    subject = (
        f"OEM Booking {action}: {doc.name} | {getattr(doc, 'asset', '')} | "
        f"{getattr(doc, 'booking_date', '')} {getattr(doc, 'time', '')}"
    )

    lines = [
        "Hi Juan",
        "",
        f"An OEM Booking has been {action}.",
        "",
        f"• Name: {doc.name}",
        f"• Site: {getattr(doc, 'site', '')}",
        f"• Fleet Number (Asset): {getattr(doc, 'asset', '')}",
        f"• Model: {getattr(doc, 'model', '')}",
        f"• Asset Category: {getattr(doc, 'asset_category', '')}",
        f"• Booking Date: {getattr(doc, 'booking_date', '')}",
        f"• Time: {getattr(doc, 'time', '')}",
        f"• Order Number: {getattr(doc, 'order_number', '')}",
        f"• Current Hours: {getattr(doc, 'current_hours', '')}",
        f"• Service Interval: {getattr(doc, 'service_interval', '')}",
        "",
        "Description of Service:",
        f"{getattr(doc, 'description_of_service', '')}",
        "",
        "Description of Work Done:",
        f"{getattr(doc, 'description_of_work_done', '')}",
        "",
        f'<a href="{url}">Click here to view</a>',
    ]

    message = "<br>".join(lines)

    try:
        frappe.sendmail(
            recipients=OEM_BOOKING_RECIPIENTS,
            sender=sender,
            subject=subject,
            message=message,
        )
    except frappe.OutgoingEmailError:
        # don't block saving if mail isn't configured properly yet
        frappe.log_error(frappe.get_traceback(), "OEM Booking Email OutgoingEmailError")
