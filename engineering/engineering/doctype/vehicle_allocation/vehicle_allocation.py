# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, nowdate

from engineering.controllers.fleet_compliance import (
	apply_draft_allocation_penalty,
	bulk_drivers,
	collect_drivers,
	compute_all,
	get_effective_allocations,
	get_expiring_threshold_days,
	render_addendum_html,
	render_driver_licence_html,
	render_service_history_html,
	render_vehicle_licence_html,
)
from engineering.engineering.doctype.fleet_management_settings.fleet_management_settings import (
	get_location_custodian,
)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def public_road_asset_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for the Asset field on both Vehicle Allocation (asset) and
	Vehicle Licence (fleet_number): only submitted Assets whose Category is
	listed on Fleet Management Settings -> Public Road Asset Categories.
	Submitted-only because a Draft Asset isn't a real in-service vehicle
	yet and a Cancelled one no longer is (same rule the Vehicle Licence
	Expiration page's counts and the road asset register export use)."""
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
			and docstatus = 1
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
		fields=["name", "asset", "required_licence_type"],
	)

	drivers_by_parent = bulk_drivers([row.name for row in rows])

	return {
		row.name: compute_all(
			row.asset,
			[d.driver for d in drivers_by_parent.get(row.name, [])],
			row.required_licence_type,
			threshold_days,
		)["overall_status"]
		for row in rows
	}


@frappe.whitelist()
def preview_compliance(asset=None, required_licence_type=None, drivers=None):
	"""Lets the form recompute every compliance HTML block (plus Overall
	Status) the instant Asset / Drivers / Required Licence Type changes,
	without needing a save + reload first. Takes raw values rather than a
	saved doc name on purpose — the whole point is to preview a combination
	that may not be saved yet (e.g. the user is mid-edit on an existing
	allocation)."""
	if not frappe.has_permission("Vehicle Allocation", "read"):
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)

	if isinstance(drivers, str):
		drivers = frappe.parse_json(drivers)

	drivers = collect_drivers(drivers)

	return {
		"vehicle_licence_compliance_html": render_vehicle_licence_html(asset),
		"driver_licence_compliance_html": render_driver_licence_html(drivers, required_licence_type),
		"company_vehicle_undertaking_html": render_addendum_html(drivers),
		"service_history_html": render_service_history_html(asset),
		"overall_status": compute_all(asset, drivers, required_licence_type)["overall_status"],
	}


def _find_active_conflicts(asset, drivers, exclude_name=None):
	"""Two kinds of overlap worth warning about before this allocation is
	submitted:

	1. "asset" — this Asset is already the subject of another still-open
	   ("Current", submitted) allocation. Submitting THIS one resolves it
	   automatically (close_previous_open_allocation closes the other one).
	2. "employee" — a Driver listed here already drives a DIFFERENT Asset
	   under another still-open allocation. Nothing closes this
	   automatically — a shared vehicle's other allocation is never
	   auto-closed just because one of its several drivers has moved on —
	   so this is a heads-up only, for a human to review.

	Used both by the whitelisted client-facing wrapper and by validate()
	(server-side, so the warning surfaces on every save regardless of what
	the browser's JS did or didn't run)."""
	exclude_name = exclude_name or ""
	drivers = collect_drivers(drivers or [])
	conflicts = []

	if asset:
		for row in frappe.get_all(
			"Vehicle Allocation",
			filters={"asset": asset, "status": "Current", "docstatus": 1, "name": ["!=", exclude_name]},
			fields=["name"],
		):
			conflicts.append({"type": "asset", "allocation": row.name})

	if drivers:
		driver_rows = frappe.get_all(
			"Vehicle Allocation Driver",
			filters={"driver": ["in", drivers], "parenttype": "Vehicle Allocation", "parentfield": "drivers"},
			fields=["driver", "driver_name", "parent"],
		)
		candidate_parents = {r.parent for r in driver_rows} - {exclude_name}

		if candidate_parents:
			open_parents = {
				a.name: a
				for a in frappe.get_all(
					"Vehicle Allocation",
					filters={"name": ["in", list(candidate_parents)], "status": "Current", "docstatus": 1},
					fields=["name", "asset"],
				)
			}

			for row in driver_rows:
				parent = open_parents.get(row.parent)

				if not parent or parent.asset == asset:
					# Not open, or it's this same Asset — already covered by
					# the "asset" conflict above, not a second finding.
					continue

				conflicts.append(
					{
						"type": "employee",
						"driver": row.driver,
						"driver_name": row.driver_name,
						"allocation": row.parent,
						"other_asset": parent.asset,
					}
				)

	return conflicts


