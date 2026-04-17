import frappe


@frappe.whitelist()
def get_user_context():
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    roles = frappe.get_roles(user)

    allowed_pages = []

    if frappe.has_permission("Mechanical Service Report", "create", user=user):
        allowed_pages.append("mechanical_service_report")

    if frappe.has_permission("Component Replacement Report", "create", user=user):
        allowed_pages.append("component_replacement_report")

    if frappe.has_permission("Mechanical Service Report", "write", user=user):
        allowed_pages.append("msr_signoff")

    if frappe.has_permission("Production Cycle Times", "create", user=user):
        allowed_pages.append("production_cycle_times")

    return {
        "user": user,
        "roles": roles,
        "allowed_pages": allowed_pages,
    }


def _has_any_role(user_roles, allowed_roles):
    user_role_set = set(user_roles or [])
    allowed_role_set = set(allowed_roles or [])
    return bool(user_role_set.intersection(allowed_role_set))