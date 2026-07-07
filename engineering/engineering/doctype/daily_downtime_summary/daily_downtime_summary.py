# Copyright (c) 2026, Isambane Mining (Pty) Ltd
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DailyDowntimeSummary(Document):
    def validate(self):
        if self.summary_message:
            self.summary_message = self.summary_message.strip()
