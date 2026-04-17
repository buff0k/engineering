import json
import frappe


def _get_allowed_locations(user):
    rows = frappe.get_all(
        "User Permission",
        filters={
            "user": user,
            "allow": "Location",
        },
        fields=["for_value"],
    )

    return [
        (row.get("for_value") or "").strip()
        for row in rows
        if (row.get("for_value") or "").strip()
    ]


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
        "allowed_locations": _get_allowed_locations(user),
    }


def _has_any_role(user_roles, allowed_roles):
    user_role_set = set(user_roles or [])
    allowed_role_set = set(allowed_roles or [])
    return bool(user_role_set.intersection(allowed_role_set))




@frappe.whitelist()
def get_unsigned_mechanical_service_reports():
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    allowed_locations = _get_allowed_locations(user)

    filters = [
        ["manager_foreman", "=", ""],
    ]

    if allowed_locations:
        filters.append(["site", "in", allowed_locations])

    return frappe.get_all(
        "Mechanical Service Report",
        filters=filters,
        fields=[
            "name",
            "service_date",
            "reference_number",
            "job_card_number",
            "site",
            "asset",
            "model",
            "asset_category",
            "plant_manager_code",
            "plant_man_name",
            "artisan_employee_code",
            "artisan_fullname",
            "start_time",
            "end_time",
            "total_time",
            "service_breakdown",
            "service_interval",
            "current_hours",
            "description_of_breakdown",
            "description_of_work_done",
            "spares_required_and_comments",
            "mechanic",
            "manager_foreman",
            "modified",
        ],
        order_by="modified desc",
        limit_page_length=500,
    )