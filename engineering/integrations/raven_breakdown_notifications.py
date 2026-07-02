import frappe
from frappe.utils import get_url_to_form, format_datetime, now_datetime, get_datetime


DEFAULT_RAVEN_CHANNEL = "Isambane Mining-all-site-fallback-channel"

SITE_CHANNELS = {
    "Gwab": "Isambane Mining-raven-engineering-downtime-gwab",
    "GWAB": "Isambane Mining-raven-engineering-downtime-gwab",

    "Klipfontein": "Isambane Mining-raven-engineering-downtime-klipfontein",
    "KLP": "Isambane Mining-raven-engineering-downtime-klipfontein",

    "Koppie": "Isambane Mining-raven-engineering-downtime-koppie",

    "Kriel Rehabilitation": "Isambane Mining-raven-engineering-downtime-kriel",
    "KRR": "Isambane Mining-raven-engineering-downtime-kriel",

    "Uitgevallen": "Isambane Mining-raven-engineering-downtime-uitgevallen",
    "UIT": "Isambane Mining-raven-engineering-downtime-uitgevallen",

    "Bankfontein": "Isambane Mining-raven-engineering-downtime-bankfontein",
    "BFT": "Isambane Mining-raven-engineering-downtime-bankfontein",

    "Grinaker": "Isambane Mining-raven-engineering-downtime-grinaker",
    "Mimosa": "Isambane Mining-raven-engineering-downtime-grinaker",
}


def _safe(value):
    if value in (None, ""):
        return "-"
    return value


def _safe_datetime(value):
    if not value:
        return "-"
    return format_datetime(value)


def _safe_number(value):
    try:
        return round(float(value or 0), 2)
    except Exception:
        return "-"


def _doc_link(doc):
    return get_url_to_form(doc.doctype, doc.name)


def _get_site_channel(location):
    return SITE_CHANNELS.get(location) or DEFAULT_RAVEN_CHANNEL


def _message_marker(doc):
    return f"PLANT_BREAKDOWN_DOC::{doc.name}"


def _send_raven_message(message, channel_id):
    raven_msg = frappe.get_doc({
        "doctype": "Raven Message",
        "channel_id": channel_id,
        "text": message,
        "message_type": "Text",
    })
    raven_msg.insert(ignore_permissions=True)
    return raven_msg.name


def _find_breakdown_raven_message(doc):
    marker = _message_marker(doc)

    rows = frappe.get_all(
        "Raven Message",
        filters={
            "text": ["like", f"%{marker}%"],
        },
        fields=["name"],
        order_by="creation desc",
        limit=1,
    )

    if rows:
        return rows[0].name

    return None


def _update_raven_message(message_name, message, channel_id=None):
    raven_msg = frappe.get_doc("Raven Message", message_name)
    raven_msg.text = message

    if channel_id:
        raven_msg.channel_id = channel_id

    raven_msg.save(ignore_permissions=True)
    return raven_msg.name


def _build_open_message(doc):
    marker = _message_marker(doc)

    return f"""
        <p><b>🚨 BREAKDOWN OPEN | {_safe(doc.asset_name)} | {_safe(doc.location)}</b></p>

        <p>
            <b>Site:</b> {_safe(doc.location)}<br>
            <b>Shift:</b> {_safe(doc.shift)}<br>
            <b>Type:</b> {_safe(doc.downtime_type)}<br>
            <b>Machine:</b> {_safe(doc.asset_name)} - {_safe(doc.asset_category)} - {_safe(doc.item_name)}<br>
            <b>Hours Breakdown/Maintenance Start:</b> {_safe_number(doc.hours_breakdown_starts)}<br>
            <b>Start Time:</b> {_safe_datetime(doc.breakdown_start_datetime)}<br>
            <b>Status:</b> {_safe(doc.open_closed)}
        </p>

        <p><b>Reason:</b><br>{_safe(doc.breakdown_reason)}</p>

        <p>
            <a href="{_doc_link(doc)}">Open Plant Breakdown / Maintenance</a>
        </p>

        <p style="display:none">{marker}</p>
    """


