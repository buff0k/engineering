# Copyright (c) 2026, Isambane
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RepairLogSheet(Document):
    pass


@frappe.whitelist()
def get_msr_entries_for_asset(plant_no):
    """
    Return all Mechanical Service Report entries for the selected Asset / Plant No.

    Repair Log Sheet field:
        plant_no

    Mechanical Service Report fields used:
        asset
        current_hours
        service_breakdown
        description_of_breakdown
        service_interval
        artisan_fullname
        site
        service_date
    """

    if not plant_no:
        return []

    msr_entries = frappe.get_all(
        "Mechanical Service Report",
        filters={
            "asset": plant_no
        },
        fields=[
            "name",
            "service_date",
            "current_hours",
            "service_breakdown",
            "description_of_breakdown",
            "service_interval",
            "artisan_fullname",
            "site"
        ],
        order_by="service_date desc, creation desc"
    )

    rows = []

    for msr in msr_entries:
        description = msr.description_of_breakdown or ""

        if msr.service_breakdown == "Service" and msr.service_interval:
            description = msr.service_interval

        rows.append({
            "msr": msr.name,
            "service_date": msr.service_date,
            "hours": msr.current_hours,
            "defect": msr.service_breakdown,
            "description": description,
            "rep_by": msr.artisan_fullname,
            "site": msr.site
        })

    return rows