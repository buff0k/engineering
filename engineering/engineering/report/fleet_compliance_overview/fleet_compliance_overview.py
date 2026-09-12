# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe

from engineering.controllers.fleet_compliance import bulk_drivers, compute_all, get_expiring_threshold_days
from engineering.engineering.doctype.fleet_management_settings.fleet_management_settings import (
	get_public_road_asset_categories,
)


def execute(filters=None):
	filters = filters or {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{"fieldname": "asset", "label": "Asset", "fieldtype": "Link", "options": "Asset", "width": 120},
		{"fieldname": "asset_name", "label": "Asset Name", "fieldtype": "Data", "width": 140},
		{"fieldname": "asset_category", "label": "Category", "fieldtype": "Link", "options": "Asset Category", "width": 100},
		{"fieldname": "registered", "label": "Registered", "fieldtype": "Data", "width": 90},
		{"fieldname": "allocation", "label": "Allocation", "fieldtype": "Link", "options": "Vehicle Allocation", "width": 160},
		{"fieldname": "location", "label": "Location", "fieldtype": "Link", "options": "Location", "width": 120},
		{"fieldname": "drivers", "label": "Drivers", "fieldtype": "Data", "width": 220},
		{"fieldname": "driver_licence_status", "label": "Driver Licence", "fieldtype": "Data", "width": 110},
		{"fieldname": "driver_licence_valid_to", "label": "Driver Licence Valid To", "fieldtype": "Date", "width": 140},
		{"fieldname": "addendum_status", "label": "Addendum", "fieldtype": "Data", "width": 100},
		{"fieldname": "vehicle_licence_status", "label": "Vehicle Licence", "fieldtype": "Data", "width": 110},
		{"fieldname": "vehicle_licence_valid_to", "label": "Vehicle Licence Valid To", "fieldtype": "Date", "width": 140},
		{"fieldname": "overall_status", "label": "Overall Status", "fieldtype": "Data", "width": 130},
	]


def get_data(filters):
	categories = get_public_road_asset_categories()

	if not categories:
		return []

	conditions, params = _build_conditions(filters, categories)
	threshold_days = get_expiring_threshold_days()

	rows = frappe.db.sql(
		f"""
		select
			a.name as asset,
			a.asset_name as asset_name,
			a.asset_category as asset_category,
			v.name as allocation,
			v.location as location,
			v.required_licence_type as required_licence_type
		from `tabAsset` a
		left join `tabVehicle Allocation` v
			on v.asset = a.name and v.docstatus = 1 and v.status = 'Current'
		where {conditions}
		order by a.name asc
		""",
		params,
		as_dict=True,
	)

	# Compliance is computed live per row (never read from a stored/cached
	# column — see engineering.controllers.fleet_compliance).
	drivers_by_allocation = bulk_drivers([row["allocation"] for row in rows if row.get("allocation")])

	for row in rows:
		row["registered"] = "Yes" if row.get("allocation") else "No"
		driver_rows = drivers_by_allocation.get(row.get("allocation"), [])
		compliance = compute_all(
			row["asset"],
			[d.driver for d in driver_rows],
			row.pop("required_licence_type"),
			threshold_days,
		)
		row.update(compliance)
		row["drivers"] = ", ".join(d.driver_name or d.driver for d in driver_rows)

		if not row.get("allocation"):
			row["overall_status"] = "Not Registered"

	status_filter = (filters.get("overall_status") or "").strip()

	if status_filter:
		rows = [r for r in rows if r["overall_status"] == status_filter]

	# Worst-first, for at-a-glance triage.
	severity = {"Non-Compliant": 0, "Not Registered": 1, "Attention Required": 2, "Compliant": 3}
	rows.sort(key=lambda r: (severity.get(r["overall_status"], 4), r["asset"]))

	return rows


def _build_conditions(filters, categories):
	where = ["a.asset_category in %(categories)s", "a.docstatus = 1"]
	params = {"categories": categories}

	simple_filter_map = {
		"location": "v.location",
		"asset_category": "a.asset_category",
	}

	for filter_key, column in simple_filter_map.items():
		value = filters.get(filter_key)

		if value:
			where.append(f"{column} = %({filter_key})s")
			params[filter_key] = value

	if filters.get("driver"):
		# Drivers is a Table MultiSelect child table now — no plain column
		# to equality-match on the parent, so filter by whether any of its
		# rows names this Employee.
		where.append(
			"""
			exists (
				select 1 from `tabVehicle Allocation Driver` vad
				where vad.parent = v.name and vad.parentfield = 'drivers' and vad.driver = %(driver)s
			)
			"""
		)
		params["driver"] = filters["driver"]

	return " and ".join(where), params
