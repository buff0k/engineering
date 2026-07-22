"""Create or update the standard Tyre Management Dashboard Page record."""

import frappe


PAGE_NAME = "tyre-dashboard"


def install():
    if frappe.db.exists("Page", PAGE_NAME):
        page = frappe.get_doc("Page", PAGE_NAME)
    else:
        page = frappe.new_doc("Page")
        page.page_name = PAGE_NAME
        page.name = PAGE_NAME

    page.title = "Tyre Management Dashboard"
    page.module = "Engineering"
    page.standard = "Yes"
    page.system_page = 0
    page.icon = "dashboard"

    if page.is_new():
        page.insert(ignore_permissions=True)
    else:
        page.save(ignore_permissions=True)

    frappe.db.commit()
    frappe.clear_cache()

    return {
        "ok": True,
        "page": PAGE_NAME,
        "route": "/desk/{0}".format(PAGE_NAME),
    }