@frappe.whitelist()
def check_active_conflicts(asset=None, drivers=None, exclude_name=None):
	"""Client-facing wrapper around _find_active_conflicts — called from the
	form on load and whenever Asset/Drivers change, so the warning shows up
	before the user even attempts to save."""
	if not frappe.has_permission("Vehicle Allocation", "read"):
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)

	if isinstance(drivers, str):
		drivers = frappe.parse_json(drivers)

	return _find_active_conflicts(asset, drivers, exclude_name)


@frappe.whitelist()
def export_road_asset_register_xlsx():
	"""XLSX export of every submitted public-road Asset (registered or not),
	grouped by Company — same general shape as the manually-maintained LDV
	spreadsheet this replaces, but Location/Driver/compliance are pulled
	live from the actual Vehicle Allocation records instead of free-typed
	site codes and driver names. Draft/Cancelled Assets are excluded — same
	rule used everywhere else in fleet compliance.

	A Draft Vehicle Allocation still populates Location/Drivers/etc (it
	shouldn't make the Asset look unregistered just because nobody has
	submitted it yet) — but its Overall Status always reads Non-Compliant
	regardless of how the underlying details look, since the allocation
	itself isn't legally in effect yet. See get_effective_allocations."""
	if not frappe.has_permission("Vehicle Allocation", "read"):
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)

	from engineering.engineering.doctype.fleet_management_settings.fleet_management_settings import (
		get_public_road_asset_categories,
	)

	categories = get_public_road_asset_categories()

	if not categories:
		frappe.throw(frappe._("No Public Road Asset Categories are configured on Fleet Management Settings."))

	rows = frappe.db.sql(
		"""
		select
			a.name as asset,
			a.asset_name as asset_name,
			a.item_name as model,
			a.company as company
		from `tabAsset` a
		where a.asset_category in %(categories)s and a.docstatus = 1
		order by a.company asc, a.name asc
		""",
		{"categories": categories},
		as_dict=True,
	)

	if not rows:
		frappe.throw(frappe._("No public-road Assets found."))

	allocation_by_asset = get_effective_allocations(
		[r.asset for r in rows], fields=["location", "required_licence_type", "comments"]
	)

	for row in rows:
		effective = allocation_by_asset.get(row.asset)
		row["allocation"] = effective.name if effective else None
		row["location"] = effective.location if effective else None
		row["required_licence_type"] = effective.required_licence_type if effective else None
		row["comments"] = effective.comments if effective else None

	# Bulk-fetch the latest Vehicle Licence per Asset for the registration/
	# chassis/engine/VIN detail columns — one query, not N. Unlike compliance
	# *status* (strictly submitted-only, by design), these are just facts
	# about the physical vehicle, so a Draft record still counts here —
	# submitted wins over draft on a tie, otherwise the newest issue_date
	# wins regardless of docstatus.
	licence_by_asset = {}
	for lic in frappe.get_all(
		"Vehicle Licence",
		filters={"fleet_number": ["in", [r.asset for r in rows]], "docstatus": ["<", 2]},
		fields=["fleet_number", "registration_number", "chassis", "engine_number", "vin_number", "docstatus"],
		order_by="issue_date desc, docstatus desc",
	):
		licence_by_asset.setdefault(lic.fleet_number, lic)  # first hit per asset = latest (ordered desc)

	threshold_days = get_expiring_threshold_days()
	drivers_by_allocation = bulk_drivers([r.allocation for r in rows if r.allocation])

	for row in rows:
		driver_rows = drivers_by_allocation.get(row.allocation, [])
		row.update(
			compute_all(
				row.asset,
				[d.driver for d in driver_rows],
				row.required_licence_type,
				threshold_days,
			)
		)

		effective = allocation_by_asset.get(row.asset)
		if effective:
			row["overall_status"] = apply_draft_allocation_penalty(row["overall_status"], effective.docstatus)

		lic = licence_by_asset.get(row.asset)
		row["registration_number"] = lic.registration_number if lic else None
		row["chassis"] = lic.chassis if lic else None
		row["engine_number"] = lic.engine_number if lic else None
		row["vin_number"] = lic.vin_number if lic else None
		row["driver_display"] = ", ".join(
			f"{d.driver} - {d.driver_name}" if d.driver_name else d.driver for d in driver_rows
		)

	return {
		"filename": f"road_asset_register_{nowdate()}.xlsx",
		"content": _rows_to_xlsx_base64(rows),
		"type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
	}


