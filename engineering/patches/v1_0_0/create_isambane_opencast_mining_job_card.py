import frappe

PARENT_DTYPE = "Isambane Opencast Mining Job Card"
CHILD_DTYPE = "Isambane Opencast Mining Job Card Item"
MODULE = "Engineering"


def execute():
    create_child_doctype()
    create_parent_doctype()
    frappe.db.commit()


def create_child_doctype():
    if frappe.db.exists("DocType", CHILD_DTYPE):
        return

    doc = frappe.get_doc({
        "doctype": "DocType",
        "name": CHILD_DTYPE,
        "module": MODULE,
        "custom": 0,
        "istable": 1,
        "editable_grid": 1,
        "track_changes": 0,
        "engine": "InnoDB",
        "fields": [
            {
                "fieldname": "part_used",
                "label": "Parts Used",
                "fieldtype": "Data",
                "in_list_view": 1,
                "reqd": 0,
                "columns": 3,
            },
            {
                "fieldname": "qty",
                "label": "Qty",
                "fieldtype": "Float",
                "in_list_view": 1,
                "columns": 1,
                "default": "0",
                "precision": "2",
            },
            {
                "fieldname": "date_start_time",
                "label": "Date/Start Time",
                "fieldtype": "Datetime",
                "in_list_view": 1,
                "columns": 2,
            },
            {
                "fieldname": "date_finish_time",
                "label": "Date/Finish Time",
                "fieldtype": "Datetime",
                "in_list_view": 1,
                "columns": 2,
            },
            {
                "fieldname": "downtime_hrs",
                "label": "Downtime (hrs)",
                "fieldtype": "Float",
                "read_only": 1,
                "in_list_view": 1,
                "columns": 1,
                "precision": "2",
            },
        ],
        "permissions": [],
    })
    doc.insert(ignore_permissions=True)


def create_parent_doctype():
    if frappe.db.exists("DocType", PARENT_DTYPE):
        return

    fields = [
        {"fieldname": "naming_series", "label": "Series", "fieldtype": "Select", "options": "JCM-.YYYY.-", "default": "JCM-.YYYY.-", "hidden": 1},
        {"fieldname": "section_general_information", "label": "1. General Information", "fieldtype": "Section Break"},
        {"fieldname": "job_card_no", "label": "Job Card No.", "fieldtype": "Data", "read_only": 1, "fetch_from": "name", "in_list_view": 1},
        {"fieldname": "date", "label": "Date", "fieldtype": "Date", "default": "Today", "in_list_view": 1},
        {"fieldname": "shift", "label": "Shift", "fieldtype": "Select", "options": "\\nDAY\\nNIGHT", "in_list_view": 1},
        {"fieldname": "priority", "label": "Priority", "fieldtype": "Select", "options": "\\nLow\\nMedium\\nHigh\\nCritical", "in_list_view": 1},
        {"fieldname": "department", "label": "Department", "fieldtype": "Select", "options": "\\nMining Onsite\\nPlot 20\\nPlot 22\\nPlant"},
        {"fieldname": "requested_by", "label": "Requested By", "fieldtype": "Data"},

        {"fieldname": "section_equipment_asset_details", "label": "2. Equipment / Asset Details", "fieldtype": "Section Break"},
        {"fieldname": "site", "label": "Site", "fieldtype": "Data"},
        {"fieldname": "equipment_no", "label": "Equipment No.", "fieldtype": "Data", "in_list_view": 1},
        {"fieldname": "machine_type", "label": "Machine Type", "fieldtype": "Data"},
        {"fieldname": "model", "label": "Model", "fieldtype": "Data"},
        {"fieldname": "hour_meter", "label": "Hour Meter", "fieldtype": "Float", "precision": "2"},
        {"fieldname": "fault_work_type", "label": "Fault / Work Type", "fieldtype": "Select", "options": "\\nBreakdown Repair\\nPreventative Maintenance\\nInspection\\nService\\nTyre Repair\\nElectrical Repair\\nWelding\\nOther"},

        {"fieldname": "section_job_description", "label": "3. Job Description", "fieldtype": "Section Break"},
        {"fieldname": "fault_work_request_reported", "label": "Fault / Work Request Reported", "fieldtype": "Small Text"},

        {"fieldname": "section_parts_times_sign_off", "label": "Parts / Times / Sign-Off", "fieldtype": "Section Break"},
        {"fieldname": "items", "label": "Parts / Times", "fieldtype": "Table", "options": CHILD_DTYPE},

        {"fieldname": "section_work_completion_report", "label": "7. Work Completion Report", "fieldtype": "Section Break"},
        {"fieldname": "work_carried_out", "label": "Work Carried Out", "fieldtype": "Small Text"},
        {"fieldname": "machine_tested", "label": "Machine Tested", "fieldtype": "Select", "options": "\\nYES\\nNO"},
        {"fieldname": "machine_status", "label": "Machine Status", "fieldtype": "Select", "options": "\\nAwaiting Parts\\nAvailable For Service\\nRunning with Observation\\nFurther Repair Required\\nUnsafe to Operate"},
        {"fieldname": "start_of_downtime", "label": "Start of Downtime", "fieldtype": "Datetime"},
        {"fieldname": "end_of_downtime", "label": "End of Downtime", "fieldtype": "Datetime"},
        {"fieldname": "further_repair_required", "label": "Further Repair Required", "fieldtype": "Select", "options": "\\nYES\\nNO"},
        {"fieldname": "unsafe_to_operate", "label": "Unsafe to Operate", "fieldtype": "Select", "options": "\\nYES\\nNO"},
        {"fieldname": "total_downtime_hrs", "label": "Total Downtime (hrs)", "fieldtype": "Float", "read_only": 1, "precision": "2"},

        {"fieldname": "section_sign_off", "label": "Sign-Off", "fieldtype": "Section Break"},
        {"fieldname": "artisan_signature", "label": "Artisan Signature", "fieldtype": "Data"},
        {"fieldname": "supervisor_foreman_signature", "label": "Supervisor/Foreman Signature", "fieldtype": "Data"},
        {"fieldname": "date_closed", "label": "Date Closed", "fieldtype": "Date"},
    ]

    doc = frappe.get_doc({
        "doctype": "DocType",
        "name": PARENT_DTYPE,
        "module": MODULE,
        "custom": 0,
        "is_submittable": 0,
        "track_changes": 1,
        "allow_rename": 1,
        "engine": "InnoDB",
        "autoname": "naming_series:",
        "title_field": "equipment_no",
        "sort_field": "modified",
        "sort_order": "DESC",
        "fields": fields,
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "print": 1, "email": 1, "share": 1, "export": 1},
            {"role": "Maintenance User", "read": 1, "write": 1, "create": 1, "print": 1, "email": 1, "share": 1, "export": 1},
            {"role": "Maintenance Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "print": 1, "email": 1, "share": 1, "export": 1},
        ],
    })
    doc.insert(ignore_permissions=True)
