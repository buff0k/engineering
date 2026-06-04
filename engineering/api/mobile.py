import json
import frappe





@frappe.whitelist()
def get_parts_requisition_item_groups(asset_category=None):
    matched_categories = {
        "ADT",
        "Dozer",
        "Excavator",
        "Rollback",
        "Water pump",
        "Grader",
        "TLB",
        "Water Bowser",
        "Service Truck",
        "Diesel Bowsers",
        "LDV",
        "Mobile Screen",
        "Mobile Crusher",
        "Loader",
        "GHT",
        "Vechiles",
        "Compressors",
        "Drills",
    }

    if asset_category and asset_category in matched_categories:
        return frappe.get_all(
            "Item Group",
            filters=[["name", "like", f"%{asset_category}%"]],
            fields=["name", "item_group_name"],
            order_by="name",
            limit_page_length=100,
        )

    return frappe.get_all(
        "Item Group",
        filters={"disabled": 0},
        fields=["name", "item_group_name"],
        order_by="name",
        limit_page_length=100,
    )


@frappe.whitelist()
def get_parts_requisition_items_by_group(item_group=None):
    if not item_group:
        return []

    return frappe.get_all(
        "Item",
        filters={
            "item_group": item_group,
            "disabled": 0,
        },
        fields=[
            "name",
            "item_name",
            "item_group",
            "modified",
        ],
        order_by="name",
        limit_page_length=500,
    )


@frappe.whitelist()
def get_parts_requisition_asset_details(asset_name=None):
    if not asset_name:
        return {
            "asset_category": "",
            "plant_make": "",
            "model": "",
            "vin_no": "",
        }

    asset = frappe.get_doc("Asset", asset_name)
    item_code = asset.item_code or ""
    parts = item_code.strip().split()

    if len(parts) <= 1:
        plant_make = item_code
        model = item_code
    else:
        plant_make = parts[-1]
        model = " ".join(parts[:-1])

    return {
        "asset_category": asset.asset_category or "",
        "plant_make": plant_make or "",
        "model": model or "",
        "vin_no": (
            getattr(asset, "vin_no", None)
            or getattr(asset, "serial_no", None)
            or getattr(asset, "chassis_no", None)
            or getattr(asset, "custom_vin_no", None)
            or ""
        ),
    }





