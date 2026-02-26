import frappe
from frappe.utils import nowdate, add_days

TARGET_DOCTYPE = "Isambane sample input"
SOURCE_DOCTYPE = "Component Replacement Report"


def _build_sample_input_values(cr_doc) -> dict:
    return {
        "site": getattr(cr_doc, "site", None),
        "fleet_number": getattr(cr_doc, "fleet_no", None),
        "date_replacement": getattr(cr_doc, "date", None),
        "component_replaced": getattr(cr_doc, "component", None),
    }


def create_from_component_replacement_report(cr_doc, commit: bool = True):
    values = _build_sample_input_values(cr_doc)

    if not values.get("fleet_number") or not values.get("component_replaced"):
        return None

    target_name = f"{values['fleet_number']}-{values['component_replaced']}"

    if frappe.db.exists(TARGET_DOCTYPE, target_name):
        return frappe.get_doc(TARGET_DOCTYPE, target_name)

    d = frappe.get_doc({"doctype": TARGET_DOCTYPE, **values})
    d.insert(ignore_permissions=True)

    if commit:
        frappe.db.commit()

    return d


def component_replacement_report_on_update(doc, method=None):
    try:
        create_from_component_replacement_report(doc, commit=True)
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Isambane sample input: create from Component Replacement Report failed",
        )


def run_daily():
    try:
        yesterday = add_days(nowdate(), -1)
        rows = frappe.get_all(
            SOURCE_DOCTYPE,
            filters={"date": ["between", [yesterday, yesterday]]},
            fields=["name"],
            limit_page_length=5000,
        )

        for r in rows:
            cr_doc = frappe.get_doc(SOURCE_DOCTYPE, r["name"])
            create_from_component_replacement_report(cr_doc, commit=False)

        frappe.db.commit()

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Isambane sample input: daily run failed")


from typing import Optional

@frappe.whitelist(allow_guest=True)
def api_isambane_sample_input(
    site: Optional[str] = None,
    limit: int = 200,
    since: Optional[str] = None,   # "YYYY-MM-DD"
):
    """
    Public endpoint (share with Henco):
    /api/method/engineering.controllers.isambane_sample_input.api_isambane_sample_input?site=Gwab&limit=200&since=2026-02-01
    """
    try:
        limit = int(limit or 200)
    except Exception:
        limit = 200

    limit = min(max(limit, 1), 1000)

    filters = {}
    if site:
        filters["site"] = site
    if since:
        filters["date_replacement"] = [">=", since]

    rows = frappe.get_all(
        TARGET_DOCTYPE,
        filters=filters,
        fields=[
            "name",
            "site",
            "fleet_number",
            "date_replacement",
            "component_replaced",
            "modified",
        ],
        order_by="modified desc",
        limit_page_length=limit,
        ignore_permissions=True,  # required for allow_guest=True
    )

    return {
        "doctype": TARGET_DOCTYPE,
        "count": len(rows),
        "filters": {"site": site, "since": since, "limit": limit},
        "data": rows,
    }