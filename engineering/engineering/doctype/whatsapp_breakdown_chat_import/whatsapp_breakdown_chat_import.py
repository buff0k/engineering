import os
import re
import zipfile
import tempfile

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate, today

from engineering.engineering.doctype.whatsapp_breakdown_message_log.whatsapp_breakdown_message_log import (
    parse_whatsapp_breakdown_message,
    create_or_update_breakdown,
)


class WhatsAppBreakdownChatImport(Document):
    def autoname(self):
        site = self.target_site or self.group_name or "WhatsApp Import"
        site = str(site).strip().replace("/", "-")

        dt = self.creation or frappe.utils.now_datetime()
        dt = frappe.utils.get_datetime(dt)

        base_name = f"{site}-{dt.strftime('%Y-%m-%d')}-Time-{dt.strftime('%H-%M')}"

        name = base_name
        counter = 1

        while frappe.db.exists("WhatsApp Breakdown Chat Import", name):
            name = f"{base_name}-{counter}"
            counter += 1

        self.name = name

    def on_trash(self):
        delete_linked_message_logs(self.name)


def delete_linked_message_logs(import_name):
    count = frappe.db.count(
        "WhatsApp Breakdown Message Log",
        filters={"source_chat_import": import_name},
    )

    if not count:
        return

    frappe.db.delete(
        "WhatsApp Breakdown Message Log",
        {
            "source_chat_import": import_name,
        },
    )

    frappe.msgprint(f"Deleted {count} linked WhatsApp Breakdown Message Log records.")


def get_file_path(file_url):
    if not file_url:
        frappe.throw("Please attach a WhatsApp chat .txt or .zip file.")

    file_doc = frappe.get_doc("File", {"file_url": file_url})
    return file_doc.get_full_path()


def read_chat_text(file_path):
    if file_path.lower().endswith(".zip"):
        with zipfile.ZipFile(file_path, "r") as z:
            txt_files = [name for name in z.namelist() if name.lower().endswith(".txt")]

            if not txt_files:
                frappe.throw("No .txt WhatsApp chat file found inside the zip.")

            with tempfile.TemporaryDirectory() as tmpdir:
                name = txt_files[0]
                z.extract(name, tmpdir)
                extracted_path = os.path.join(tmpdir, name)

                with open(extracted_path, "rb") as f:
                    raw = f.read()
    else:
        with open(file_path, "rb") as f:
            raw = f.read()

    for encoding in ["utf-8", "utf-8-sig", "cp1252", "latin-1"]:
        try:
            return raw.decode(encoding)
        except Exception:
            continue

    return raw.decode("utf-8", errors="ignore")


