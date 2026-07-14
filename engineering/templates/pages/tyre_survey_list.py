import json

import frappe
from frappe import _
from frappe.utils import now
from erpnext.controllers.website_list_for_contact import (
    get_customers_suppliers,
)


TYRE_ITEM_FIELDS = [
    "position",
    "tyre_make",
    "serial_number",
    "brand_number",
    "tyre_size",
    "tread_pattern",
    "star_ply_rating",
    "tra_code",
    "compound_code",
    "overall_diameter",
    "otd",
    "rtd_1",
    "rtd_2",
    "rtd_percent",
    "recommended_pressure",
    "actual_pressure",
    "pressure_variance",
    "condition_notes",
    "required_action",
]


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    context.title = "My Tyre Surveys"

    _validate_portal_access()

    context.records = frappe.get_all(
        "Tyre Survey Supplier Portal Draft",
        filters={
            "portal_user": frappe.session.user,
        },
        fields=[
            "name",
            "site",
            "fleet_number",
            "survey_date",
            "sent_to_erp",
            "erp_document",
            "modified",
        ],
        order_by="modified desc",
        limit_page_length=200,
    )

    for row in context.records:
        row.status = (
            "Submitted"
            if row.sent_to_erp
            else "Draft"
        )


def _validate_portal_access():
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = (
            "/login?redirect-to=/tyre_survey_list"
        )
        raise frappe.Redirect

    if "Supplier" not in frappe.get_roles(
        frappe.session.user
    ):
        frappe.throw(
            _("Not permitted."),
            frappe.PermissionError,
        )


def _get_user_suppliers():
    customers, suppliers = get_customers_suppliers(
        "Request for Quotation Supplier",
        frappe.session.user,
    )

    return suppliers or []


def _validate_supplier_asset_access(asset_name):
    """
    Temporary testing version.

    Allows any supplier-owned asset to be sent without
    checking the supplier linked to the portal user.
    """

    asset = frappe.db.get_value(
        "Asset",
        asset_name,
        [
            "name",
            "asset_owner",
            "supplier",
        ],
        as_dict=True,
    )

    if not asset:
        frappe.throw(
            _("Fleet Number does not exist.")
        )

    if asset.asset_owner != "Supplier":
        frappe.throw(
            _("Only supplier-owned Assets can be used."),
            frappe.PermissionError,
        )

    if not asset.supplier:
        frappe.throw(
            _("The selected Asset has no Supplier assigned.")
        )

    return asset.supplier


def _move_attachment_to_erp(
    file_url,
    document_name,
):
    if not file_url:
        return

    file_name = frappe.db.get_value(
        "File",
        {
            "file_url": file_url,
        },
        "name",
    )

    if not file_name:
        return

    frappe.db.set_value(
        "File",
        file_name,
        {
            "attached_to_doctype": "Tyre Survey",
            "attached_to_name": document_name,
            "attached_to_field":
                "survey_attachment",
        },
        update_modified=False,
    )


@frappe.whitelist(allow_guest=False)
def send_tyre_surveys(names=None):
    _validate_portal_access()

    if names is None:
        names = frappe.form_dict.get("names")

    if isinstance(names, str):
        try:
            names = json.loads(names)
        except (TypeError, ValueError):
            names = [names]

    if not isinstance(names, list):
        names = [names]

    names = [
        str(name).strip()
        for name in names
        if str(name).strip()
    ]

    if not names:
        frappe.throw(
            _("No records selected.")
        )

    sent = []

    for name in names:
        draft = frappe.get_doc(
            "Tyre Survey Supplier Portal Draft",
            name,
        )

        if draft.portal_user != frappe.session.user:
            frappe.throw(
                _("You can only send your own records."),
                frappe.PermissionError,
            )

        if draft.sent_to_erp:
            continue

        supplier = _validate_supplier_asset_access(
            draft.fleet_number
        )

        if not draft.tyres:
            frappe.throw(
                _(
                    "Draft {0} does not contain any tyres."
                ).format(draft.name)
            )

        existing_document = frappe.db.exists(
            "Tyre Survey",
            {
                "supplier": supplier,
                "fleet_number": draft.fleet_number,
                "survey_date": draft.survey_date,
            },
        )

        if existing_document:
            frappe.throw(
                _(
                    "A Tyre Survey already exists for "
                    "{0} on {1}: {2}"
                ).format(
                    draft.fleet_number,
                    draft.survey_date,
                    existing_document,
                )
            )

        erp_doc = frappe.get_doc(
            {
                "doctype": "Tyre Survey",
                "supplier": supplier,
                "site": draft.site,
                "fleet_number":
                    draft.fleet_number,
                "survey_date":
                    draft.survey_date,
                "survey_attachment":
                    draft.survey_attachment,
                "general_remarks":
                    draft.general_remarks,
                "portal_user":
                    frappe.session.user,
            }
        )

        for tyre in draft.tyres:
            erp_doc.append(
                "tyres",
                {
                    fieldname: tyre.get(fieldname)
                    for fieldname in TYRE_ITEM_FIELDS
                },
            )

        erp_doc.insert(ignore_permissions=True)

        _move_attachment_to_erp(
            draft.survey_attachment,
            erp_doc.name,
        )

        draft.db_set(
            "sent_to_erp",
            1,
            update_modified=False,
        )

        draft.db_set(
            "sent_on",
            now(),
            update_modified=False,
        )

        draft.db_set(
            "erp_document",
            erp_doc.name,
            update_modified=False,
        )

        sent.append(
            {
                "draft": draft.name,
                "erp_document": erp_doc.name,
            }
        )

    frappe.db.commit()

    return {
        "ok": True,
        "sent": sent,
    }