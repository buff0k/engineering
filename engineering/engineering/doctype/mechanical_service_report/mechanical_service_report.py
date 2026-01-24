# Copyright (c) 2025, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document



class MechanicalServiceReport(Document):

    def validate(self):
        # Make sure total_time is always correct on save
        self.set_total_hours()
        self.set_total_time_unavailable()

    def set_total_hours(self):
        if not self.start_time or not self.end_time:
            self.total_time = 0
            return

        start_dt = frappe.utils.get_datetime(self.start_time)
        end_dt = frappe.utils.get_datetime(self.end_time)

        diff_seconds = (end_dt - start_dt).total_seconds()
        if diff_seconds < 0:
            frappe.msgprint("MSR End Time is BEFORE MSR Start Time. Please fix start_time/end_time.")
            diff_seconds = 0

        # Duration expects seconds
        self.total_time = int(diff_seconds)

    def set_total_time_unavailable(self):
        if not self.plant_breakdown_number or not self.end_time:
            self.total_time_unavailable = 0
            return

        breakdown_start = frappe.db.get_value(
            "Plant Breakdown or Maintenance",
            self.plant_breakdown_number,
            "breakdown_start_datetime"
        )


        if not breakdown_start:
            self.total_time_unavailable = 0
            return

        end_dt = frappe.utils.get_datetime(self.end_time)
        breakdown_dt = frappe.utils.get_datetime(breakdown_start)

        diff_seconds = (end_dt - breakdown_dt).total_seconds()
        if diff_seconds < 0:
            diff_seconds = 0

        self.total_time_unavailable = int(diff_seconds)



@frappe.whitelist()
def get_last_preuse_hours(asset: str):
    """Return eng_hrs_start of the last Pre-Use Hours document where
    Pre-use Assets.asset_name = given asset.

    Pre-Use Hours is not submittable, so we do NOT filter on docstatus.
    """

    if not asset:
        return None

    result = frappe.db.sql("""
        SELECT pua.eng_hrs_start
        FROM `tabPre-use Assets` pua
        JOIN `tabPre-Use Hours` puh
            ON pua.parent = puh.name
        WHERE pua.asset_name = %s
        ORDER BY puh.shift_date DESC, puh.creation DESC
        LIMIT 1
    """, (asset,), as_dict=True)

    if result:
        return result[0].eng_hrs_start

    return None
