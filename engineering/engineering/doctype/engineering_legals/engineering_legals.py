import os
from typing import Optional

import frappe
from frappe.model.document import Document

# Drive Team that will own all Engineering Legals links.
# This must match the Drive Team "Title" exactly.
ENGINEERING_DRIVE_TEAM_TITLE = "Engineering team"


class EngineeringLegals(Document):
    """Controller for Engineering Legals DocType."""
    # You can add per-document logic here later if you like
    pass


def on_update(doc: Document, method: Optional[str] = None):
    """
    Hook called whenever an Engineering Legals document is saved.
    1. Moves the attached file into File Manager folder tree:
       Home / Engineering Legals / <Site> / <Sections> / <Fleet Number> /
    2. Creates a link entry in Frappe Drive under:
       Home / Engineering Legals / <Site> / <Sections> /
    """
    try:
        move_engineering_legal_file_to_folder(doc)
        create_drive_link_for_engineering_legals(doc)
    except Exception:
        frappe.log_error(
            title="Engineering Legals file move failed",
            message=frappe.get_traceback(),
        )


def move_engineering_legal_file_to_folder(doc: Document):
    """Move the File linked in doc.attach_paper into the desired folder tree."""

    # If no file attached, nothing to do
    file_url = getattr(doc, "attach_paper", None)
    if not file_url:
        return

    # Build folder path parts
    site = (doc.site or "Unknown Site").strip()
    section = (doc.sections or "Unclassified").strip()
    fleet = (doc.fleet_number or "No Fleet").strip()

    # Final folder path: Home/Engineering Legals/<Site>/<Section>/<Fleet>/
    root_folder = "Home/Engineering Legals"
    # Note: File.folder uses "Home/<child>/<child>" naming, not OS paths.
    # We still use os.path.join only to build a string with "/" separators.
    target_folder_path = os.path.join(root_folder, site, section, fleet)

    # Ensure folder tree exists in File DocType
    target_folder_name = ensure_file_folder_tree(target_folder_path)

    # Find the File record for this attachment
    file_doc = frappe.get_value(
        "File",
        {
            "file_url": file_url,
            "attached_to_doctype": doc.doctype,
            "attached_to_name": doc.name,
        },
        ["name", "folder"],
        as_dict=True,
    )

    if not file_doc:
        # Nothing found; maybe an external URL or already detached
        return

    # Load the File document
    file_doc = frappe.get_doc("File", file_doc.name)

    # 🔥 Force file to be public BEFORE moving it
    if file_doc.is_private:
        file_doc.is_private = 0
        file_doc.save(ignore_permissions=True)

        # Update the document’s attach_paper to point to the PUBLIC url
        if file_doc.file_url.startswith("/private/files/"):
            new_url = file_doc.file_url.replace("/private/files/", "/files/")
            file_doc.file_url = new_url
            file_doc.save(ignore_permissions=True)

            # update the parent document so the UI also shows the public URL
            doc.db_set("attach_paper", new_url)

            frappe.db.commit()


    # If it's already in the correct folder, just return
    if file_doc.folder == target_folder_name:
        return

    # Move the file into the correct folder
    file_doc.folder = target_folder_name
    file_doc.save(ignore_permissions=True)





def ensure_file_folder_tree(path: str) -> str:
    """
    Ensure that a nested folder path like
    'Home/Engineering Legals/GWAB/NDT/EX014'
    exists in the File DocType.

    Returns the File.name of the deepest folder.
    """

    parts = path.split("/")
    if not parts or parts[0] != "Home":
        raise ValueError("Folder path must start with 'Home'")

    parent_name = "Home"

    # Walk through Engineering Legals / Site / Section / Fleet
    for part in parts[1:]:
        if not part:
            continue

        folder_name = f"{parent_name}/{part}"

        existing = frappe.get_value(
            "File",
            {"name": folder_name, "is_folder": 1},
            "name",
        )

        if existing:
            parent_name = existing
            continue

        # Create new folder
        folder_doc = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": part,
                "is_folder": 1,
                "folder": parent_name,
            }
        )
        folder_doc.insert(ignore_permissions=True)
        parent_name = folder_doc.name

    return parent_name


# ----------------------------------------------------------------------
# Frappe Drive integration
# ----------------------------------------------------------------------


