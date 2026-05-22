import json
import frappe




@frappe.whitelist()
def get_parts_requisition_mobile_items():
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    rows = frappe.db.sql("""
        SELECT
            item.name,
            item.item_name,
            item_default.expense_account AS default_expense_account,
            item.modified
        FROM `tabItem` item
        INNER JOIN `tabItem Default` item_default
            ON item_default.parent = item.name
        WHERE
            item.disabled = 0
            AND IFNULL(item_default.expense_account, '') != ''
        ORDER BY item.name
    """, as_dict=True)

    return rows





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

    if _has_any_role(roles, ["Engineering Manager"]):
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
def sign_off_mechanical_service_report(docname, manager_foreman_signature):
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    roles = frappe.get_roles(user)
    if not _has_any_role(roles, ["Engineering Manager"]):
        frappe.throw("Only Engineering Manager may sign off MSR records", frappe.PermissionError)

    doc = frappe.get_doc("Mechanical Service Report", docname)
    doc.plant_manager_forman = manager_foreman_signature
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "name": doc.name,
    }





@frappe.whitelist()
def get_unsigned_mechanical_daily_worksheets():
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    roles = frappe.get_roles(user)
    if not _has_any_role(roles, ["Engineering Manager"]):
        frappe.throw("Only Engineering Manager may view unsigned Daily Worksheet records", frappe.PermissionError)

    filters = [
        ["supervisor_forman_signature", "in", ["", None]],
    ]

    return frappe.get_all(
        "Mechanical Daily Worksheet",
        filters=filters,
        fields=[
            "name",
            "clock_in_time",
            "clock_out_time",
            "total_hours",
            "total_work_time",
            "mechanic_company_no",
            "mechanic_name_surname",
            "mechanic_signature",
        ],
        order_by="creation desc",
        limit_page_length=200,
    )


@frappe.whitelist()
def sign_off_mechanical_daily_worksheet(docname, supervisor_forman_signature):
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    roles = frappe.get_roles(user)
    if not _has_any_role(roles, ["Engineering Manager"]):
        frappe.throw("Only Engineering Manager may sign off Daily Worksheets", frappe.PermissionError)

    doc = frappe.get_doc("Mechanical Daily Worksheet", docname)
    doc.supervisor_forman_signature = supervisor_forman_signature
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "name": doc.name,
    }







@frappe.whitelist()
def get_unsigned_mechanical_service_reports():
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    roles = frappe.get_roles(user)
    if not _has_any_role(roles, ["Engineering Manager"]):
        frappe.throw("Only Engineering Manager may view unsigned MSR records", frappe.PermissionError)

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
            "job_card_number",
            "site",
            "asset",
            "model",
            "asset_category",
            "plant_manager_forman_code",
            "plant_man_forman_name",
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
            "artisan1",
            "plant_manager_forman",
            "modified",
        ],
        order_by="modified desc",
        limit_page_length=500,
    )