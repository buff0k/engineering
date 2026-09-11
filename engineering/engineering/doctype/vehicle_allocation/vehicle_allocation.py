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


@frappe.whitelist()
def export_road_asset_register_xlsx():
	"""XLSX export of every public-road Asset (registered or not), grouped by
	Company — same general shape as the manually-maintained LDV spreadsheet
	this replaces, but Location/Driver/compliance are pulled live from the
	actual Vehicle Allocation records instead of free-typed site codes and
	driver names."""
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
			a.company as company,
			v.name as allocation,
			v.location as location,
			v.driver as driver,
			v.driver_name as driver_name,
			v.required_licence_type as required_licence_type
		from `tabAsset` a
		left join `tabVehicle Allocation` v
			on v.asset = a.name and v.docstatus = 1 and v.status = 'Current'
		where a.asset_category in %(categories)s and a.docstatus < 2
		order by a.company asc, a.name asc
		""",
		{"categories": categories},
		as_dict=True,
	)

	if not rows:
		frappe.throw(frappe._("No public-road Assets found."))

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

	for row in rows:
		row.update(compute_all(row.asset, row.driver, row.required_licence_type, threshold_days))
		lic = licence_by_asset.get(row.asset)
		row["registration_number"] = lic.registration_number if lic else None
		row["chassis"] = lic.chassis if lic else None
		row["engine_number"] = lic.engine_number if lic else None
		row["vin_number"] = lic.vin_number if lic else None

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
		("Driver", 32),
		("Required Licence", 24),
		("Driver Licence Status", 18),
		("Vehicle Licence Status", 18),
		("Addendum Status", 16),
		("Overall Status", 16),
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
			driver_display = f"{row.driver} - {row.driver_name}" if row.driver else ""
			values = [
				i,
				row.asset,
				row.model or row.asset_name,
				row.registration_number,
				row.chassis,
				row.engine_number,
				row.vin_number,
				row.location or "",
				driver_display,
				row.required_licence_type or "",
				row.driver_licence_status,
				row.vehicle_licence_status,
				row.addendum_status,
				row.overall_status,
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
