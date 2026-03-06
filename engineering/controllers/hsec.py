import base64
import mimetypes

import frappe
from frappe.utils import now_datetime


def _file_to_base64_and_mime(file_url: str):
    """Returns (b64, mime, filename) for a File referenced by file_url."""
    if not file_url:
        return None, None, None

    # Always use /files/ form for lookup consistency
    public_url = file_url.replace("/private/files/", "/files/")

    file_row = frappe.db.get_value(
        "File",
        {"file_url": public_url},
        ["name", "file_name", "file_url", "file_type", "is_private"],
        as_dict=True,
    )
    if not file_row:
        return None, None, None

    file_doc = frappe.get_doc("File", file_row.name)

    # Read raw bytes / text
    try:
        content = file_doc.get_content()
    except Exception:
        return None, None, file_row.file_name

    if isinstance(content, str):
        content = content.encode("utf-8")

    b64 = base64.b64encode(content).decode("utf-8")

    mime = (
        mimetypes.guess_type(file_row.file_name or "")[0]
        or (file_row.file_type or "")
        or "application/octet-stream"
    )

    return b64, mime, file_row.file_name



def _build_onedrive_target_path(site: str, section: str, fleet: str, file_name: str) -> str:
    site = (site or "").strip() or "Unknown Site"
    section = (section or "").strip() or "Unclassified"
    fleet = (fleet or "").strip() or "No Fleet"
    file_name = (file_name or "").strip() or "attachment"

    return f"Isambane/{site}/{section}/{fleet}/{file_name}"


@frappe.whitelist()
def get_onedrive_engineering_legal_files(since: str = None, limit: int = 50, offset: int = 0):
    """
    Returns Engineering Legals files for OneDrive upload.

    Rules:
    - source = File list / attach_paper
    - only sites: GWAB, Klipfontein
    - path format: Isambane/<Site>/<Section>/<Fleet>/<File Name>
    """
    limit = int(limit or 50)
    offset = int(offset or 0)

    filters = [
        ["docstatus", "<", 2],
        ["site", "in", ["GWAB", "Klipfontein"]],
        ["attach_paper", "is", "set"],
    ]

    if since:
        filters.append(["modified", ">", since])

    rows = frappe.get_all(
        "Engineering Legals",
        filters=filters,
        fields=[
            "name",
            "site",
            "sections",
            "fleet_number",
            "attach_paper",
            "modified",
        ],
        order_by="modified asc",
        limit_page_length=limit,
        limit_start=offset,
    )

    out = []
    for r in rows:
        b64, mime, fname = _file_to_base64_and_mime(r.get("attach_paper"))
        if not fname:
            continue

        out.append(
            {
                "source_docname": r.get("name"),
                "site": r.get("site"),
                "section": r.get("sections"),
                "fleet": r.get("fleet_number"),
                "file_url": r.get("attach_paper"),
                "file_name": fname,
                "mime_type": mime,
                "target_path": _build_onedrive_target_path(
                    r.get("site"),
                    r.get("sections"),
                    r.get("fleet_number"),
                    fname,
                ),
                "file_content_base64": b64,
                "modified": r.get("modified"),
            }
        )

    return {
        "server_time": str(now_datetime()),
        "count": len(out),
        "limit": limit,
        "offset": offset,
        "since": since,
        "data": out,
    }






@frappe.whitelist()
def get_hsec_equipment_docs(since: str = None, limit: int = 50, offset: int = 0):
    """
    HSEC pulls new/updated docs.
    since: ISO datetime string, e.g. 2026-02-19 08:00:00
    """
    limit = int(limit or 50)
    offset = int(offset or 0)

    filters = [
        ["hsec_send", "=", 1],
        ["docstatus", "<", 2],
    ]
    if since:
        filters.append(["modified", ">", since])

    rows = frappe.get_all(
        "Engineering Legals",
        filters=filters,
        fields=[
            "name",
            "fleet_number",
            "start_date",
            "expiry_date",
            "hsec_qual_category_id",
            "hsec_qualification_id_external",
            "attach_paper",
            "modified",
        ],
        order_by="modified asc",
        limit_page_length=limit,
        limit_start=offset,
    )

    out = []
    for r in rows:
        b64, mime, fname = _file_to_base64_and_mime(r.get("attach_paper"))
        out.append(
            {
                # HSEC fields / meaning:
                "Qual_Category_ID": r.get("hsec_qual_category_id"),
                "ID_No": r.get("fleet_number"),
                "Qualification_Date_Start": r.get("start_date"),
                "Qualification_Date_End": r.get("expiry_date"),
                "Qualification_ID_External": r.get("hsec_qualification_id_external"),
                "Document_Image": b64,
                "Document_Mime_Type": mime,
                "Document_Name": fname,
                # helpers:
                "source_docname": r.get("name"),
                "modified": r.get("modified"),
            }
        )

    return {
        "server_time": str(now_datetime()),
        "count": len(out),
        "limit": limit,
        "offset": offset,
        "since": since,
        "data": out,
    }
