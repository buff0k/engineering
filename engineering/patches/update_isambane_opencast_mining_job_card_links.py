import frappe

PARENT_DTYPE = "Isambane Opencast Mining Job Card"


def execute():
    if not frappe.db.exists("DocType", PARENT_DTYPE):
        frappe.throw(f"{PARENT_DTYPE} does not exist. Create it first.")

    update_parent_doctype()
    frappe.clear_cache(doctype=PARENT_DTYPE)
    frappe.reload_doctype(PARENT_DTYPE)
    frappe.db.commit()


def update_parent_doctype():
    doc = frappe.get_doc("DocType", PARENT_DTYPE)

    existing = {df.fieldname: df for df in doc.fields}

    wanted_fields = [
        {
            "fieldname": "job_card_no",
            "label": "Job Card No.",
            "fieldtype": "Data",
            "read_only": 0,
            "reqd": 0,
            "fetch_from": "",
            "in_list_view": 1,
            "insert_after": "section_general_information",
        },
        {
            "fieldname": "requested_by",
            "label": "Requested By",
            "fieldtype": "Link",
            "options": "Employee",
            "read_only": 0,
            "insert_after": "department",
        },
        {
            "fieldname": "site",
            "label": "Site",
            "fieldtype": "Link",
            "options": "Location",
            "read_only": 0,
            "insert_after": "section_equipment_asset_details",
        },
        {
            "fieldname": "equipment_no",
            "label": "Equipment No.",
            "fieldtype": "Link",
            "options": "Asset",
            "read_only": 0,
            "in_list_view": 1,
            "insert_after": "site",
        },
        {
            "fieldname": "machine_type",
            "label": "Machine Type",
            "fieldtype": "Data",
            "read_only": 1,
            "insert_after": "equipment_no",
        },
        {
            "fieldname": "model",
            "label": "Model",
            "fieldtype": "Data",
            "read_only": 1,
            "insert_after": "machine_type",
        },
        {
            "fieldname": "shift",
            "label": "Shift",
            "fieldtype": "Select",
            "options": "\\nDay\\nNight",
            "in_list_view": 1,
        },
        {
            "fieldname": "priority",
            "label": "Priority",
            "fieldtype": "Select",
            "options": "\\nLow\\nMedium\\nHigh\\nCritical",
            "in_list_view": 1,
        },
        {
            "fieldname": "department",
            "label": "Department",
            "fieldtype": "Select",
            "options": "\\nMining Onsite\\nPlot 20\\nPLOT 22\\nPLANT",
        },
        {
            "fieldname": "fault_work_type",
            "label": "Fault / Work Type",
            "fieldtype": "Select",
            "options": "\\nBreakdown Repair\\nPreventative Maintenance\\nInspection\\nService\\nTyre Repair\\nElectrical Repair\\nWelding\\nOther",
        },
        {
            "fieldname": "machine_tested",
            "label": "Machine Tested",
            "fieldtype": "Select",
            "options": "\\nYes\\nNo",
        },
        {
            "fieldname": "further_repair_required",
            "label": "Further Repair Required",
            "fieldtype": "Select",
            "options": "\\nYes\\nNo",
        },
        {
            "fieldname": "unsafe_to_operate",
            "label": "Unsafe to Operate",
            "fieldtype": "Select",
            "options": "\\nYes\\nNo",
        },
        {
            "fieldname": "machine_status",
            "label": "Machine Status",
            "fieldtype": "Select",
            "options": "\\nAwaiting Parts\\nAvailable For Service\\nRunning with Observation\\nFurther Repair Required\\nUnsafe to Operate",
        },
        {
            "fieldname": "artisan_name_and_surname",
            "label": "Artisan Name and Surname",
            "fieldtype": "Link",
            "options": "Employee",
            "read_only": 0,
            "insert_after": "section_sign_off",
        },
        {
            "fieldname": "artisan_signature",
            "label": "Artisan Signature",
            "fieldtype": "Data",
            "read_only": 0,
            "insert_after": "artisan_name_and_surname",
        },
        {
            "fieldname": "supervisor_forman_name_and_surname",
            "label": "Supervisor/Forman Name and Surname",
            "fieldtype": "Link",
            "options": "Employee",
            "read_only": 0,
            "insert_after": "artisan_signature",
        },
        {
            "fieldname": "supervisor_foreman_signature",
            "label": "Supervisor/Foreman Signature",
            "fieldtype": "Data",
            "read_only": 0,
            "insert_after": "supervisor_forman_name_and_surname",
        },
    ]

    for field_def in wanted_fields:
        fieldname = field_def["fieldname"]

        if fieldname in existing:
            df = existing[fieldname]
            for key, value in field_def.items():
                setattr(df, key, value)
        else:
            doc.append("fields", field_def)

    fields_to_remove = {
        "selected_item",
        "requested_by_company_number",
        "requested_by_name",
        "requested_by_surname",
        "artisan_name",
        "artisan_surname",
        "supervisor_name",
        "supervisor_surname",
    }

    doc.fields = [df for df in doc.fields if df.fieldname not in fields_to_remove]

    doc.save(ignore_permissions=True)