def _build_closed_message(doc):
    marker = _message_marker(doc)

    return f"""
        <p><b>✅ BREAKDOWN CLOSED | {_safe(doc.asset_name)} | {_safe_number(doc.breakdown_hours)} hrs</b></p>

        <p>
            <b>Site:</b> {_safe(doc.location)}<br>
            <b>Shift:</b> {_safe(doc.shift)}<br>
            <b>Type:</b> {_safe(doc.downtime_type)}<br>
            <b>Machine:</b> {_safe(doc.asset_name)} - {_safe(doc.asset_category)} - {_safe(doc.item_name)}<br>
            <b>Hours Breakdown/Maintenance Start:</b> {_safe_number(doc.hours_breakdown_starts)}<br>
            <b>Start Time:</b> {_safe_datetime(doc.breakdown_start_datetime)}<br>
            <b>Resolved Time:</b> {_safe_datetime(doc.resolved_datetime)}<br>
            <b>Total Hours:</b> {_safe_number(doc.breakdown_hours)}
        </p>

        <p><b>Resolution Summary:</b><br>{_safe(doc.resolution_summary)}</p>

        <p>
            <a href="{_doc_link(doc)}">Open Plant Breakdown / Maintenance</a>
        </p>

        <p style="display:none">{marker}</p>
    """


def send_new_breakdown_message(doc, method=None):
    channel_id = _get_site_channel(doc.location)
    message = _build_open_message(doc)

    existing_message = _find_breakdown_raven_message(doc)

    if existing_message:
        _update_raven_message(existing_message, message, channel_id)
    else:
        _send_raven_message(message, channel_id)


def send_closed_breakdown_message(doc, method=None):
    if doc.open_closed != "Closed":
        return

    old_doc = doc.get_doc_before_save()

    if not old_doc:
        return

    if old_doc.open_closed == doc.open_closed:
        return

    channel_id = _get_site_channel(doc.location)
    message = _build_closed_message(doc)

    existing_message = _find_breakdown_raven_message(doc)

    if existing_message:
        _update_raven_message(existing_message, message, channel_id)
    else:
        _send_raven_message(message, channel_id)


def _alert_already_sent(docname, alert_level):
    marker = f"RAVEN_BREAKDOWN_ALERT::{alert_level}::{docname}"

    existing = frappe.get_all(
        "Raven Message",
        filters={
            "text": ["like", f"%{marker}%"],
        },
        fields=["name"],
        limit=1,
    )

    return bool(existing)


def _send_long_open_alert(doc, open_hours, alert_level):
    if _alert_already_sent(doc.name, alert_level):
        return

    channel_id = _get_site_channel(doc.location)
    marker = f"RAVEN_BREAKDOWN_ALERT::{alert_level}::{doc.name}"

    if alert_level == "2H":
        heading = "⚠️ BREAKDOWN STILL OPEN AFTER 2 HOURS"
    else:
        heading = "🚨 CRITICAL BREAKDOWN OPEN AFTER 4 HOURS"

    message = f"""
        <p><b>{heading} | {_safe(doc.asset_name)} | {_safe(doc.location)}</b></p>

        <p>
            <b>Site:</b> {_safe(doc.location)}<br>
            <b>Shift:</b> {_safe(doc.shift)}<br>
            <b>Machine:</b> {_safe(doc.asset_name)} - {_safe(doc.asset_category)} - {_safe(doc.item_name)}<br>
            <b>Start Time:</b> {_safe_datetime(doc.breakdown_start_datetime)}<br>
            <b>Open For:</b> {_safe_number(open_hours)} hours<br>
            <b>Status:</b> {_safe(doc.open_closed)}
        </p>

        <p><b>Reason:</b><br>{_safe(doc.breakdown_reason)}</p>

        <p>
            <a href="{_doc_link(doc)}">Open Plant Breakdown / Maintenance</a>
        </p>

        <p style="display:none">{marker}</p>
    """

    _send_raven_message(message, channel_id)


def send_long_open_breakdown_alerts():
    now = now_datetime()

    open_docs = frappe.get_all(
        "Plant Breakdown or Maintenance",
        filters={
            "open_closed": ["!=", "Closed"],
            "breakdown_start_datetime": ["is", "set"],
        },
        fields=[
            "name",
            "location",
            "shift",
            "downtime_type",
            "asset_name",
            "item_name",
            "asset_category",
            "hours_breakdown_starts",
            "breakdown_start_datetime",
            "breakdown_reason",
            "open_closed",
        ],
        limit=500,
    )

    for row in open_docs:
        if not row.breakdown_start_datetime:
            continue

        start_time = get_datetime(row.breakdown_start_datetime)
        open_hours = (now - start_time).total_seconds() / 3600

        if open_hours >= 4:
            _send_long_open_alert(row, open_hours, "4H")
        elif open_hours >= 2:
            _send_long_open_alert(row, open_hours, "2H")

    frappe.db.commit()