def normalize_message_text(text):
    text = text or ""
    text = text.replace("\u202f", " ")
    text = text.replace("\xa0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def parse_whatsapp_datetime(date_text, time_text, ampm):
    date_text = date_text.strip()
    time_text = time_text.strip()
    ampm = (ampm or "").strip().lower().replace(".", "")

    if ampm:
        candidate = f"{date_text} {time_text} {ampm}"
    else:
        candidate = f"{date_text} {time_text}"

    formats = [
        "%Y/%m/%d %I:%M %p",
        "%Y/%m/%d %H:%M",
        "%d/%m/%Y %I:%M %p",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d %H:%M",
    ]

    from datetime import datetime

    for fmt in formats:
        try:
            return datetime.strptime(candidate, fmt)
        except Exception:
            pass

    return get_datetime()


def parse_exported_chat(chat_text):
    chat_text = normalize_message_text(chat_text)

    pattern = re.compile(
        r"^(?P<date>\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{4}),\s*"
        r"(?P<time>\d{1,2}:\d{2})\s*(?P<ampm>[ap]\.?m\.?)?\s*-\s*"
        r"(?P<body>.*)$",
        re.IGNORECASE,
    )

    messages = []
    current = None

    for line in chat_text.split("\n"):
        line = line.rstrip()
        match = pattern.match(line)

        if match:
            if current:
                messages.append(current)

            body = match.group("body") or ""

            sender = ""
            message = body

            if ": " in body:
                sender, message = body.split(": ", 1)

            current = {
                "datetime": parse_whatsapp_datetime(
                    match.group("date"),
                    match.group("time"),
                    match.group("ampm"),
                ),
                "sender": sender.strip(),
                "message": message.strip(),
                "raw_body": body.strip(),
            }
        else:
            if current:
                current["message"] = (current["message"] + "\n" + line).strip()

    if current:
        messages.append(current)

    return messages


def contains_plant_number(text):
    return bool(re.search(r"\b(IS|EX)\s*0*\d{2,4}\b", text or "", re.IGNORECASE))


def is_full_status_report(text):
    text_lower = (text or "").lower()

    status_markers = [
        "breakdown reports",
        "available adt",
        "available adt's",
        "available adts",
        "excavators",
        "dozers",
        "water bowsers",
        "graders",
    ]

    marker_count = sum(1 for marker in status_markers if marker in text_lower)

    if marker_count >= 2:
        return True

    if "available" in text_lower and ("✅" in text_lower or "❌" in text_lower):
        return True

    return False


def is_system_or_blank_message(message_text):
    if not message_text or not message_text.strip():
        return True

    message_text_lower = message_text.strip().lower()

    if message_text_lower in [
        "<media omitted>",
        "this message was deleted",
        "you deleted this message",
    ]:
        return True

    if "messages and calls are end-to-end encrypted" in message_text_lower:
        return True

    return False


def make_unique_source_id(import_name, message_datetime, sender, message):
    base = f"{import_name}|{message_datetime}|{sender}|{message}"
    return frappe.generate_hash(base, 20)


@frappe.whitelist()
def import_chat(import_name):
    doc = frappe.get_doc("WhatsApp Breakdown Chat Import", import_name)

    file_path = get_file_path(doc.chat_file)
    chat_text = read_chat_text(file_path)
    parsed_messages = parse_exported_chat(chat_text)

    total = 0
    created = 0
    duplicates = 0
    ignored = 0
    needs_review = 0
    skipped_by_action = 0
    skipped_by_date = 0
    skipped_status_reports = 0

    import_from_date = getdate(doc.import_from_date or "2026-06-01")
    import_to_date = getdate(doc.import_to_date or today())

    for msg in parsed_messages:
        total += 1

        message_text = normalize_message_text(msg.get("message"))
        sender = msg.get("sender") or ""
        message_datetime = msg.get("datetime")
        message_date = getdate(message_datetime)

        if message_date < import_from_date or message_date > import_to_date:
            skipped_by_date += 1
            continue

        if is_system_or_blank_message(message_text):
            ignored += 1
            continue

        source_id = make_unique_source_id(
            doc.name,
            message_datetime,
            sender,
            message_text,
        )

        if frappe.db.exists(
            "WhatsApp Breakdown Message Log",
            {"source_message_id": source_id},
        ):
            duplicates += 1
            continue

        # Status reports are ignored outright when requested. They must not be
        # parsed into Book Down / Book Back actions or Needs Review records.
        if doc.skip_status_reports and is_full_status_report(message_text):
            skipped_status_reports += 1
            ignored += 1
            continue

        # When only plant-related messages are requested, a message without a
        # plant number is an ignored message. Create an Ignored log only when
        # the user has not asked to skip ignored messages.
        if doc.only_messages_with_plant and not contains_plant_number(message_text):
            ignored += 1

            if doc.skip_ignored_messages:
                continue

            log = frappe.new_doc("WhatsApp Breakdown Message Log")
            log.message_datetime = message_datetime
            log.sender_name = sender
            log.group_name = doc.group_name
            log.target_site = doc.target_site
            log.raw_message = message_text
            log.source_message_id = source_id
            log.source_chat_import = doc.name
            log.detected_action = "Unknown"
            log.status = "Ignored"
            log.error_message = "Ignored because no plant number was found."
            log.insert(ignore_permissions=True)

            created += 1
            continue

        log = frappe.new_doc("WhatsApp Breakdown Message Log")
        log.message_datetime = message_datetime
        log.sender_name = sender
        log.group_name = doc.group_name
        log.target_site = doc.target_site
        log.raw_message = message_text
        log.source_message_id = source_id
        log.source_chat_import = doc.name

        parse_whatsapp_breakdown_message(log)

        if log.status == "Needs Review":
            needs_review += 1

            if doc.skip_needs_review_messages:
                continue

        if log.status == "Ignored":
            ignored += 1

            if doc.skip_ignored_messages:
                continue

        if log.detected_action == "Book Down" and not doc.import_book_down_messages:
            skipped_by_action += 1
            continue

        if log.detected_action == "Book Back" and not doc.import_book_back_messages:
            skipped_by_action += 1
            continue

        log.insert(ignore_permissions=True)
        created += 1

    doc.total_messages_found = total
    doc.logs_created = created
    doc.duplicates_skipped = duplicates
    doc.ignored_messages = ignored
    doc.needs_review_messages = needs_review
    doc.import_status = "Completed"

    result_messages = []

    if skipped_status_reports:
        result_messages.append(
            f"Skipped full status reports: {skipped_status_reports}"
        )

    if skipped_by_date:
        result_messages.append(
            f"Skipped outside import date range: {skipped_by_date}"
        )

    if skipped_by_action:
        result_messages.append(
            f"Skipped by Book Down/Book Back filter: {skipped_by_action}"
        )

    doc.error_message = "\n".join(result_messages) if result_messages else None
    doc.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "total_messages_found": total,
        "logs_created": created,
        "duplicates_skipped": duplicates,
        "ignored_messages": ignored,
        "needs_review_messages": needs_review,
        "skipped_status_reports": skipped_status_reports,
        "skipped_by_action": skipped_by_action,
        "skipped_by_date": skipped_by_date,
    }
