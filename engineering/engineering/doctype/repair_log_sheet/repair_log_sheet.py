import frappe
from datetime import datetime
from frappe.utils import get_first_day, get_last_day


@frappe.whitelist()
def get_msr_entries_for_asset(plant_no, month=None):
    if not plant_no:
        return []

    filters = {
        "plant_no": plant_no,
        "docstatus": ["!=", 2]
    }

    if month:
        try:
            month_date = datetime.strptime(month, "%b-%y").date()
        except ValueError:
            frappe.throw("Month must be in format MMM-YY. Example: Jan-26")

        filters["service_date"] = [
            "between",
            [
                get_first_day(month_date),
                get_last_day(month_date)
            ]
        ]

    msr_list = frappe.get_all(
        "Mechanical Service Report",
        filters=filters,
        fields=[
            "name",
            "service_date",
            "hours",
            "defect",
            "description",
            "rep_by",
            "site"
        ],
        order_by="service_date desc"
    )

    entries = []

    for msr in msr_list:
        entries.append({
            "msr": msr.name or "",
            "service_date": msr.service_date or "",
            "hours": msr.hours or 0,
            "defect": msr.defect or "",
            "description": msr.description or "",
            "rep_by": msr.rep_by or "",
            "site": msr.site or ""
        })

    return entries