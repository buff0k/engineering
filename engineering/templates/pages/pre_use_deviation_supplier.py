import frappe
from frappe import _
from erpnext.controllers.website_list_for_contact import get_customers_suppliers

ALLOWED_SUPPLIER_SITES = ["GWAB", "Klipfontein"]
ACTION_STATUS_OPTIONS = ["Open", "Closed", "Cancelled"]
OPERATING_STATUS_OPTIONS = [
    "Off Site",
    "Parts Order",
    "Pending Incident report",
    "Go But 48 Hours",
    "Go But Plan ASP (WEEK)",
    "Working",
    "Repair within 24 hours",
    "Repair within 1 week",
    "Don't operate machine",
]


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    context.title = "Pre Use Deviation"

    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/pre_use_deviation_supplier"
        raise frappe.Redirect

    if "Supplier" not in frappe.get_roles(frappe.session.user):
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    if frappe.request.method == "POST":
        _handle_post()

    doc = _get_doc_from_query()

    context.site_options = ALLOWED_SUPPLIER_SITES
    context.asset_options = _get_asset_options()
    context.asset_details = _get_asset_details(context.asset_options)
    context.action_status_options = ACTION_STATUS_OPTIONS
    context.operating_status_options = OPERATING_STATUS_OPTIONS

    context.form_values = {
        "name": doc.name if doc else "",
        "report_datetime": _format_datetime_for_input(doc.report_datetime) if doc else frappe.utils.now_datetime().strftime("%Y-%m-%dT%H:%M"),
        "site": doc.site if doc else "",
        "fleet_number": doc.fleet_number if doc else "",
        "pre_use_no": doc.pre_use_no if doc else "",
        "machine_type": doc.machine_type if doc else "",
        "machine_model": doc.machine_model if doc else "",
        "operating_status": doc.operating_status if doc else "",
        "deviation_details": doc.deviation_details if doc else "",
        "reported_by_coy_number": doc.reported_by_coy_number if doc else "",
        "reported_by_name_and_surname": doc.reported_by_name_and_surname if doc else frappe.session.user,
        "resolution_summary": doc.resolution_summary if doc else "",
        "action_date_and_time": _format_datetime_for_input(doc.action_date_and_time) if doc and doc.action_date_and_time else "",
        "actioned_by_coy_number": doc.actioned_by_coy_number if doc else "",
        "actioned_by_name_and_surname": doc.actioned_by_name_and_surname if doc else "",
        "job_card_number": doc.job_card_number if doc else "",
        "action_status": doc.action_status if doc else "Open",
        "completion_percentage": doc.completion_percentage if doc else 0,
    }


def _handle_post():
    name = (frappe.form_dict.get("name") or "").strip()
    site = (frappe.form_dict.get("site") or "").strip()
    fleet_number = (frappe.form_dict.get("fleet_number") or "").strip()
    action_status = (frappe.form_dict.get("action_status") or "Open").strip()
    operating_status = (frappe.form_dict.get("operating_status") or "").strip()
    completion_percentage = int(frappe.form_dict.get("completion_percentage") or 0)

    if not site:
        frappe.throw(_("Site is required."))
    if not fleet_number:
        frappe.throw(_("Fleet Number is required."))
    if action_status not in ACTION_STATUS_OPTIONS:
        frappe.throw(_("Invalid action status."))

    if operating_status and operating_status not in OPERATING_STATUS_OPTIONS:
        frappe.throw(_("Invalid operating status."))

    if completion_percentage < 0 or completion_percentage > 100:
        frappe.throw(_("Completion Percentage must be between 0 and 100."))

    _validate_site(site)
    _validate_asset(fleet_number)

    if name:
        doc = frappe.get_doc("Pre Use Deviation", name)
        _validate_doc_access(doc)
    else:
        doc = frappe.new_doc("Pre Use Deviation")
        doc.naming_series = "PUD-.YYYY.-"

    doc.report_datetime = _parse_datetime(frappe.form_dict.get("report_datetime")) or frappe.utils.now_datetime()
    doc.site = site
    doc.fleet_number = fleet_number
    doc.pre_use_no = int(frappe.form_dict.get("pre_use_no") or 0)
    doc.machine_type = frappe.form_dict.get("machine_type") or None
    doc.machine_model = frappe.form_dict.get("machine_model") or None
    doc.operating_status = frappe.form_dict.get("operating_status") or None
    doc.deviation_details = frappe.form_dict.get("deviation_details") or None
    doc.reported_by_coy_number = frappe.form_dict.get("reported_by_coy_number") or None
    doc.reported_by_name_and_surname = frappe.form_dict.get("reported_by_name_and_surname") or frappe.session.user
    doc.resolution_summary = frappe.form_dict.get("resolution_summary") or None
    doc.action_date_and_time = _parse_datetime(frappe.form_dict.get("action_date_and_time"))
    doc.actioned_by_coy_number = frappe.form_dict.get("actioned_by_coy_number") or None
    doc.actioned_by_name_and_surname = frappe.form_dict.get("actioned_by_name_and_surname") or None
    doc.job_card_number = frappe.form_dict.get("job_card_number") or None
    doc.action_status = action_status
    doc.completion_percentage = completion_percentage

    if name:
        doc.save(ignore_permissions=True)
    else:
        doc.insert(ignore_permissions=True)

    frappe.local.flags.redirect_location = "/pre_use_deviation_list"
    raise frappe.Redirect


