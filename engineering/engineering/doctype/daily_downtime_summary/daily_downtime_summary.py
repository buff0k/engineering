# Copyright (c) 2026, Isambane Mining (Pty) Ltd
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DailyDowntimeSummary(Document):
    def validate(self):
        if self.summary_message:
            self.summary_message = self.summary_message.strip()

        signatures = [
            "site_manager",
            "supervisor",
            "engineering_manager_signature",
            "information_officer",
        ]

        all_signed = all(getattr(self, fieldname, None) for fieldname in signatures)

        self.status = "Signed" if all_signed else "Not Signed"