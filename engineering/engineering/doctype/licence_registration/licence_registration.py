# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_months, date_diff


class LicenceRegistration(Document):
	def validate(self):
		self.set_expiry_date()
		self.set_days_left()

	def set_expiry_date(self):
		if self.issue_date:
			self.expiry_date = add_months(self.issue_date, 12)

	def set_days_left(self):
		if self.issue_date and self.expiry_date:
			self.days_left = date_diff(self.expiry_date, self.issue_date)
