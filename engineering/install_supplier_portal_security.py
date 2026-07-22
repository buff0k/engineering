"""One-time setup helpers for supplier-scoped tyre portal accounts."""

import frappe
from frappe import _


def install():
    """Create the optional manager role. Safe to run more than once."""

    if not frappe.db.exists("Role", "Supplier Manager"):
        frappe.get_doc(
            {
                "doctype": "Role",
                "role_name": "Supplier Manager",
                "desk_access": 0,
            }
        ).insert(ignore_permissions=True)

    frappe.db.commit()
    return {
        "ok": True,
        "role": "Supplier Manager",
        "message": "Use one Supplier User Permission per portal user.",
    }


def audit():
    """Read-only check of portal users and Supplier assignments."""

    users = frappe.db.sql(
        """
        SELECT DISTINCT hr.parent AS user
        FROM `tabHas Role` hr
        WHERE hr.role IN ('Supplier', 'Supplier Manager')
          AND hr.parenttype = 'User'
        ORDER BY hr.parent
        """,
        as_dict=True,
    )
    results = []

    for row in users:
        suppliers = frappe.get_all(
            "User Permission",
            filters={
                "user": row.user,
                "allow": "Supplier",
            },
            pluck="for_value",
            limit_page_length=0,
        )
        suppliers = sorted(set(value for value in suppliers if value))
        results.append(
            {
                "user": row.user,
                "suppliers": suppliers,
                "valid": len(suppliers) == 1,
            }
        )

    return {
        "portal_users": len(results),
        "valid_users": sum(1 for row in results if row["valid"]),
        "needs_attention": [row for row in results if not row["valid"]],
        "users": results,
    }


def assign_user(user, supplier, manager=False):
    """Assign one portal role and one Supplier User Permission safely."""

    if not frappe.db.exists("User", user):
        frappe.throw(_("User {0} does not exist.").format(user))

    if not frappe.db.exists("Supplier", supplier):
        frappe.throw(_("Supplier {0} does not exist.").format(supplier))

    existing = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": "Supplier"},
        pluck="for_value",
        limit_page_length=0,
    )
    other_suppliers = sorted(
        set(value for value in existing if value and value != supplier)
    )

    if other_suppliers:
        frappe.throw(
            _(
                "User {0} is already linked to another Supplier: {1}. "
                "Review that permission manually before continuing."
            ).format(user, ", ".join(other_suppliers))
        )

    if supplier not in existing:
        frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": user,
                "allow": "Supplier",
                "for_value": supplier,
                "is_default": 1,
                "apply_to_all_doctypes": 1,
            }
        ).insert(ignore_permissions=True)

    role = "Supplier Manager" if _as_bool(manager) else "Supplier"
    user_doc = frappe.get_doc("User", user)
    if role not in {row.role for row in user_doc.roles}:
        user_doc.append("roles", {"role": role})
        user_doc.save(ignore_permissions=True)

    frappe.db.commit()
    return {"ok": True, "user": user, "supplier": supplier, "role": role}


def _as_bool(value):
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no"}
    return bool(value)
