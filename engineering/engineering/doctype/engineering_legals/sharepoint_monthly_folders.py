from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import frappe
import requests


SITES = [
    "Gwab",
    "Klipfontein",
]

SUBFOLDERS = [
    "01. Automatic Fire Suppression",
    "02. Condition Monitoring",
    "03. Dynamic Brake Testing",
    "04. Earth Leakage Testing & CoC",
    "05. Equipment list",
    "06. FRCS Compliance",
    "07. Load Testing",
    "08. Maintenance Schedules",
    "09. PDS-MPI Maintenance",
    "10. Pressure Vessels",
]

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


def _get_configuration() -> dict:
    tenant_id = frappe.conf.get("ms_graph_tenant_id")
    client_id = frappe.conf.get("ms_graph_client_id")
    client_secret = frappe.conf.get("ms_graph_client_secret")

    hostname = (
        frappe.conf.get("sharepoint_hostname") or ""
    ).strip()

    site_path = (
        frappe.conf.get("sharepoint_site_path") or ""
    ).strip("/")

    drive_name = (
        frappe.conf.get("sharepoint_drive_name") or "Documents"
    ).strip()

    hostname = (
        hostname
        .replace("https://", "")
        .replace("http://", "")
        .rstrip("/")
    )

    required = {
        "ms_graph_tenant_id": tenant_id,
        "ms_graph_client_id": client_id,
        "ms_graph_client_secret": client_secret,
        "sharepoint_hostname": hostname,
        "sharepoint_site_path": site_path,
        "sharepoint_drive_name": drive_name,
    }

    missing = [
        key
        for key, value in required.items()
        if not value
    ]

    if missing:
        frappe.throw(
            "Missing SharePoint configuration: "
            + ", ".join(missing)
        )

    return {
        "tenant_id": tenant_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "hostname": hostname,
        "site_path": site_path,
        "drive_name": drive_name,
    }


