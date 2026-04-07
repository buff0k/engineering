import frappe

MODULE = "Engineering"
PARENT_DTYPE = "Engineering Checklist Register"
CHILD_DTYPE = "Engineering Checklist Register Row"


def make_field(fieldname, label, fieldtype, **kwargs):
    d = {
        "fieldname": fieldname,
        "label": label,
        "fieldtype": fieldtype,
    }
    d.update(kwargs)
    return d


def month_select_options():
    return "\n".join([
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ])


def get_site_field():
    if frappe.db.exists("DocType", "Site"):
        return make_field("site", "Site", "Link", options="Site", reqd=1)
    return make_field("site", "Site", "Data", reqd=1)


def child_fields():
    fields = [
        make_field("fleet_no", "Fleet No", "Data", in_list_view=1, reqd=1, columns=2),
        make_field("machine_type", "Machine Type", "Data", in_list_view=1, columns=2),
        make_field("item_name", "Item Name", "Data", in_list_view=1, columns=2),
        make_field("target", "Target", "Percent", in_list_view=1, default="100", columns=1),
        make_field("checklist_submission", "Checklist Submission", "Percent", in_list_view=1, read_only=1, columns=1),
    ]

    for day in range(1, 32):
        fields.append(make_field(f"d{day}_day", f"{day} Day", "Check", default="0", columns=1))
        fields.append(make_field(f"d{day}_night", f"{day} Night", "Check", default="0", columns=1))

    return fields


def parent_fields():
    return [
        get_site_field(),
        make_field("month", "Month", "Select", options=month_select_options(), reqd=1),
        make_field("year", "Year", "Int", reqd=1),
        make_field("machine_type_filter", "Machine Type Filter", "Data"),
        make_field("rows", "Rows", "Table", options=CHILD_DTYPE, reqd=1),
    ]


def system_manager_permissions(submittable=False):
    perm = {
        "role": "System Manager",
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "print": 1,
        "email": 1,
        "report": 1,
        "export": 1,
        "share": 1,
    }
    if submittable:
        perm.update({
            "submit": 1,            "cancel": 1,
            "amend": 1,
        })
    return [perm]


def create_child_doctype():
    if frappe.db.exists("DocType", CHILD_DTYPE):
        print(f"SKIP: {CHILD_DTYPE} already exists")
        return

    child = frappe.get_doc({
        "doctype": "DocType",
        "name": CHILD_DTYPE,
        "module": MODULE,
        "custom": 0,
        "istable": 1,
        "editable_grid": 1,
        "track_changes": 0,
        "engine": "InnoDB",
        "fields": child_fields(),
        "permissions": system_manager_permissions(submittable=False),
    })
    child.insert(ignore_permissions=True)
    print(f"CREATED: {CHILD_DTYPE}")


def create_parent_doctype():
    if frappe.db.exists("DocType", PARENT_DTYPE):
        print(f"SKIP: {PARENT_DTYPE} already exists")
        return

    parent = frappe.get_doc({
        "doctype": "DocType",
        "name": PARENT_DTYPE,
        "module": MODULE,
        "custom": 0,
        "is_submittable": 0,
        "track_changes": 1,
        "quick_entry": 0,
        "search_fields": "site,month,year",
        "title_field": "site",
        "engine": "InnoDB",
        "fields": parent_fields(),
        "permissions": system_manager_permissions(submittable=False),
    })
    parent.insert(ignore_permissions=True)
    print(f"CREATED: {PARENT_DTYPE}")


def run():
    frappe.flags.in_migrate = True
    create_child_doctype()
    create_parent_doctype()
    frappe.db.commit()
    frappe.clear_cache()
    print("DONE")
