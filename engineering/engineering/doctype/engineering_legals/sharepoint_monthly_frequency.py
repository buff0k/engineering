from __future__ import annotations

import mimetypes
import os
from datetime import datetime
from urllib.parse import quote

import frappe
import requests
from frappe.utils import get_first_day, getdate, nowdate

from engineering.engineering.doctype.engineering_legals.engineering_legals import (
    NEW_SHAREPOINT_ROOT,
    NEW_SHAREPOINT_SECTION_MAPPING,
    NEW_SHAREPOINT_SITE_MAPPING,
    _ensure_sharepoint_folder,
    _get_graph_access_token,
    _get_sharepoint_drive_id,
    _get_sharepoint_settings,
    _get_sharepoint_site_id,
    _graph_request,
    _sanitize_sharepoint_part,
)


# These documents must remain visible in every monthly folder
# from their Start Date month through their Expiry Date month.
RECURRING_UNTIL_EXPIRY_SECTIONS = {
    "Fire Suppression",
    "Illumination Baseline",
    "Noise Level Baseline & Measurement",
    "NDT",
    "Machine NDT",
    "Brake Test",
    "FRCS",
    "Lifting Equipment",

    # These will begin working automatically once the exact ERP
    # section records and expiry rules are added.
    "Brake Tester Calibration Certificate",
    "Brake Test Authorisations",
    "CoC for Containers, Offices, Workshops",
    "Multi-meter Calibration Certificate",
    "Authorised LV Person",
    "Earth Leakage Testing",
    "Load Test Certificate",
    "Pressure Vessels",
}


def _month_start(value):
    if not value:
        return None

    return getdate(get_first_day(getdate(value)))


def _target_month(year=None, month=None):
    if year is None or month is None:
        selected = getdate(nowdate())
        year = selected.year
        month = selected.month

    year = int(year)
    month = int(month)

    if month < 1 or month > 12:
        frappe.throw("Month must be between 1 and 12.")

    month_date = getdate(f"{year:04d}-{month:02d}-01")
    month_folder = datetime(year, month, 1).strftime("%b-%y")

    return month_date, month_folder


def _get_attachment_file(doc):
    file_url = getattr(doc, "attach_paper", None)

    if not file_url:
        return None

    file_row = frappe.get_value(
        "File",
        {
            "attached_to_doctype": doc.doctype,
            "attached_to_name": doc.name,
            "file_url": file_url,
            "is_folder": 0,
        },
        "name",
    )

    if not file_row:
        file_row = frappe.get_value(
            "File",
            {
                "file_url": file_url,
                "is_folder": 0,
            },
            "name",
        )

    if not file_row:
        return None

    return frappe.get_doc("File", file_row)


def _build_filename(doc, file_doc):
    raw_date = getattr(doc, "start_date", None)

    if raw_date:
        date_part = getdate(raw_date).strftime("%Y-%m-%d")
    else:
        date_part = "No-Date"

    original_ext = os.path.splitext(
        file_doc.file_name or ""
    )[1] or ".pdf"

    return _sanitize_sharepoint_part(
        f"{(doc.fleet_number or 'No Fleet').strip()}-"
        f"{(doc.sections or 'Unclassified').strip()}-"
        f"{date_part}{original_ext}"
    )


def _sharepoint_item_exists(
    drive_id,
    folder_parts,
    filename,
    token,
):
    full_path = "/".join(
        [*folder_parts, filename]
    )

    encoded_path = quote(full_path, safe="/")

    url = (
        f"https://graph.microsoft.com/v1.0/drives/{drive_id}"
        f"/root:/{encoded_path}"
    )

    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )

    if response.status_code == 404:
        return False

    if response.status_code == 401:
        return False

    response.raise_for_status()
    return True


def _upload_to_month(
    doc,
    month_folder,
    drive_id,
    token,
    dry_run,
):
    site = (getattr(doc, "site", None) or "").strip()
    section = (getattr(doc, "sections", None) or "").strip()

    new_site = NEW_SHAREPOINT_SITE_MAPPING.get(site)
    category_parts = NEW_SHAREPOINT_SECTION_MAPPING.get(section)

    if not new_site:
        return {
            "status": "skipped",
            "reason": f"Site not configured: {site}",
        }

    if not category_parts:
        return {
            "status": "skipped",
            "reason": f"Section not mapped: {section}",
        }

    folder_parts = [
        NEW_SHAREPOINT_ROOT,
        month_folder,
        new_site,
        *category_parts,
    ]

    file_doc = _get_attachment_file(doc)

    if not file_doc:
        return {
            "status": "skipped",
            "reason": "Attachment File row not found",
        }

    filename = _build_filename(doc, file_doc)

    destination = "/".join(
        [*folder_parts, filename]
    )

    if dry_run:
        return {
            "status": "planned",
            "destination": destination,
        }

    parent_item_id = _ensure_sharepoint_folder(
        drive_id,
        folder_parts,
        token,
    )

    if _sharepoint_item_exists(
        drive_id,
        folder_parts,
        filename,
        token,
    ):
        return {
            "status": "existing",
            "destination": destination,
        }

    content = file_doc.get_content()

    if content is None:
        return {
            "status": "failed",
            "reason": "Could not read attachment content",
        }

    if isinstance(content, str):
        data = content.encode("utf-8")
    else:
        data = content

    encoded_filename = quote(filename)

    upload_url = (
        f"https://graph.microsoft.com/v1.0/drives/{drive_id}"
        f"/items/{parent_item_id}:/{encoded_filename}:/content"
    )

    mime_type = (
        mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    )

    _graph_request(
        "PUT",
        upload_url,
        token,
        data=data,
        headers={"Content-Type": mime_type},
    )

    return {
        "status": "uploaded",
        "destination": destination,
    }


