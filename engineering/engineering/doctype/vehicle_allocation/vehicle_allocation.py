# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

from engineering.controllers.fleet_compliance import (
	compute_addendum_status,
	compute_all,
	compute_driver_licence_status,
	compute_overall_status,
	compute_vehicle_licence_status,
	get_expiring_threshold_days,
	render_service_history_html,
)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def public_road_asset_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for the Asset field: only Assets whose Category is listed
	on Fleet Management Settings -> Public Road Asset Categories."""
	from engineering.engineering.doctype.fleet_management_settings.fleet_management_settings import (
		get_public_road_asset_categories,
	)

	categories = get_public_road_asset_categories()

	if not categories:
		return []

	return frappe.db.sql(
		"""
		select name, asset_name
		from `tabAsset`
		where asset_category in %(categories)s
			and (name like %(txt)s or asset_name like %(txt)s)
		order by name
		limit %(start)s, %(page_len)s
		""",
		{
			"categories": categories,
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)


@frappe.whitelist()
def get_overall_statuses(names):
	"""overall_status (and the fields it depends on) is a virtual field, so
	it never comes through the List View's bulk query. The list view JS
	calls this once per page of rows and patches the indicator in
	afterwards, rather than storing/caching the value anywhere."""
	if isinstance(names, str):
		names = frappe.parse_json(names)

	if not names:
		return {}

	threshold_days = get_expiring_threshold_days()

	rows = frappe.get_all(
		"Vehicle Allocation",
		filters={"name": ["in", names]},
		fields=["name", "asset", "driver", "required_licence_type"],
	)

	return {
		row.name: compute_all(row.asset, row.driver, row.required_licence_type, threshold_days)["overall_status"]
		for row in rows
	}


class VehicleAllocation(Document):
	# ------------------------------------------------------------------
	# All compliance fields below are virtual (is_virtual: 1 in the JSON) —
	# they hold no DB column and are recomputed on every read, straight from
	# the actual source doctypes. That is deliberate: this data is dynamic
	# by nature (a licence can expire, be renewed, or be uploaded at any
	# time regardless of this document), so nothing here is ever cached or
	# allowed to go stale between scheduled refreshes.
	#
	# Note: because these are virtual, they are NOT populated by bulk
	# frappe.get_all()/list-view queries — only by loading the full
	# Document (form view, frappe.get_doc). The report/dashboard/
	# notifications call the same underlying engineering.controllers.
	# fleet_compliance functions directly instead, for exactly this reason.
	# ------------------------------------------------------------------
	@property
	def driver_licence_valid_to(self):
		return compute_driver_licence_status(self.driver, self.required_licence_type)[0]

	@property
	def driver_licence_status(self):
		return compute_driver_licence_status(self.driver, self.required_licence_type)[1]

	@property
	def driver_licence_source(self):
		return compute_driver_licence_status(self.driver, self.required_licence_type)[2]

	@property
	def addendum_status(self):
		return compute_addendum_status(self.driver)[0]

	@property
	def addendum_date(self):
		return compute_addendum_status(self.driver)[1]

	@property
	def addendum_url(self):
		return compute_addendum_status(self.driver)[2]

	@property
	def vehicle_licence_valid_to(self):
		return compute_vehicle_licence_status(self.asset)[0]

	@property
	def vehicle_licence_status(self):
		return compute_vehicle_licence_status(self.asset)[1]

	@property
	def vehicle_licence_source(self):
		return compute_vehicle_licence_status(self.asset)[2]

	@property
	def overall_status(self):
		return compute_overall_status(
			self.vehicle_licence_status, self.driver, self.driver_licence_status, self.addendum_status
		)

	@property
	def service_history_html(self):
		return render_service_history_html(self.asset)

	# ------------------------------------------------------------------
	# Allocation-period lifecycle (real, stored fields — these describe
	# this document's own identity/state, not another doctype's data).
	# ------------------------------------------------------------------
	def on_submit(self):
		self.close_previous_open_allocation()

	def close_previous_open_allocation(self):
		"""A newly submitted allocation for an Asset supersedes whichever
		other allocation for that same Asset was still open. valid_to is a
		system-only field — it is never typed in by a user."""
		previous = frappe.get_all(
			"Vehicle Allocation",
			filters={"asset": self.asset, "status": "Current", "docstatus": 1, "name": ["!=", self.name]},
			pluck="name",
		)

		for name in previous:
			frappe.db.set_value(
				"Vehicle Allocation", name, {"status": "Closed", "valid_to": self.valid_from}
			)

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	@frappe.whitelist()
	def close(self):
		"""'Return Vehicle': close this allocation (asset goes back to the
		pool) without creating a new allocation record."""
		if self.docstatus != 1:
			frappe.throw(frappe._("Only a submitted allocation can be returned."))

		if self.status != "Current":
			frappe.throw(frappe._("This allocation is already {0}.").format(self.status))

		self.db_set({"status": "Closed", "valid_to": nowdate()})
