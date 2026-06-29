# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

import frappe
from frappe.email.doctype.email_account.email_account import EmailAccount
from frappe.utils import now, now_datetime, cint


# ---------------------------------------------------------------------
# OEM Booking recipients unchanged
# ---------------------------------------------------------------------
OEM_BOOKING_RECIPIENTS = ["juan@isambane.co.za", "renier@isambane.co.za"]


# ---------------------------------------------------------------------
# Plant Breakdown / Maintenance digest recipients per site/location
# NOTE: "msani@isambane.co.za" must always be included for all sites
# ---------------------------------------------------------------------
OPEN_BREAKDOWN_SITE_RECIPIENTS = {
    "Koppie": [
        "wimpie@isambane.co.za",
        "dian@isambane.co.za",
        "msani@isambane.co.za",
        "juan@isambane.co.za",
        "koppie.control@isambane.co.za",
    ],
    "Klipfontein": [
        "kobus@isambane.co.za",
        "richard@isambane.co.za",
        "werner.french@isambane.co.za",
        "msani@isambane.co.za",
    ],
    "Uitgevallen": [
        "charles@excavo.co.za",
        "saul@isambane.co.za",
        "juan@isambane.co.za",
        "msani@isambane.co.za",
        "uitcontrol@isambane.co.za",
    ],
    "Gwab": [
        "bongani@isambane.co.za",
        "matimba@isambane.co.za",
        "msani@isambane.co.za",
    ],
    "Bankfontein": [
        "noel@isambane.co.za",
        "j.semelane@excavo.co.za",
        "msani@isambane.co.za",
        "bankfontein.control@isambane.co.za",
        "juan@isambane.co.za",
    ],
    "Kriel Rehabilitation": [
        "carel@isambane.co.za",
        "xolani@isambane.co.za",
        "ishmael@isambane.co.za",
        "msani@isambane.co.za",
    ],
}

# Fallback if a Location name does not match any key above
OPEN_BREAKDOWN_DEFAULT_RECIPIENTS = ["msani@isambane.co.za"]


# ---------------------------------------------------------------------
# WearCheck severity map
# Recipients are now configured in API Wearcheck Settings, not hardcoded.
# ---------------------------------------------------------------------
WEARCHECK_SEVERITY_MAP = {
    3: "Urgent",
    4: "Critical",
}


# ---------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------
def _norm(value):
    return (value or "").strip()


def _dedupe_keep_order(values):
    seen = set()
    output = []

    for value in values:
        value = _norm(value)

        if not value:
            continue

        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        output.append(value)

    return output


def _get_outgoing_email_account(match_by_doctype=None):
    email_account = EmailAccount.find_outgoing(
        match_by_doctype=match_by_doctype,
        _raise_error=False,
    )

    if not email_account:
        row = frappe.get_all(
            "Email Account",
            filters={"enable_outgoing": 1},
            pluck="name",
            limit=1,
        )
        email_account = row and frappe.get_doc("Email Account", row[0]) or None

    return email_account


# ---------------------------------------------------------------------
# Plant Breakdown digest
# ---------------------------------------------------------------------
def send_open_breakdowns_digest_hourly_gate():
    """Run digest only at 06:00 server time."""
    dt = now_datetime()  # server TZ

    if not (dt.minute == 0 and dt.hour == 6):
        return

    # Once-per-slot guard prevents duplicates if scheduler retries
    key = f"open_breakdowns_digest_ran::{dt.date()}::{dt.hour:02d}"

    if frappe.cache().get_value(key):
        return

    frappe.cache().set_value(key, 1, expires_in_sec=60 * 60 * 3)

    return send_open_breakdowns_digest(dry_run=False)


