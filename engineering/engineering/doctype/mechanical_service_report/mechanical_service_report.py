# Copyright (c) 2025, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, date, timedelta
from frappe.utils import get_time


class MechanicalServiceReport(Document):

    def validate(self):
        # Make sure total_time is always correct on save
        self.set_total_hours()

    def set_total_hours(self):
        """Calculate total_time from start_time and end_time."""
        if not self.start_time or not self.end_time:
            self.total_time = 0
            return

        # start_time/end_time may come through as strings -> convert safely to datetime.time
        start_t = get_time(self.start_time)
        end_t = get_time(self.end_time)

        start_dt = datetime.combine(date.today(), start_t)
        end_dt = datetime.combine(date.today(), end_t)

        # Handle crossing midnight (e.g. 22:00 to 02:00)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        diff_seconds = (end_dt - start_dt).total_seconds()

        # Duration expects seconds; round to nearest minute to keep it clean
        self.total_time = int(round(diff_seconds / 60.0) * 60)


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
