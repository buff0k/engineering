import re
import frappe
from bs4 import BeautifulSoup
from frappe.utils import now_datetime


def clean_html_message(message):
    if not message:
        return ""

    text = str(message)

    try:
        soup = BeautifulSoup(text, "html.parser")
        text = soup.get_text("\n")
    except Exception:
        pass

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]

    return "\n".join(lines).strip()


def should_ignore_message(text):
    text_lower = (text or "").strip().lower()

    if not text_lower:
        return True

    ignore_exact = {
        "ok",
        "okay",
        "noted",
        "thanks",
        "thank you",
        "received",
        "location?",
        "location",
        "where",
        "yes",
        "no",
    }

    if text_lower in ignore_exact:
        return True

    # Ignore questions or instruction messages that do not contain a plant number
    has_plant = re.search(r"\b(IS|EX)\s*0*\d{2,4}\b", text_lower, re.IGNORECASE)

    if not has_plant:
        return True

    return False


def whatsapp_message_after_insert(doc, method=None):
    try:
        # Only process incoming WhatsApp text messages
        if getattr(doc, "type", None) != "Incoming":
            return

        if getattr(doc, "content_type", None) and doc.content_type != "text":
            return

        raw_text = clean_html_message(getattr(doc, "message", ""))

        if not raw_text:
            return

        # Prevent duplicates
        existing = None

        if getattr(doc, "name", None):
            existing = frappe.db.exists(
                "WhatsApp Breakdown Message Log",
                {"source_whatsapp_message": doc.name},
            )

        if not existing and getattr(doc, "message_id", None):
            existing = frappe.db.exists(
                "WhatsApp Breakdown Message Log",
                {"source_message_id": doc.message_id},
            )

        if existing:
            return

        log = frappe.new_doc("WhatsApp Breakdown Message Log")
        log.message_datetime = getattr(doc, "creation", None) or now_datetime()
        log.source_whatsapp_message = getattr(doc, "name", None)
        log.source_message_id = getattr(doc, "message_id", None)
        log.sender_number = getattr(doc, "from", None)
        log.sender_name = getattr(doc, "profile_name", None)

        # frappe_whatsapp does not clearly store WhatsApp group name here.
        # Use available fields until we map real breakdown group later.
        log.group_name = (
            getattr(doc, "label", None)
            or getattr(doc, "conversation_id", None)
            or getattr(doc, "whatsapp_account", None)
            or getattr(doc, "to", None)
        )

        log.raw_message = raw_text

        if should_ignore_message(raw_text):
            log.status = "Ignored"
            log.error_message = "Message ignored because it is not a breakdown/service message."
            log.insert(ignore_permissions=True)
            return

        # Parser will run on validate and set Parsed / Needs Review
        log.insert(ignore_permissions=True)

    except Exception:
        frappe.log_error(
            title="WhatsApp Breakdown Import Error",
            message=frappe.get_traceback(),
        )
