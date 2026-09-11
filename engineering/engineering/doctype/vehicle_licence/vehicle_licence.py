# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, add_months, cint, date_diff, getdate, nowdate

THRESHOLD_FALLBACK_DAYS = 90


def _get_expiring_threshold_days() -> int:
	try:
		days = frappe.db.get_single_value("Fleet Management Settings", "expiring_threshold_days")
	except Exception:
		days = None

	return cint(days) or THRESHOLD_FALLBACK_DAYS


class VehicleLicence(Document):
	def validate(self):
		self.set_expiry_date()

	def set_expiry_date(self):
		if self.issue_date:
			self.expiry_date = add_months(self.issue_date, 12)

	# ------------------------------------------------------------------
	# Days Left / Status are virtual (is_virtual: 1 in the JSON) — they hold
	# no DB column and are recomputed from today() on every read, so they
	# never go stale between edits the way a periodically-refreshed stored
	# field would.
	# ------------------------------------------------------------------
	@property
	def days_left(self):
		if not self.expiry_date:
			return None

		return date_diff(self.expiry_date, nowdate())

	@property
	def status(self):
		if self.docstatus == 2:
			return "Cancelled"

		if self.docstatus == 1 and self.fleet_number and self.issue_date:
			newer_exists = frappe.db.exists(
				"Vehicle Licence",
				{
					"fleet_number": self.fleet_number,
					"docstatus": 1,
					"issue_date": [">", self.issue_date],
					"name": ["!=", self.name],
				},
			)

			if newer_exists:
				return "Superseded"

		if not self.expiry_date:
			return "Active"

		today = getdate(nowdate())
		expiry_date = getdate(self.expiry_date)
		threshold_days = _get_expiring_threshold_days()

		if expiry_date < today:
			return "Expired"

		if expiry_date <= add_days(today, threshold_days):
			return "Expiring"

		return "Active"