def sync_active_legals_for_month(
    year=None,
    month=None,
    dry_run=True,
):
    """
    Copy active recurring Engineering Legals attachments into a
    selected new monthly SharePoint folder.

    Active rule:
        Start month <= selected month <= Expiry month

    The expiry month is included.
    The following month is excluded.
    """
    if isinstance(dry_run, str):
        dry_run = dry_run.strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
        }

    selected_month, month_folder = _target_month(
        year=year,
        month=month,
    )

    settings = _get_sharepoint_settings()
    token = _get_graph_access_token(settings)
    site_id = _get_sharepoint_site_id(
        settings,
        token,
    )
    drive_id = _get_sharepoint_drive_id(
        settings,
        site_id,
        token,
    )

    rows = frappe.get_all(
        "Engineering Legals",
        filters={
            "site": [
                "in",
                list(NEW_SHAREPOINT_SITE_MAPPING.keys()),
            ],
            "sections": [
                "in",
                list(RECURRING_UNTIL_EXPIRY_SECTIONS),
            ],
            "attach_paper": ["is", "set"],
        },
        fields=[
            "name",
            "site",
            "sections",
            "start_date",
            "expiry_date",
            "attach_paper",
        ],
        order_by="site asc, sections asc, start_date asc",
    )

    results = {
        "month": month_folder,
        "dry_run": dry_run,
        "checked": 0,
        "active": 0,
        "planned": 0,
        "uploaded": 0,
        "existing": 0,
        "skipped": 0,
        "failed": 0,
        "details": [],
    }

    for row in rows:
        results["checked"] += 1

        start_month = _month_start(row.start_date)
        expiry_month = _month_start(row.expiry_date)

        if not start_month:
            results["skipped"] += 1
            results["details"].append({
                "name": row.name,
                "status": "skipped",
                "reason": "Start Date is empty",
            })
            continue

        if not expiry_month:
            results["skipped"] += 1
            results["details"].append({
                "name": row.name,
                "status": "skipped",
                "reason": "Expiry Date is empty",
            })
            continue

        if selected_month < start_month:
            continue

        if selected_month > expiry_month:
            continue

        results["active"] += 1

        try:
            doc = frappe.get_doc(
                "Engineering Legals",
                row.name,
            )

            outcome = _upload_to_month(
                doc=doc,
                month_folder=month_folder,
                drive_id=drive_id,
                token=token,
                dry_run=dry_run,
            )

            status = outcome.get("status") or "failed"

            if status in results:
                results[status] += 1
            else:
                results["failed"] += 1

            results["details"].append({
                "name": row.name,
                "site": row.site,
                "section": row.sections,
                "start_date": row.start_date,
                "expiry_date": row.expiry_date,
                **outcome,
            })

            print(
                status.upper(),
                row.name,
                outcome.get("destination")
                or outcome.get("reason")
                or "",
            )

        except Exception:
            results["failed"] += 1

            error = frappe.get_traceback()

            results["details"].append({
                "name": row.name,
                "status": "failed",
                "reason": error,
            })

            frappe.log_error(
                error,
                "Engineering Legals monthly frequency sync",
            )

            print("FAILED", row.name)

    print()
    print("=== MONTHLY FREQUENCY SUMMARY ===")
    print("Month:", results["month"])
    print("Dry run:", results["dry_run"])
    print("Checked:", results["checked"])
    print("Active:", results["active"])
    print("Planned:", results["planned"])
    print("Uploaded:", results["uploaded"])
    print("Already existing:", results["existing"])
    print("Skipped:", results["skipped"])
    print("Failed:", results["failed"])

    return results


def run_current_month_frequency_sync():
    """
    Scheduled task.

    Runs for the current month and uploads only active recurring
    documents that are not already present.
    """
    return sync_active_legals_for_month(
        dry_run=False,
    )
