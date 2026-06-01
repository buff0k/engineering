from frappe.utils import now_datetime, cstr
# Copyright (c) 2025, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MechanicalServiceReport(Document):

    def validate(self):
        self.lock_saved_comments()
        self.capture_saved_comments()

        # Make sure total_time is always correct on save
        self.set_total_hours()

    def set_total_hours(self):
        if not self.start_time or not self.end_time:
            self.total_time = 0
            return

        start_dt = frappe.utils.get_datetime(self.start_time)
        end_dt = frappe.utils.get_datetime(self.end_time)

        diff_seconds = (end_dt - start_dt).total_seconds()

        if diff_seconds < 0:
            frappe.throw("MSR End Time is BEFORE MSR Start Time. Please fix Start Time and End Time.")

        if diff_seconds > 24 * 60 * 60:
            frappe.throw("MSR Total Time cannot be more than 24 hours. Please fix Start Time and End Time.")

        # Duration field expects seconds
        self.total_time = int(diff_seconds)

    def capture_saved_comments(self):
        comment_fields = [
            {
                "comment_field": "artisan",
                "role": "Artisan",
                "name_field": "artisan_fullname",
                "employee_code_field": "artisan_employee_code",
            },
            {
                "comment_field": "plant_manager_forman1",
                "role": "Plant Manager/Forman",
                "name_field": "plant_man_forman_name",
                "employee_code_field": "plant_manager_forman_code",
            },
        ]

        for item in comment_fields:
            comment = (self.get(item["comment_field"]) or "").strip()

            if not comment:
                continue

            commented_by = (
                self.get(item["name_field"])
                or self.get(item["employee_code_field"])
                or item["role"]
            )

            row = self.append("comment_history", {})
            row.comment_from = item["role"]
            row.comment = comment
            row.commented_by = commented_by
            row.commented_on = now_datetime()

            # Clear the comment field after saving it to history
            self.set(item["comment_field"], "")

    def lock_saved_comments(self):
        if self.is_new():
            return

        old_doc = frappe.get_doc(self.doctype, self.name)

        old_rows = {
            row.name: row
            for row in old_doc.get("comment_history") or []
        }

        current_rows = {
            row.name: row
            for row in self.get("comment_history") or []
            if row.name and not str(row.name).startswith("new-")
        }

        for row_name, old_row in old_rows.items():
            current_row = current_rows.get(row_name)

            if not current_row:
                frappe.throw("Saved comments cannot be deleted.")

            fields_to_check = [
                "comment_from",
                "comment",
                "commented_by",
                "commented_on",
            ]

            for fieldname in fields_to_check:
                if cstr(old_row.get(fieldname)) != cstr(current_row.get(fieldname)):
                    frappe.throw("Saved comments cannot be edited.")


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