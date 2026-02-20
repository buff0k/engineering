# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

import frappe
from frappe.email.doctype.email_account.email_account import EmailAccount

# Always receive notifications (all sites)
ALL_SITES_RECIPIENTS = [
    "msani@isambane.co.za",
]

# Site-specific recipients
SITE_RECIPIENTS = {
    "Koppie": [
        "wimpie@isambane.co.za",
        "dian@isambane.co.za",
    ],
    "Klipfontein": [
        "kobus@isambane.co.za",
        "richard@isambane.co.za",
        "werner.french@isambane.co.za",
    ],
    "Uitgevallen": [
        "charles@excavo.co.za",
        "saul@isambane.co.za",
    ],
    "Gwab": [
        "shawn@isambane.co.za",
        "mandla@isambane.co.za",
    ],
    "Bankfontein": [
        "noel@isambane.co.za",
        "j.semelane@excavo.co.za",
    ],
    "Kriel Rehabilitation": [
        "carel@isambane.co.za",
        "xolani@isambane.co.za",
        "ishmael@isambane.co.za",
    ],
}


def _clean_email(email: str) -> str:
    """Normalize/clean an email address; supports 'Name <email@x.com>'."""
    email = (email or "").strip()
    if "<" in email and ">" in email:
        email = email[email.find("<") + 1 : email.find(">")]
    return email.strip().lower()


def get_recipients_for_site(site: str | None) -> list[str]:
    """
    Returns recipients for a given site + ALL_SITES_RECIPIENTS.
    Deduplicated, lowercased.
    """
    site_key = (site or "").strip()

    recipients = []
    recipients.extend(SITE_RECIPIENTS.get(site_key, []))
    recipients.extend(ALL_SITES_RECIPIENTS)

    seen = set()
    out = []
    for r in recipients:
        e = _clean_email(r)
        if e and e not in seen:
            out.append(e)
            seen.add(e)
    return out


def send_open_breakdowns_digest():
    """Twice daily digest: all Plant Breakdown or Maintenance records still Open."""
    # pick ANY outgoing account (same pattern as OEM Booking)
    email_account = EmailAccount.find_outgoing(match_by_doctype="Plant Breakdown or Maintenance", _raise_error=False)
    if not email_account:
        row = frappe.get_all("Email Account", filters={"enable_outgoing": 1}, pluck="name", limit=1)
        email_account = row and frappe.get_doc("Email Account", row[0]) or None

    if not email_account or not getattr(email_account, "email_id", None):
        frappe.log_error("No outgoing Email Account configured/enabled. Skipping Open Breakdown digest.", "Open Breakdown Digest")
        return

    sender = email_account.email_id

    rows = frappe.get_all(
        "Plant Breakdown or Maintenance",
        filters={"open_closed": "Open"},
        fields=[
            "name",
            "asset_name",
            "breakdown_start_datetime",
            "site",
            "breakdown_maintenance_reason",
        ],
        order_by="breakdown_start_datetime asc",
        limit_page_length=5000,
    )

    # Group rows by site so each site gets only their list
    by_site = {}
    for r in rows:
        site = (r.get("site") or "").strip() or "Unknown"
        by_site.setdefault(site, []).append(r)

    # If there are no open rows, notify ALL_SITES recipients once
    if not rows:
        subject = "Open Plant Breakdowns / Maintenance (0)"
        message = "<br>".join(["Hi,", "", "No open records found."])
        try:
            frappe.sendmail(
                recipients=get_recipients_for_site(None),  # ALL_SITES only
                sender=sender,
                subject=subject,
                message=message,
            )
        except frappe.OutgoingEmailError:
            frappe.log_error(frappe.get_traceback(), "Open Breakdown Digest OutgoingEmailError")
        return

    # Send one email per site
    for site, site_rows in by_site.items():
        recipients = get_recipients_for_site(site)
        if not recipients:
            continue

        subject = f"Open Plant Breakdowns / Maintenance - {site} ({len(site_rows)})"

        lines = [
            "Hi,",
            "",
            f"Site: {site}",
            f"Open Plant Breakdown or Maintenance records: {len(site_rows)}",
            "",
            "<b>Open Records</b>",
            "",
        ]

        for r in site_rows:
            doc_url = frappe.utils.get_url_to_form("Plant Breakdown or Maintenance", r["name"])
            asset_url = frappe.utils.get_url_to_form("Asset", r["asset_name"]) if r.get("asset_name") else ""
            asset_link = f'<a href="{asset_url}">{r["asset_name"]}</a>' if asset_url else (r.get("asset_name") or "")
            dt = r.get("breakdown_start_datetime") or ""
            reason = r.get("breakdown_maintenance_reason") or ""

            lines.append(f'• {asset_link} | {dt} | <a href="{doc_url}">{r["name"]}</a>')
            if reason:
                lines.append(f'&nbsp;&nbsp;&nbsp;&nbsp;Breakdown/Maintenance Reason: {reason}')

        message = "<br>".join(lines)

        try:
            frappe.sendmail(
                recipients=recipients,
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
        "Hi,",
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
            recipients=get_recipients_for_site(getattr(doc, "site", None)),
            sender=sender,
            subject=subject,
            message=message,
        )
    except frappe.OutgoingEmailError:
        # don't block saving if mail isn't configured properly yet
        frappe.log_error(frappe.get_traceback(), "OEM Booking Email OutgoingEmailError")