@frappe.whitelist()
def get_parts_requisition_mobile_items():
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    rows = frappe.db.sql("""
        SELECT
            item.name,
            item.item_name,
            item.item_group AS default_expense_account,
            item.modified
        FROM `tabItem` item
        WHERE
            item.disabled = 0
            AND IFNULL(item.item_group, '') != ''
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



def _get_allowed_site_codes(user):
    allowed_locations = _get_allowed_locations(user)

    if not allowed_locations:
        return []

    return frappe.get_all(
        "Site Code",
        filters={"location": ["in", allowed_locations]},
        pluck="name",
    )




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

    if _has_any_role(roles, ["Engineering Manager", "Engineering Plant Manager"]):
        allowed_pages.append("msr_signoff")

    if frappe.has_permission("Production Cycle Times", "create", user=user):
        allowed_pages.append("production_cycle_times")

    if _has_any_role(roles, ["Parts Driver"]):
        allowed_pages = ["travel_log_sheet"]

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

def _require_parts_driver(user):
    roles = frappe.get_roles(user)

    if not _has_any_role(roles, ["Parts Driver", "System Manager"]):
        frappe.throw("Only Parts Driver may use Travel Log Sheet", frappe.PermissionError)


@frappe.whitelist()
def get_last_travel_log_odo(vehicle_registration=None):
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    _require_parts_driver(user)

    if not vehicle_registration:
        return {
            "odo_meter_out": None,
        }

    rows = frappe.get_all(
        "Travel Log Sheet",
        filters={
            "vehicle_registration": vehicle_registration,
        },
        fields=[
            "name",
            "odo_meter_in",
            "date",
            "creation",
        ],
        order_by="date desc, creation desc",
        limit_page_length=1,
    )

    if not rows:
        return {
            "odo_meter_out": None,
        }

    return {
        "odo_meter_out": rows[0].odo_meter_in,
        "previous_travel_log": rows[0].name,
    }


@frappe.whitelist()
def create_travel_log_sheet(data):
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    _require_parts_driver(user)

    if isinstance(data, str):
        data = json.loads(data)

    required_fields = [
        "incurred_by",
        "vehicle_registration",
        "date",
        "odo_meter_out",
        "odo_meter_in",
        "trip",
    ]

    for field in required_fields:
        if data.get(field) in [None, ""]:
            frappe.throw(f"{field} is required")

    odo_meter_out = int(data.get("odo_meter_out") or 0)
    odo_meter_in = int(data.get("odo_meter_in") or 0)

    if odo_meter_in < odo_meter_out:
        frappe.throw("ODO Meter In cannot be less than ODO Meter Out")

    doc = frappe.get_doc({
        "doctype": "Travel Log Sheet",
        "incurred_by": data.get("incurred_by"),
        "vehicle_registration": data.get("vehicle_registration"),
        "date": data.get("date"),
        "odo_meter_out": odo_meter_out,
        "odo_meter_in": odo_meter_in,
        "litres": int(data.get("litres") or 0),
        "trip": data.get("trip"),
    })

    doc.insert(ignore_permissions=False)
    frappe.db.commit()

    return {
        "name": doc.name,
    }

@frappe.whitelist()
def get_mobile_employee_lookup(modified_after=None):
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    if not frappe.has_permission("Employee", "select", user=user):
        frappe.throw("You may not select Employee records", frappe.PermissionError)

    filters = {}
    if modified_after:
        filters["modified"] = [">", modified_after]

    return frappe.get_all(
        "Employee",
        filters=filters,
        fields=[
            "name",
            "employee_name",
            "modified",
        ],
        order_by="name asc",
        limit_page_length=5000,
        ignore_permissions=True,
    )

@frappe.whitelist()
def get_mobile_supplier_lookup(modified_after=None):
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    filters = {}
    if modified_after:
        filters["modified"] = [">", modified_after]

    return frappe.get_all(
        "Supplier",
        filters=filters,
        fields=[
            "name",
            "supplier_name",
            "modified",
        ],
        order_by="name asc",
        limit_page_length=5000,
        ignore_permissions=True,
    )

@frappe.whitelist()
def sign_off_mechanical_service_report(docname, manager_foreman_signature):
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    roles = frappe.get_roles(user)
    if not _has_any_role(roles, ["Engineering Manager", "Engineering Plant Manager"]):
        frappe.throw("Only Engineering Manager or Engineering Plant Manager may sign off MSR records", frappe.PermissionError)

    frappe.db.set_value(
        "Mechanical Service Report",
        docname,
        "plant_manager_forman",
        manager_foreman_signature,
        update_modified=True,
    )
    frappe.db.commit()

    return {
        "name": docname,
    }


@frappe.whitelist()
def get_unsigned_parts_requisition_forms():
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    roles = frappe.get_roles(user)
    if not _has_any_role(roles, ["Engineering Manager", "Engineering Plant Manager"]):
        frappe.throw("Only Engineering Manager or Engineering Plant Manager may view unsigned PR records", frappe.PermissionError)

    allowed_site_codes = _get_allowed_site_codes(user)

    filters = [
        ["mechanic_signature", "!=", ""],
        ["forman_supervisor_sign", "=", ""],
    ]

    if allowed_site_codes:
        filters.append(["site", "in", allowed_site_codes])

    return frappe.get_all(
        "Parts Requisition",
        filters=filters,
        fields=[
            "name",
            "date111",
            "requested_by_employee_number",
            "mechanic_name_and_surname",
            "plant_no",
            "plant_make",
            "model",
            "vin_no",
            "smr",
            "site",
            "forman_supervisor_employee_number",
            "formansupervisor_name_and_surname",
            "date",
            "mechanic_signature",
            "forman_supervisor_sign",
            "modified",
        ],
        order_by="modified desc",
        limit_page_length=200,
    )


@frappe.whitelist()
def sign_off_parts_requisition_form(docname, supervisor_forman_signature, sign_date=None):
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    roles = frappe.get_roles(user)
    if not _has_any_role(roles, ["Engineering Manager", "Engineering Plant Manager"]):
        frappe.throw("Only Engineering Manager or Engineering Plant Manager may sign off PR records", frappe.PermissionError)

    allowed_site_codes = _get_allowed_site_codes(user)
    doc_site = frappe.db.get_value("Parts Requisition", docname, "site")

    if allowed_site_codes and doc_site not in allowed_site_codes:
        frappe.throw("You may only sign off PR records for your allowed site.", frappe.PermissionError)

    frappe.db.set_value(
        "Parts Requisition",
        docname,
        {
            "forman_supervisor_sign": supervisor_forman_signature,
            "date": sign_date,
        },
        update_modified=True,
    )
    frappe.db.commit()

    return {
        "name": docname,
    }


@frappe.whitelist()
def get_unsigned_mechanical_daily_worksheets():
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    roles = frappe.get_roles(user)
    if not _has_any_role(roles, ["Engineering Manager", "Engineering Plant Manager"]):
        frappe.throw("Only Engineering Manager or Engineering Plant Manager may view unsigned Daily Worksheet records", frappe.PermissionError)

    allowed_locations = _get_allowed_locations(user)

    filters = [
        ["forman_supervisor_signature", "in", ["", None]],
    ]

    names = []

    if allowed_locations:
        work_detail_parents = frappe.get_all(
            "Mechanical Daily Worksheet Detail",
            filters={"site": ["in", allowed_locations]},
            pluck="parent",
        )

        non_msr_parents = frappe.get_all(
            "Non MSR Work",
            filters={"site": ["in", allowed_locations]},
            pluck="parent",
        )

        names = list(set(work_detail_parents + non_msr_parents))

        if not names:
            return []

        filters.append(["name", "in", names])

    return frappe.get_all(
        "Mechanical Daily Worksheet",
        filters=filters,
        fields=[
            "name",
            "clock_in_time",
            "clock_out_time",
            "total_hours",
            "total_work_time",
            "total_non_msr_time",
            "sum_total",
            "total_unallocated",
            "date",
            "mechanic_employee_no",
            "mechanic_name_surname",
            "mechanic_signature",
            "forman_supervisor_employee_no",
            "forman_supervisor_name_surname",
            "modified",            
        ],
        order_by="creation desc",
        limit_page_length=200,
    )


@frappe.whitelist()
def sign_off_mechanical_daily_worksheet(docname, forman_supervisor_signature=None, supervisor_forman_signature=None):
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Not logged in")

    roles = frappe.get_roles(user)
    if not _has_any_role(roles, ["Engineering Manager", "Engineering Plant Manager"]):
        frappe.throw("Only Engineering Manager or Engineering Plant Manager may sign off Daily Worksheets", frappe.PermissionError)

    doc = frappe.get_doc("Mechanical Daily Worksheet", docname)
    doc.forman_supervisor_signature = forman_supervisor_signature or supervisor_forman_signature
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
    if not _has_any_role(roles, ["Engineering Manager", "Engineering Plant Manager"]):
        frappe.throw("Only Engineering Manager or Engineering Plant Manager may view unsigned MSR records", frappe.PermissionError)

    allowed_locations = _get_allowed_locations(user)

    filters = [
        ["plant_manager_forman", "=", ""],
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