def send_open_breakdowns_digest(dry_run: bool = False):
    """
    Twice daily digest: send separate emails per Site/Location for Open records.
    dry_run=True: returns payloads instead of sending.
    """

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

    by_location = {}

    for r in rows:
        loc = (r.get("location") or "").strip() or "Unknown"
        by_location.setdefault(loc, []).append(r)

    payloads = {}

    if not rows:
        subject = "Open Plant Breakdowns / Maintenance (0)"
        lines = [
            "Hi Team",
            "",
            "Site: All",
            "Open Plant Breakdown or Maintenance records: 0",
            "",
            "No open records found.",
        ]
        message = "<br>".join(lines)

        payloads["__default__"] = {
            "recipients": OPEN_BREAKDOWN_DEFAULT_RECIPIENTS,
            "subject": subject,
            "message": message,
        }

        if dry_run:
            return payloads

        email_account = _get_outgoing_email_account(
            match_by_doctype="Plant Breakdown or Maintenance"
        )

        if not email_account or not getattr(email_account, "email_id", None):
            frappe.log_error(
                "No outgoing Email Account configured/enabled. Skipping Open Breakdown digest.",
                "Open Breakdown Digest",
            )
            return payloads

        try:
            frappe.sendmail(
                recipients=OPEN_BREAKDOWN_DEFAULT_RECIPIENTS,
                sender=email_account.email_id,
                subject=subject,
                message=message,
            )
        except frappe.OutgoingEmailError:
            frappe.log_error(
                frappe.get_traceback(),
                "Open Breakdown Digest OutgoingEmailError",
            )

        return payloads

    for loc, loc_rows in by_location.items():
        recipients = _recipients_for_location(loc)
        subject = f"Open Plant Breakdowns / Maintenance — {loc} ({len(loc_rows)})"

        lines = [
            "Hi Team",
            "",
            f"Site: {loc}",
            f"Open Plant Breakdown or Maintenance records: {len(loc_rows)}",
            "",
            "<b>Open Records</b>",
            "",
        ]

        for r in loc_rows:
            doc_url = frappe.utils.get_url_to_form(
                "Plant Breakdown or Maintenance",
                r["name"],
            )
            asset_url = (
                frappe.utils.get_url_to_form("Asset", r["asset_name"])
                if r.get("asset_name")
                else ""
            )
            asset_link = (
                f'<a href="{asset_url}">{r["asset_name"]}</a>'
                if asset_url
                else (r.get("asset_name") or "")
            )
            dt = r.get("breakdown_start_datetime") or ""
            lines.append(
                f'• {asset_link} | {dt} | <a href="{doc_url}">{r["name"]}</a>'
            )

        message = "<br>".join(lines)

        payloads[loc] = {
            "recipients": recipients,
            "subject": subject,
            "message": message,
        }

    if dry_run:
        return payloads

    email_account = _get_outgoing_email_account(
        match_by_doctype="Plant Breakdown or Maintenance"
    )

    if not email_account or not getattr(email_account, "email_id", None):
        frappe.log_error(
            "No outgoing Email Account configured/enabled. Skipping Open Breakdown digest.",
            "Open Breakdown Digest",
        )
        return payloads

    sender = email_account.email_id

    for loc, p in payloads.items():
        try:
            frappe.sendmail(
                recipients=p["recipients"],
                sender=sender,
                subject=p["subject"],
                message=p["message"],
            )
        except frappe.OutgoingEmailError:
            frappe.log_error(
                frappe.get_traceback(),
                f"Open Breakdown Digest OutgoingEmailError ({loc})",
            )

    return payloads


# ---------------------------------------------------------------------
# OEM Booking notification
# ---------------------------------------------------------------------
def oem_booking_on_update(doc, method=None):
    # Fires on every SAVE, create and edit
    _send_oem_booking_email(doc, action="saved")


def _send_oem_booking_email(doc, action: str):
    email_account = _get_outgoing_email_account(match_by_doctype=doc.doctype)

    if not email_account or not getattr(email_account, "email_id", None):
        frappe.log_error(
            "No outgoing Email Account configured/enabled. Skipping OEM Booking email.",
            "OEM Booking Email",
        )
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
            recipients=OEM_BOOKING_RECIPIENTS,
            sender=sender,
            subject=subject,
            message=message,
        )
    except frappe.OutgoingEmailError:
        # Do not block saving if mail is not configured properly yet
        frappe.log_error(
            frappe.get_traceback(),
            "OEM Booking Email OutgoingEmailError",
        )


# ---------------------------------------------------------------------
# WearCheck notifications
# ---------------------------------------------------------------------
def wearcheck_results_after_insert(doc, method=None):
    _send_wearcheck_alert_email(doc)


def wearcheck_results_on_update(doc, method=None):
    """
    Do not only check has_value_changed("status").

    A failed WearCheck import may later be retried after mappings are fixed.
    In that case status may not change, but location/asset/company may now
    be resolved and the alert should be eligible to send.
    """
    _send_wearcheck_alert_email(doc)


def _get_wearcheck_settings():
    return frappe.get_single("API Wearcheck Settings")


def _get_wearcheck_user_email(user):
    user = _norm(user)

    if not user:
        return None

    email = frappe.db.get_value("User", user, "email")

    return _norm(email or user)


def _get_wearcheck_recipient_users_for_location(location):
    """
    Reads configured WearCheck recipients from API Wearcheck Settings.

    Global recipients:
        API Wearcheck Settings.global_recipients

    Location recipients:
        API Wearcheck Settings.recipients_per_site

    The location should normally be WearCheck Results.location, which is the
    mapped Frappe Location, not the raw JSON site value.
    """
    settings = _get_wearcheck_settings()
    location = _norm(location)

    users = []

    for row in settings.get("global_recipients") or []:
        user = _norm(getattr(row, "user", None))

        if user:
            users.append(user)

    for row in settings.get("recipients_per_site") or []:
        row_location = _norm(getattr(row, "location", None))

        if row_location and location and row_location == location:
            user = _norm(getattr(row, "user", None))

            if user:
                users.append(user)

    return _dedupe_keep_order(users)


def _get_wearcheck_recipient_emails_for_users(users):
    emails = []

    for user in users:
        email = _get_wearcheck_user_email(user)

        if email:
            emails.append(email)

    return _dedupe_keep_order(emails)