def _sanitize_table_name(label, index):
	"""Excel table (ListObject) names must be unique in the workbook, start
	with a letter, and contain only letters/digits/underscore."""
	cleaned = "".join(ch if ch.isalnum() else "_" for ch in (label or ""))

	if not cleaned or not cleaned[0].isalpha():
		cleaned = f"Company_{cleaned}"

	return f"{cleaned}_{index}"[:255]


def _rows_to_xlsx_base64(rows):
	import base64
	from io import BytesIO

	from openpyxl import Workbook
	from openpyxl.styles import Font, PatternFill
	from openpyxl.worksheet.table import Table, TableStyleInfo

	wb = Workbook()
	ws = wb.active
	ws.title = "Road Asset Register"

	columns = [
		("No", 6),
		("Asset", 14),
		("Model", 32),
		("Registration Number", 18),
		("Chassis", 22),
		("Engine Number", 18),
		("VIN Number", 20),
		("Location", 18),
		("Driver", 44),
		("Required Licence", 24),
		("Driver Licence Status", 18),
		("Vehicle Licence Status", 18),
		("Addendum Status", 16),
		("Overall Status", 16),
		("Comments", 40),
	]

	header_fill = PatternFill(fill_type="solid", fgColor="FFD9EAF7", bgColor="FFD9EAF7")
	company_fill = PatternFill(fill_type="solid", fgColor="FF262A76", bgColor="FF262A76")
	company_font = Font(bold=True, color="FFFFFFFF", size=12)
	header_font = Font(bold=True)

	by_company = {}

	for row in rows:
		by_company.setdefault(row.company or "Unassigned", []).append(row)

	current_row = 1
	last_col_letter = ws.cell(row=1, column=len(columns)).column_letter

	for table_index, company in enumerate(sorted(by_company), start=1):
		company_cell = ws.cell(row=current_row, column=1, value=company)
		company_cell.font = company_font

		for col_idx in range(1, len(columns) + 1):
			ws.cell(row=current_row, column=col_idx).fill = company_fill

		ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=len(columns))
		current_row += 1

		header_row = current_row

		for col_idx, (label, width) in enumerate(columns, start=1):
			cell = ws.cell(row=current_row, column=col_idx, value=label)
			cell.font = header_font
			cell.fill = header_fill
			ws.column_dimensions[cell.column_letter].width = width

		current_row += 1

		for i, row in enumerate(by_company[company], start=1):
			values = [
				i,
				row.asset,
				row.model or row.asset_name,
				row.registration_number,
				row.chassis,
				row.engine_number,
				row.vin_number,
				row.location or "",
				row.driver_display,
				row.required_licence_type or "",
				row.driver_licence_status,
				row.vehicle_licence_status,
				row.addendum_status,
				row.overall_status,
				row.comments or "",
			]

			for col_idx, value in enumerate(values, start=1):
				ws.cell(row=current_row, column=col_idx, value=value)

			current_row += 1

		# A real Excel Table (not a sheet-wide AutoFilter, which only allows
		# one range per sheet) gives this company's header row its own
		# independent filter dropdowns, scoped to just its own rows.
		table = Table(
			displayName=_sanitize_table_name(company, table_index),
			ref=f"A{header_row}:{last_col_letter}{current_row - 1}",
		)
		table.tableStyleInfo = TableStyleInfo(
			name="TableStyleMedium9",
			showRowStripes=True,
			showFirstColumn=False,
			showLastColumn=False,
			showColumnStripes=False,
		)
		ws.add_table(table)

		current_row += 1  # blank spacer row between companies

	out = BytesIO()
	wb.save(out)
	out.seek(0)

	return base64.b64encode(out.read()).decode("utf-8")