def _parse_datetime(value):
    value = (value or "").strip()
    if not value:
        return None
    return frappe.utils.get_datetime(value.replace("T", " "))


def _format_datetime_for_input(value):
    if not value:
        return ""
    return frappe.utils.get_datetime(value).strftime("%Y-%m-%dT%H:%M")


def _get_doc_from_query():
    name = (frappe.form_dict.get("name") or "").strip()
    if not name:
        return None

    doc = frappe.get_doc("Pre Use Deviation", name)
    _validate_doc_access(doc)
    return doc


def _get_user_suppliers():
    suppliers = []

    try:
        customers, rfq_suppliers = get_customers_suppliers(
            "Request for Quotation Supplier",
            frappe.session.user,
        )
        suppliers.extend(rfq_suppliers or [])
    except Exception:
        pass

    contact_names = frappe.db.sql_list(
        """
        SELECT DISTINCT c.name
        FROM `tabContact` c
        LEFT JOIN `tabContact Email` ce ON ce.parent = c.name
        WHERE c.email_id = %(user)s
           OR ce.email_id = %(user)s
        """,
        {"user": frappe.session.user},
    )

    if contact_names:
        linked_suppliers = frappe.db.sql_list(
            """
            SELECT DISTINCT link_name
            FROM `tabDynamic Link`
            WHERE parenttype = 'Contact'
              AND parent IN %(contacts)s
              AND link_doctype = 'Supplier'
            """,
            {"contacts": tuple(contact_names)},
        )
        suppliers.extend(linked_suppliers or [])

    return sorted(set([s for s in suppliers if s]))


def _get_asset_options():
    suppliers = _get_user_suppliers()
    if not suppliers:
        return []

    return frappe.get_all(
        "Asset",
        filters={
            "asset_owner": "Supplier",
            "supplier": ["in", suppliers],
        },
        pluck="name",
        order_by="name asc",
        limit_page_length=0,
    )




def _get_asset_details(asset_names):
    if not asset_names:
        return {}

    available_columns = set(frappe.db.sql_list("SHOW COLUMNS FROM `tabAsset`"))
    wanted_fields = ["name"]

    for field in ["asset_category", "item_code", "asset_name"]:
        if field in available_columns:
            wanted_fields.append(field)

    rows = frappe.get_all(
        "Asset",
        filters={"name": ["in", asset_names]},
        fields=wanted_fields,
        limit_page_length=0,
    )

    details = {}
    for row in rows:
        details[row.name] = {
            "machine_type": row.get("asset_category") or "",
            "machine_model": row.get("item_code") or row.get("asset_name") or "",
        }

    return details


def _validate_site(site):
    if site not in ALLOWED_SUPPLIER_SITES:
        frappe.throw(_("You can only create records for GWAB or Klipfontein."), frappe.PermissionError)


def _validate_asset(asset):
    suppliers = _get_user_suppliers()
    if not suppliers:
        frappe.throw(_("Your user is not linked to a Supplier."))

    if not frappe.db.exists(
        "Asset",
        {
            "name": asset,
            "asset_owner": "Supplier",
            "supplier": ["in", suppliers],
        },
    ):
        frappe.throw(_("This asset is not linked to your supplier access."), frappe.PermissionError)


def _validate_doc_access(doc):
    _validate_site(doc.site)
    _validate_asset(doc.fleet_number)