def create_drive_link_for_engineering_legals(doc: Document):
    """
    Create / update a Drive File *link* for this Engineering Legals document.

       Drive folder structure:
        Home / Engineering Legals / <Site> / <Section> / <Fleet Number> /


    Inside that folder we create a Drive File with:
        is_group = 0 (file)
        is_link  = 1 (link entity)
        path     = File.file_url (ERPNext file URL)
    """

    # If Drive app is not installed, do nothing
    if "drive" not in frappe.get_installed_apps():
        return

    # No attachment? Nothing to sync.
    file_url = getattr(doc, "attach_paper", None)
    if not file_url:
        return

    # Always work with the PUBLIC url form for Drive
    public_url = file_url.replace("/private/files/", "/files/")

    # Find the File record for this attachment (should already use /files/ after move)
    file_row = frappe.db.get_value(
        "File",
        {"file_url": public_url},
        ["name", "file_name", "file_size", "file_type", "file_url"],
        as_dict=True,
    )
    if not file_row:
        return

    team = _get_default_drive_team()
    home = _get_drive_home_folder(team)

    # Build folder path: Engineering Legals / <Site> / <Section> / <Fleet>
    root_title = "Engineering Legals"
    site_title = (doc.site or "").strip() or "No Site"
    section_title = (doc.sections or "").strip() or "No Section"
    fleet_title = (doc.fleet_number or "").strip() or "No Fleet"

    root_folder = _get_or_create_drive_folder(root_title, home, team)
    site_folder = _get_or_create_drive_folder(site_title, root_folder, team)
    section_folder = _get_or_create_drive_folder(section_title, site_folder, team)
    fleet_folder = _get_or_create_drive_folder(fleet_title, section_folder, team)


    # Avoid creating duplicate links for the same file & folder
    public_url = file_row.file_url.replace("/private/files/", "/files/")

    existing = frappe.db.exists(
        "Drive File",
        {
            "team": team,
            "parent_entity": fleet_folder,
            "is_link": 1,
            "path": public_url,   # always compare using public url
            "is_active": 1,
        },
    )

    if existing:
        return


    # Finally, create the Drive File link (always using PUBLIC url)
    public_url = file_row.file_url.replace("/private/files/", "/files/")

    link_doc = frappe.get_doc(
        {
            "doctype": "Drive File",
            "title": file_row.file_name or "Attachment",
            "team": team,
            "parent_entity": fleet_folder,
            "is_group": 0,   # file
            "is_link": 1,    # link entity
            "is_active": 1,
            "is_private": 0,  # visible to team
            "path": public_url,  # ALWAYS /files/...
            "file_size": file_row.file_size or 0,
            "mime_type": file_row.file_type or "",
        }
    )



    link_doc.insert(ignore_permissions=True)


def _get_default_drive_team() -> str:
    """
    Always use the specific Drive Team configured for Engineering Legals.

    We look it up by Drive Team *Title* so we don't accidentally use
    someone else's personal team.
    """
    team = frappe.db.get_value(
        "Drive Team",
        {"title": ENGINEERING_DRIVE_TEAM_TITLE},
        "name",
    )

    if not team:
        frappe.throw(
            f"Drive Team '{ENGINEERING_DRIVE_TEAM_TITLE}' not found. "
            "Please create it in Drive > Drive Team or update ENGINEERING_DRIVE_TEAM_TITLE "
            "in engineering_legals.py."
        )

    return team



def _get_drive_home_folder(team: str) -> str:
    """
    Get the 'Home' folder for this team in Drive.
    """
    home = frappe.db.get_value(
        "Drive File",
        {
            "title": "Home",
            "is_group": 1,
            "team": team,
            "is_active": 1,
        },
        "name",
    )
    if home:
        return home

    # Fallback: create a Home folder if missing
    home_doc = frappe.get_doc(
        {
            "doctype": "Drive File",
            "title": "Home",
            "parent_entity": None,
            "is_group": 1,
            "is_link": 0,
            "is_active": 1,
            "team": team,
            "owner": frappe.session.user,
            "is_private": 0,
        }
    )
    home_doc.insert(ignore_permissions=True)
    return home_doc.name


def _get_or_create_drive_folder(title: str, parent_entity: Optional[str], team: str) -> str:
    """
    Find a Drive folder (Drive File with is_group=1) by title under parent_entity.
    If missing, create it and return its name.
    """
    existing = frappe.db.get_value(
        "Drive File",
        {
            "title": title,
            "parent_entity": parent_entity,
            "is_group": 1,
            "is_active": 1,
            "team": team,
        },
        "name",
    )
    if existing:
        return existing

    folder = frappe.get_doc(
        {
            "doctype": "Drive File",
            "title": title,
            "parent_entity": parent_entity,
            "is_group": 1,
            "is_link": 0,
            "is_active": 1,
            "team": team,
            "owner": frappe.session.user,
            "is_private": 0,
        }
    )
    folder.insert(ignore_permissions=True)
    return folder.name