class VehicleAllocation(Document):
	# ------------------------------------------------------------------
	# All compliance fields below are virtual (is_virtual: 1 in the JSON) —
	# they hold no DB column and are recomputed on every read, straight from
	# the actual source doctypes. That is deliberate: this data is dynamic
	# by nature (a licence can expire, be renewed, or be uploaded at any
	# time regardless of this document), so nothing here is ever cached or
	# allowed to go stale between scheduled refreshes.
	#
	# Driver Licence / Company Vehicle Undertaking / Vehicle Licence
	# Compliance are HTML fields, not individual Select/Date/Link fields —
	# once a vehicle can have more than one Driver, a single status/valid_to
	# pair per section can't represent it (each driver has their own), so
	# they render a small table instead. Only Overall Status stays a plain
	# Select field, since the list view and reports need one filterable
	# value out of it.
	#
	# Note: because these are virtual, they are NOT populated by bulk
	# frappe.get_all()/list-view queries — only by loading the full
	# Document (form view, frappe.get_doc). The report/dashboard/
	# notifications call the same underlying engineering.controllers.
	# fleet_compliance functions directly instead, for exactly this reason.
	# ------------------------------------------------------------------
	def _drivers(self):
		"""Every Employee listed in the Drivers table, deduped. Empty when
		this is a shared resource allocated to a Location with no driver
		assigned at all."""
		return collect_drivers([row.driver for row in (self.drivers or [])])

	@property
	def driver_licence_compliance_html(self):
		return render_driver_licence_html(self._drivers(), self.required_licence_type)

	@property
	def company_vehicle_undertaking_html(self):
		return render_addendum_html(self._drivers())

	@property
	def vehicle_licence_compliance_html(self):
		return render_vehicle_licence_html(self.asset)

	@property
	def overall_status(self):
		return compute_all(self.asset, self._drivers(), self.required_licence_type)["overall_status"]

	@property
	def service_history_html(self):
		return render_service_history_html(self.asset)

	# ------------------------------------------------------------------
	# Allocation-period lifecycle (real, stored fields — these describe
	# this document's own identity/state, not another doctype's data).
	# ------------------------------------------------------------------
	def validate(self):
		self.warn_about_active_conflicts()

	def warn_about_active_conflicts(self):
		"""Non-blocking heads-up, surfaced on every save (Draft or Submit) —
		the form's own JS runs the same check live on Asset/Drivers change,
		this is the server-side backstop so the warning shows up regardless
		of what the browser did (API/Data Import saves included, though
		nothing displays a msgprint there)."""
		conflicts = _find_active_conflicts(self.asset, self._drivers(), exclude_name=self.name)

		if not conflicts:
			return

		lines = []

		for c in conflicts:
			route = f"/app/vehicle-allocation/{frappe.utils.quote(c['allocation'])}"

			if c["type"] == "asset":
				lines.append(
					frappe._("This Asset is already allocated under {0} — submitting this allocation will close it.").format(
						f"<a href='{route}'>{c['allocation']}</a>"
					)
				)
			else:
				lines.append(
					frappe._(
						"{0} already drives a different Asset ({1}) under {2} — not closed automatically, review manually."
					).format(
						frappe.utils.escape_html(c.get("driver_name") or c["driver"]),
						frappe.utils.escape_html(c["other_asset"]),
						f"<a href='{route}'>{c['allocation']}</a>",
					)
				)

		frappe.msgprint(
			"<br>".join(lines),
			title=frappe._("Active Allocation Conflicts"),
			indicator="orange",
		)

	def before_submit(self):
		"""Signed Vehicle Handover Paperwork is only meaningful once there is
		someone to hand the vehicle to — required at submit time whenever
		one or more Drivers are listed, never required for a shared vehicle
		with no driver assigned. Deliberately not a plain reqd/
		mandatory_depends_on field: that would also block ordinary Draft
		saves while the allocation is still being assembled, one Driver at
		a time."""
		if self._drivers() and not self.handover_paperwork:
			frappe.throw(
				frappe._(
					"You cannot submit this allocation without attaching the signed Vehicle Handover"
					" Paperwork — one or more Drivers are listed above."
				),
				title=frappe._("Attachment Required"),
			)

	def on_submit(self):
		self.close_previous_open_allocation()
		self.sync_asset_custodian_and_location()

	def on_update_after_submit(self):
		"""Fires when an allow_on_submit field changes on an already-
		submitted (Current) allocation — in practice, just Location today.
		Re-run the same reconciliation so moving the vehicle here raises an
		Asset Movement too, not just on the original submit."""
		self.sync_asset_custodian_and_location()

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

	def sync_asset_custodian_and_location(self):
		"""Keep the linked Asset's own Custodian/Location in step with this
		allocation, via a proper Asset Movement (never a silent field
		overwrite — Asset Movement is the audited, standard ERPNext
		mechanism, and other tools already read/rely on it).

		Custodian rule: exactly one Driver -> that Employee is Custodian.
		More than one Driver -> the Location's configured recipient (Fleet
		Management Settings) is Custodian, standing in for "whoever
		manages this shared vehicle at this Location". Zero Drivers -> the
		Asset's existing Custodian is left untouched (a shared-resource
		allocation with nobody named doesn't imply anything about who
		should hold it).

		IMPORTANT: ERPNext's Asset Movement is not a diff — on submit it
		takes the LATEST movement's own target_location/to_employee as the
		Asset's complete new state (see AssetMovement.
		get_latest_location_and_custodian), and unlike location (which is
		only applied if truthy), custodian is applied unconditionally, even
		when blank. So a pure "Transfer" movement that leaves to_employee
		empty silently wipes the Custodian. Every movement created here
		therefore always carries the CURRENT value forward for whichever
		dimension isn't the one actually changing, so each movement is a
		complete, accurate snapshot rather than a partial one.

		Only creates a movement for whichever of Custodian/Location
		actually differs from what the Asset currently records — calling
		this repeatedly (e.g. on every subsequent Location edit) is a
		no-op once things already match."""
		if not self.asset:
			return

		asset = frappe.db.get_value("Asset", self.asset, ["custodian", "location", "company"], as_dict=True)

		if not asset:
			return

		drivers = self._drivers()

		if len(drivers) == 1:
			target_custodian = drivers[0]
		elif len(drivers) == 0:
			target_custodian = asset.custodian  # leave untouched
		else:
			target_custodian = get_location_custodian(self.location) or asset.custodian

		target_location = self.location or asset.location
		current_location = asset.location
		current_custodian = asset.custodian

		if target_location and target_location != current_location:
			self._create_asset_movement(
				purpose="Transfer",
				company=asset.company,
				source_location=current_location,
				target_location=target_location,
				to_employee=current_custodian,  # carry forward — see docstring
			)
			current_location = target_location

		if target_custodian and target_custodian != current_custodian:
			self._create_asset_movement(
				purpose="Issue",
				company=asset.company,
				target_location=current_location,  # carry forward — see docstring
				to_employee=target_custodian,
			)

	def _create_asset_movement(
		self, purpose, company, source_location=None, target_location=None, from_employee=None, to_employee=None
	):
		movement = frappe.new_doc("Asset Movement")
		movement.purpose = purpose
		movement.company = company
		movement.transaction_date = now_datetime()
		movement.reference_doctype = "Vehicle Allocation"
		movement.reference_name = self.name
		movement.append(
			"assets",
			{
				"asset": self.asset,
				"source_location": source_location,
				"target_location": target_location,
				"from_employee": from_employee,
				"to_employee": to_employee,
			},
		)
		movement.insert(ignore_permissions=True)
		movement.submit()

		return movement.name

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		self.cancel_linked_asset_movements()

	def cancel_linked_asset_movements(self):
		"""Any Asset Movement this allocation raised (see
		sync_asset_custodian_and_location) dynamically links back to it via
		reference_doctype/reference_name — Frappe blocks cancelling a
		document that's still linked from elsewhere, so without this a
		Vehicle Allocation that ever changed the Asset's Custodian/Location
		could never be cancelled at all."""
		for name in frappe.get_all(
			"Asset Movement",
			filters={"reference_doctype": "Vehicle Allocation", "reference_name": self.name, "docstatus": 1},
			pluck="name",
		):
			frappe.get_doc("Asset Movement", name).cancel()

	@frappe.whitelist()
	def close(self):
		"""'Return Vehicle': close this allocation (asset goes back to the
		pool) without creating a new allocation record."""
		if self.docstatus != 1:
			frappe.throw(frappe._("Only a submitted allocation can be returned."))

		if self.status != "Current":
			frappe.throw(frappe._("This allocation is already {0}.").format(self.status))

		self.db_set({"status": "Closed", "valid_to": nowdate()})
