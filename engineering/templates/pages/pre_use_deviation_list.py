import frappe
from frappe import _
from erpnext.controllers.website_list_for_contact import get_customers_suppliers

ALLOWED_SUPPLIER_SITES = ["GWAB", "Klipfontein"]


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    context.title = "My Pre Use Deviations"

    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/pre_use_deviation_list"
        raise frappe.Redirect

    if "Supplier" not in frappe.get_roles(frappe.session.user):
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    assets = _get_asset_options()

    if not assets:
        context.records = []
        return

    context.records = frappe.get_all(
        "Pre Use Deviation",
        filters={
            "fleet_number": ["in", assets],
            "site": ["in", ALLOWED_SUPPLIER_SITES],
        },
        fields=[
            "name",
            "report_datetime",
            "site",
            "fleet_number",
            "pre_use_no",
            "machine_type",
            "machine_model",
            "action_status",
            "completion_percentage",
            "modified",
        ],
        order_by="modified desc",
        limit_page_length=100,
    )


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
