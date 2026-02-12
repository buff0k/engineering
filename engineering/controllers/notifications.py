# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

import frappe
from frappe.email.doctype.email_account.email_account import EmailAccount

# Temporary recipient list (your email)
OEM_BOOKING_RECIPIENTS = ["juan@isambane.co.za"]


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
