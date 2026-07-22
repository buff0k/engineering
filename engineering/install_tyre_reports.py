"""Create or update the five standard Tyre Survey Script Report records."""

import frappe


REPORTS = [
    "Tyre Urgency Report",
    "Tyre Replacement Forecast",
    "ADT Six Wheel Status",
    "Tyre Site Performance",
    "Tyre Brand Performance",
]


def install():
    if not frappe.db.exists("Module Def", "Engineering"):
        frappe.throw("The Engineering module does not exist.")

    installed = []

    for report_name in REPORTS:
        if frappe.db.exists("Report", report_name):
            report = frappe.get_doc("Report", report_name)
        else:
            report = frappe.new_doc("Report")
            report.report_name = report_name
            report.name = report_name

        report.ref_doctype = "Tyre Survey"
        report.report_type = "Script Report"
        report.module = "Engineering"
        report.is_standard = "Yes"
        report.disabled = 0
        report.prepared_report = 0
        report.add_total_row = 0
        report.set("roles", [])

        for role_name in ("System Manager", "Engineering Manager"):
            if frappe.db.exists("Role", role_name):
                report.append("roles", {"role": role_name})

        if report.is_new():
            report.insert(ignore_permissions=True)
        else:
            report.save(ignore_permissions=True)

        installed.append(report_name)

    frappe.db.commit()
    frappe.clear_cache()

    return {
        "ok": True,
        "installed_reports": installed,
    }
