"""Shared server-side security for the supplier tyre survey portal."""

import frappe
from frappe import _


PORTAL_ROLES = {"Supplier", "Supplier Manager"}


def validate_portal_access(redirect_to="/tyre_survey_list"):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = (
            "/login?redirect-to={0}".format(redirect_to)
        )
        raise frappe.Redirect

    if not PORTAL_ROLES.intersection(
        frappe.get_roles(frappe.session.user)
    ):
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    # Resolve this immediately so a portal account without a Supplier
    # assignment cannot reach any supplier data endpoint.
    get_portal_supplier()


def get_portal_supplier(user=None):
    """Return the one Supplier assigned through standard User Permission."""

    user = user or frappe.session.user
    permissions = frappe.get_all(
        "User Permission",
        filters={
            "user": user,
            "allow": "Supplier",
        },
        fields=["for_value", "is_default"],
        order_by="is_default desc, creation asc",
        limit_page_length=0,
    )

    suppliers = []
    for permission in permissions:
        supplier = str(permission.for_value or "").strip()
        if supplier and supplier not in suppliers:
            suppliers.append(supplier)

    if not suppliers:
        frappe.throw(
            _(
                "Your portal account is not linked to a Supplier. "
                "Ask an administrator to add a Supplier User Permission."
            ),
            frappe.PermissionError,
        )

    if len(suppliers) != 1:
        frappe.throw(
            _(
                "Your portal account has more than one Supplier assignment. "
                "Exactly one Supplier User Permission is required."
            ),
            frappe.PermissionError,
        )

    supplier = suppliers[0]
    supplier_record = frappe.db.get_value(
        "Supplier",
        supplier,
        ["name", "disabled"],
        as_dict=True,
    )

    if not supplier_record or supplier_record.disabled:
        frappe.throw(
            _("Your assigned Supplier is missing or disabled."),
            frappe.PermissionError,
        )

    return supplier


def is_supplier_manager(user=None):
    return "Supplier Manager" in frappe.get_roles(
        user or frappe.session.user
    )


def can_access_draft(draft, write=False):
    """Enforce company isolation; surveyors may only change their own drafts."""

    if draft.supplier != get_portal_supplier():
        return False

    if draft.portal_user == frappe.session.user:
        return True

    # Managers may submit company drafts, but cannot silently rewrite another
    # surveyor's captured readings.
    return is_supplier_manager() and not write


def assert_draft_access(draft, write=False):
    if not can_access_draft(draft, write=write):
        message = (
            _("You can only edit your own draft.")
            if write
            else _("You cannot access this supplier record.")
        )
        frappe.throw(message, frappe.PermissionError)

