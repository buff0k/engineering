import frappe
from frappe import _


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    context.title = "Engineering Legals"

    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in first."))

    if "Supplier" not in frappe.get_roles(frappe.session.user):
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    if frappe.request.method == "POST":
        _handle_post(context)

    context.sections_options = _get_link_options("Engineering Legals Sections")
    context.site_options = _get_recent_site_options()
    context.fleet_options = _get_recent_fleet_options()

    context.form_values = {
        "sections": frappe.form_dict.get("sections") or "",
        "site": frappe.form_dict.get("site") or "",
        "fleet_number": frappe.form_dict.get("fleet_number") or "",
        "vehicle_type": frappe.form_dict.get("vehicle_type") or "",
        "lifting_type": frappe.form_dict.get("lifting_type") or "",
        "attach_paper": frappe.form_dict.get("attach_paper") or "",
        "start_date": frappe.form_dict.get("start_date") or "",
        "expiry_date": frappe.form_dict.get("expiry_date") or "",
    }


def _handle_post(context):
    sections = (frappe.form_dict.get("sections") or "").strip()
    site = (frappe.form_dict.get("site") or "").strip()
    fleet_number = (frappe.form_dict.get("fleet_number") or "").strip()
    vehicle_type = (frappe.form_dict.get("vehicle_type") or "").strip()
    lifting_type = (frappe.form_dict.get("lifting_type") or "").strip()
    attach_paper = (frappe.form_dict.get("attach_paper") or "").strip()
    start_date = (frappe.form_dict.get("start_date") or "").strip()

    if not sections:
        frappe.throw(_("Section is required."))
    if not site:
        frappe.throw(_("Site is required."))
    if not fleet_number:
        frappe.throw(_("Fleet Number is required."))
    if not attach_paper:
        frappe.throw(_("Attach Paper is required."))
    if not start_date:
        frappe.throw(_("Document Start Date is required."))

    file_name = frappe.db.get_value("File", {"file_url": attach_paper}, "name")
    if not file_name:
        frappe.throw(_("Attachment is still uploading. Please wait a few seconds and submit again."))

    doc = frappe.get_doc(
        {
            "doctype": "Engineering Legals supplier Portal Draft",
            "portal_user": frappe.session.user,
            "sections": sections,
            "site": site,
            "fleet_number": fleet_number,
            "vehicle_type": vehicle_type or None,
            "lifting_type": lifting_type or None,
            "attach_paper": attach_paper,
            "start_date": start_date,
            "expiry_date": frappe.form_dict.get("expiry_date") or None,
            "sent_to_erp": 0,
        }
    )

    doc.insert(ignore_permissions=True)

    frappe.local.flags.redirect_location = "/engineering_legals_list"
    raise frappe.Redirect


def _get_link_options(doctype_name):
    return frappe.get_all(
        doctype_name,
        pluck="name",
        order_by="name asc",
        limit_page_length=0,
    )


def _get_asset_options():
    return frappe.get_all(
        "Asset",
        pluck="name",
        order_by="name asc",
        limit_page_length=0,
    )


def _get_recent_site_options():
    rows = frappe.get_all(
        "Engineering Legals",
        fields=["site"],
        filters={"site": ["is", "set"]},
        order_by="modified desc",
        limit_page_length=20,
    )

    seen = []
    for row in rows:
        value = (row.get("site") or "").strip()
        if value and value not in seen:
            seen.append(value)
        if len(seen) == 3:
            break

    return seen


def _get_recent_fleet_options():
    rows = frappe.get_all(
        "Engineering Legals",
        fields=["fleet_number"],
        filters={"fleet_number": ["is", "set"]},
        order_by="modified desc",
        limit_page_length=20,
    )

    seen = []
    for row in rows:
        value = (row.get("fleet_number") or "").strip()
        if value and value not in seen:
            seen.append(value)
        if len(seen) == 3:
            break

    return seen