def _get_access_token(config: dict) -> str:
    response = requests.post(
        (
            "https://login.microsoftonline.com/"
            f"{config['tenant_id']}/oauth2/v2.0/token"
        ),
        data={
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
        timeout=30,
    )

    response.raise_for_status()

    access_token = response.json().get("access_token")

    if not access_token:
        frappe.throw(
            "Microsoft Graph did not return an access token."
        )

    return access_token


def _get_headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def _get_site(config: dict, headers: dict) -> dict:
    response = requests.get(
        (
            f"{GRAPH_BASE_URL}/sites/"
            f"{config['hostname']}:/{config['site_path']}"
        ),
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


def _get_drive(
    site_id: str,
    drive_name: str,
    headers: dict,
) -> dict:
    response = requests.get(
        f"{GRAPH_BASE_URL}/sites/{site_id}/drives",
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    drives = response.json().get("value", [])

    for drive in drives:
        current_name = (drive.get("name") or "").strip()

        if current_name.lower() == drive_name.lower():
            return drive

    available = [
        drive.get("name")
        for drive in drives
        if drive.get("name")
    ]

    frappe.throw(
        f"SharePoint document library '{drive_name}' "
        f"was not found. Available libraries: "
        f"{', '.join(available)}"
    )


def _get_item_by_path(
    drive_id: str,
    folder_path: str,
    headers: dict,
) -> dict | None:
    encoded_path = quote(folder_path, safe="/")

    response = requests.get(
        (
            f"{GRAPH_BASE_URL}/drives/{drive_id}"
            f"/root:/{encoded_path}"
        ),
        headers=headers,
        timeout=30,
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()


def _ensure_folder(
    drive_id: str,
    parent_path: str,
    folder_name: str,
    headers: dict,
) -> str:
    if parent_path:
        full_path = (
            parent_path.strip("/")
            + "/"
            + folder_name.strip("/")
        )
    else:
        full_path = folder_name.strip("/")

    existing = _get_item_by_path(
        drive_id=drive_id,
        folder_path=full_path,
        headers=headers,
    )

    if existing:
        if not existing.get("folder"):
            frappe.throw(
                "A file already exists where a folder "
                f"is required: {full_path}"
            )

        return "existing"

    if parent_path:
        parent = _get_item_by_path(
            drive_id=drive_id,
            folder_path=parent_path,
            headers=headers,
        )

        if not parent:
            frappe.throw(
                f"Parent folder does not exist: {parent_path}"
            )

        endpoint = (
            f"{GRAPH_BASE_URL}/drives/{drive_id}"
            f"/items/{parent['id']}/children"
        )
    else:
        endpoint = (
            f"{GRAPH_BASE_URL}/drives/{drive_id}"
            "/root/children"
        )

    response = requests.post(
        endpoint,
        headers=headers,
        json={
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail",
        },
        timeout=30,
    )

    if response.status_code == 409:
        existing = _get_item_by_path(
            drive_id=drive_id,
            folder_path=full_path,
            headers=headers,
        )

        if existing and existing.get("folder"):
            return "existing"

        frappe.throw(
            f"SharePoint folder conflict: {full_path}"
        )

    response.raise_for_status()
    return "created"


def ensure_month_folders(
    year: str | int | None = None,
    month: str | None = None,
) -> dict:
    """
    Create the year, site, current month and standard folders.

    Existing folders and files are never overwritten.

    Examples:
        ensure_month_folders()
        ensure_month_folders(year=2027, month="January")
    """

    current_date = frappe.utils.now_datetime()

    selected_year = str(
        year or current_date.strftime("%Y")
    )

    selected_month = (
        month or current_date.strftime("%B")
    ).strip()

    valid_months = {
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    }

    if selected_month not in valid_months:
        frappe.throw(
            f"Invalid month name: {selected_month}"
        )

    config = _get_configuration()
    access_token = _get_access_token(config)
    headers = _get_headers(access_token)

    sharepoint_site = _get_site(
        config=config,
        headers=headers,
    )

    drive = _get_drive(
        site_id=sharepoint_site["id"],
        drive_name=config["drive_name"],
        headers=headers,
    )

    drive_id = drive["id"]

    created_paths = []
    existing_paths = []

    def ensure(parent_path: str, folder_name: str) -> None:
        if parent_path:
            full_path = (
                parent_path.strip("/")
                + "/"
                + folder_name.strip("/")
            )
        else:
            full_path = folder_name.strip("/")

        result = _ensure_folder(
            drive_id=drive_id,
            parent_path=parent_path,
            folder_name=folder_name,
            headers=headers,
        )

        if result == "created":
            created_paths.append(full_path)
            frappe.logger("engineering_legals").info(
                f"Created SharePoint folder: {full_path}"
            )
        else:
            existing_paths.append(full_path)

    ensure("", selected_year)

    for site_name in SITES:
        site_path = f"{selected_year}/{site_name}"
        month_path = f"{site_path}/{selected_month}"

        ensure(selected_year, site_name)
        ensure(site_path, selected_month)

        for subfolder_name in SUBFOLDERS:
            ensure(month_path, subfolder_name)

    result = {
        "year": selected_year,
        "month": selected_month,
        "sites": SITES,
        "created_count": len(created_paths),
        "existing_count": len(existing_paths),
        "created_paths": created_paths,
        "existing_paths": existing_paths,
        "sharepoint_site": sharepoint_site.get("webUrl"),
        "document_library": drive.get("webUrl"),
    }

    frappe.logger("engineering_legals").info(
        "Monthly SharePoint folder check completed: "
        f"{result}"
    )

    return result


def create_current_month_sharepoint_folders() -> None:
    """
    Scheduler entry point.

    Runs every day and ensures that the current year's
    current-month folders exist for Gwab and Klipfontein.
    """

    try:
        result = ensure_month_folders()

        frappe.logger("engineering_legals").info(
            "Scheduled SharePoint monthly folder task completed. "
            f"Year={result['year']}, "
            f"Month={result['month']}, "
            f"Created={result['created_count']}, "
            f"Existing={result['existing_count']}"
        )

    except Exception:
        frappe.log_error(
            title="Engineering Legals SharePoint Folder Error",
            message=frappe.get_traceback(),
        )

        raise
