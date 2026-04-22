import base64
import re

import frappe
from frappe.utils import getdate
from frappe.utils.file_manager import save_file


DATE_PATTERNS = [
    re.compile(r"(?P<d>\d{2})-(?P<m>\d{2})-(?P<y>\d{4})"),
    re.compile(r"(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})"),
]


def _parse_date(value: str):
    value = (value or "").strip()
    if not value:
        return None

    for rx in DATE_PATTERNS:
        m = rx.search(value)
        if not m:
            continue

        d = int(m.group("d"))
        mth = int(m.group("m"))
        y = int(m.group("y"))
        return getdate(f"{y:04d}-{mth:02d}-{d:02d}")

    return None


def _require_exists(doctype: str, name: str, label: str):
    if not name:
        frappe.throw(f"{label} is required.")

    if not frappe.db.exists(doctype, name):
        frappe.throw(f"{label} '{name}' does not exist in {doctype}.")




def _get_mapped_value(mapping_type: str, source_value: str):
    source_value = (source_value or "").strip()
    if not source_value:
        return source_value

    row = frappe.db.get_value(
        "Engineering Legals Import Mapping",
        {
            "mapping_type": mapping_type,
            "source_value": source_value,
            "enabled": 1,
        },
        ["target_value"],
        as_dict=True,
    )

    if row and row.get("target_value"):
        return row.get("target_value").strip()

    return source_value





@frappe.whitelist()
def import_legacy_legal():
    """
    JSON/body args expected from PowerShell:

    {
      "site": "GWAB",
      "sections": "Brake Test",
      "fleet_number": "IS543",
      "start_date": "2026-01-21",
      "file_name": "IS543 - Brake test - 21-01-2026.pdf",
      "file_content_base64": "<base64>",
      "vehicle_type": "TMM",          # only for Brake Test / PDS
      "lifting_type": "Inspection"    # only for Lifting Equipment
    }
    """
    data = frappe.local.form_dict or {}

    raw_site = (data.get("site") or "").strip()
    raw_sections = (data.get("sections") or "").strip()
    raw_fleet_number = (data.get("fleet_number") or "").strip()

    site = _get_mapped_value("Location", raw_site)
    sections = _get_mapped_value("Section", raw_sections)
    fleet_number = _get_mapped_value("Asset", raw_fleet_number)

    file_name = (data.get("file_name") or "").strip()
    file_b64 = data.get("file_content_base64")
    vehicle_type = (data.get("vehicle_type") or "").strip() or None
    lifting_type = (data.get("lifting_type") or "").strip() or None

    start_date = _parse_date(data.get("start_date") or "")
    if not start_date:
        frappe.throw("Valid start_date is required. Use dd-mm-yyyy or yyyy-mm-dd.")

    if not file_name:
        frappe.throw("file_name is required.")
    if not file_b64:
        frappe.throw("file_content_base64 is required.")

    _require_exists("Location", site, "Site")
    _require_exists("Engineering Legals Sections", sections, "Section")
    _require_exists("Asset", fleet_number, "Fleet Number")

    existing = frappe.db.exists(
        "Engineering Legals",
        {
            "site": site,
            "sections": sections,
            "fleet_number": fleet_number,
            "start_date": start_date,
        },
    )
    if existing:
        return {
            "ok": 1,
            "skipped": 1,
            "reason": "duplicate",
            "name": existing,
        }

    try:
        file_bytes = base64.b64decode(file_b64)
    except Exception:
        frappe.throw("file_content_base64 is not valid base64.")

    doc = frappe.get_doc(
        {
            "doctype": "Engineering Legals",
            "site": site,
            "sections": sections,
            "fleet_number": fleet_number,
            "start_date": start_date,
            "vehicle_type": vehicle_type,
            "lifting_type": lifting_type,
        }
    )

    # attach_paper is mandatory on the DocType, so create parent once with ignore_mandatory,
    # then attach the file, then save normally so all validation still runs.
    doc.insert(ignore_permissions=True, ignore_mandatory=True)

    saved_file = save_file(
        fname=file_name,
        content=file_bytes,
        dt="Engineering Legals",
        dn=doc.name,
        is_private=0,
    )

    doc.attach_paper = saved_file.file_url
    doc.save(ignore_permissions=True)

    return {
        "ok": 1,
        "name": doc.name,
        "file_url": doc.attach_paper,
        "expiry_date": doc.expiry_date,
    }