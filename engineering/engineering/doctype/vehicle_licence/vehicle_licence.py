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


def _current_vehicle_licence(asset):
	"""Same "current licence" definition used everywhere else in fleet
	compliance (engineering.controllers.fleet_compliance): the most
	recently issued non-cancelled record — submitted preferred, falling
	back to a Draft if that's all there is."""
	rows = frappe.get_all(
		"Vehicle Licence",
		filters={"fleet_number": asset, "docstatus": ["<", 2]},
		fields=["name"],
		order_by="issue_date desc, docstatus desc",
		limit_page_length=1,
	)

	return rows[0].name if rows else None


def sync_location_from_asset_movement(doc, method=None):
	"""Hook: engineering.hooks.doc_events["Asset Movement"] (on_submit /
	on_cancel). Asset Movement's own controller already updates
	Asset.location for every Asset in the movement before this runs (it's
	the doctype's own on_submit/on_cancel, which fires first) — this just
	carries that new location across onto the current Vehicle Licence for
	each of those Assets too, so licensing doesn't go stale relative to
	where the vehicle actually is. Only the current record is touched;
	superseded/historical Vehicle Licences keep whatever site they were
	actually issued at."""
	for row in doc.get("assets") or []:
		if not row.asset:
			continue

		licence_name = _current_vehicle_licence(row.asset)

		if not licence_name:
			continue

		current_location = frappe.db.get_value("Asset", row.asset, "location")

		if not current_location:
			continue

		if frappe.db.get_value("Vehicle Licence", licence_name, "site") == current_location:
			continue

		frappe.db.set_value("Vehicle Licence", licence_name, "site", current_location)


class VehicleLicence(Document):
	def validate(self):
		self.set_expiry_date()

	def set_expiry_date(self):
		if self.issue_date:
			self.expiry_date = add_months(self.issue_date, 12)

	def before_submit(self):
		if not self.attach:
			frappe.throw(
				frappe._("You cannot submit this record without attaching the licence document."),
				title=frappe._("Attachment Required"),
			)

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
