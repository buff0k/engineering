import frappe


@frappe.whitelist()
def get_user_context():
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    roles = frappe.get_roles(user)

    allowed_pages = []

    if _has_any_role(roles, ["Engineering User", "Engineering Manager", "Fleet Manager", "System Manager"]):
        allowed_pages.append("jobcard")

    if _has_any_role(roles, ["Production Cycle Time User", "Production Cycle Time Manager", "System Manager"]):
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