def _wearcheck_alert_already_sent(doc):
    meta = frappe.get_meta(doc.doctype)

    if not meta.has_field("critical_notification_sent"):
        return False

    return bool(getattr(doc, "critical_notification_sent", 0))


def _set_wearcheck_notification_audit(doc, users):
    """
    Stores the users who were notified into:

        WearCheck Results.critical_notification_recipients

    This field is a Table using child table Wearcheck Global Users.
    That child table has a single required field:

        user
    """
    meta = frappe.get_meta(doc.doctype)

    if meta.has_field("critical_notification_sent"):
        doc.critical_notification_sent = 1

    if meta.has_field("critical_notification_sent_on"):
        doc.critical_notification_sent_on = now()

    if meta.has_field("critical_notification_recipients"):
        doc.set("critical_notification_recipients", [])

        for user in users:
            doc.append(
                "critical_notification_recipients",
                {
                    "user": user,
                },
            )

    doc.save(ignore_permissions=True)


def _send_wearcheck_alert_email(doc):
    if getattr(frappe.flags, "in_wearcheck_alert_notification", False):
        return

    status = cint(getattr(doc, "status", None) or 0)

    if status not in WEARCHECK_SEVERITY_MAP:
        return

    # Do not send alerts for unresolved failed imports.
    # The scheduled failed retry will re-run this after mappings are fixed.
    if cint(getattr(doc, "import_failed", 0)):
        return

    if _wearcheck_alert_already_sent(doc):
        return

    severity = WEARCHECK_SEVERITY_MAP.get(status)

    location = (
        _norm(getattr(doc, "location", None))
        or _norm(getattr(doc, "site", None))
        or "Unknown"
    )

    users = _get_wearcheck_recipient_users_for_location(location)
    recipients = _get_wearcheck_recipient_emails_for_users(users)

    if not recipients:
        frappe.log_error(
            (
                f"No WearCheck alert recipients configured for result {doc.name}. "
                f"Location: {location}. Status: {status} ({severity})."
            ),
            "WearCheck Alert Email",
        )
        return

    email_account = _get_outgoing_email_account(match_by_doctype=doc.doctype)

    if not email_account or not getattr(email_account, "email_id", None):
        frappe.log_error(
            "No outgoing Email Account configured/enabled. Skipping WearCheck alert email.",
            "WearCheck Alert Email",
        )
        return

    sender = email_account.email_id
    url = frappe.utils.get_url(doc.get_url())

    subject = (
        f"{severity} Oil Sample Alert for "
        f"{getattr(doc, 'machine', '') or getattr(doc, 'asset', '') or doc.name} "
        f"({location})"
    )

    lines = [
        "Dear Team,",
        "",
        f"<b>{severity} Oil Sample Alert</b>",
        "",
        "A WearCheck oil sample result has been received for the machine below and requires attention.",
        "",
        f"<b>Site:</b> {frappe.utils.escape_html(location)}",
        f"<b>Asset:</b> {frappe.utils.escape_html(getattr(doc, 'asset', '') or '-')}",
        f"<b>Machine:</b> {frappe.utils.escape_html(getattr(doc, 'machine', '') or '-')}",
        f"<b>Sample No:</b> {frappe.utils.escape_html(str(getattr(doc, 'sampno', '') or '-'))}",
        f"<b>Component:</b> {frappe.utils.escape_html(getattr(doc, 'component', '') or '-')}",
        f"<b>Severity:</b> {frappe.utils.escape_html(severity)}",
        f"<b>Sample Date:</b> {frappe.utils.escape_html(str(getattr(doc, 'sampledate', '') or '-'))}",
        f"<b>Registered Date:</b> {frappe.utils.escape_html(str(getattr(doc, 'registerdate', '') or '-'))}",
        "",
        "Please monitor this machine closely and take the necessary action as soon as possible to prevent possible failure or further damage.",
        "",
        "<b>Comments:</b>",
        f"{frappe.utils.escape_html(getattr(doc, 'commentstext', '') or '-')}",
        "",
        "<b>Recommended Action:</b>",
        f"{frappe.utils.escape_html(getattr(doc, 'actiontext', '') or '-')}",
        "",
        f'<a href="{url}">Click here to view the record</a>',
        "",
        "Regards,",
        "Engineering System",
    ]

    message = "<br>".join(lines)

    try:
        frappe.sendmail(
            recipients=recipients,
            sender=sender,
            subject=subject,
            message=message,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
        )

        frappe.flags.in_wearcheck_alert_notification = True

        try:
            _set_wearcheck_notification_audit(doc, users)
        finally:
            frappe.flags.in_wearcheck_alert_notification = False

    except frappe.OutgoingEmailError:
        frappe.log_error(
            frappe.get_traceback(),
            "WearCheck Alert Email OutgoingEmailError",
        )
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "WearCheck Alert Email Failed",
        )