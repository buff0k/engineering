# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

"""Whitelisted data sources for the Fleet Management dashboard's Number
Cards. Each returns {"value": N, "route": [...], "route_options": {...}}
so clicking a card drills straight into the filtered Fleet Compliance
Overview report.

Compliance-related counts (Non-Compliant / Expiring Soon) are computed live
per allocation via fleet_compliance.compute_all — never read from a stored
column, since overall_status is a virtual field on Vehicle Allocation."""

import frappe

from engineering.controllers.fleet_compliance import bulk_drivers, compute_all, get_expiring_threshold_days
from engineering.engineering.doctype.fleet_management_settings.fleet_management_settings import (
	get_public_road_asset_categories,
)

REPORT_ROUTE = ["query-report", "Fleet Compliance Overview"]


def _asset_count(categories):
	if not categories:
		return 0

	return frappe.db.count("Asset", filters={"asset_category": ["in", categories], "docstatus": ["<", 2]})


def _current_allocations():
	return frappe.get_all(
		"Vehicle Allocation",
		filters={"docstatus": 1, "status": "Current"},
		fields=["name", "asset", "required_licence_type"],
	)


def _count_by_overall_status(target_statuses):
	threshold_days = get_expiring_threshold_days()
	rows = _current_allocations()
	drivers_by_parent = bulk_drivers([row.name for row in rows])
	count = 0

	for row in rows:
		compliance = compute_all(
			row.asset,
			[d.driver for d in drivers_by_parent.get(row.name, [])],
			row.required_licence_type,
			threshold_days,
		)

		if compliance["overall_status"] in target_statuses:
			count += 1

	return count


@frappe.whitelist()
def total_public_road_assets(filters=None):
	categories = get_public_road_asset_categories()

	return {"value": _asset_count(categories), "route": REPORT_ROUTE}


@frappe.whitelist()
def currently_allocated(filters=None):
	value = frappe.db.count("Vehicle Allocation", filters={"docstatus": 1, "status": "Current"})

	return {"value": value, "route": REPORT_ROUTE, "route_options": {"registered": "Yes"}}


@frappe.whitelist()
def unregistered_assets(filters=None):
	categories = get_public_road_asset_categories()

	if not categories:
		return {"value": 0, "route": REPORT_ROUTE}

	value = frappe.db.sql(
		"""
		select count(*)
		from `tabAsset` a
		left join `tabVehicle Allocation` v
			on v.asset = a.name and v.docstatus = 1 and v.status = 'Current'
		where a.asset_category in %(categories)s and a.docstatus < 2 and v.name is null
		""",
		{"categories": categories},
	)[0][0]

	return {"value": value, "route": REPORT_ROUTE, "route_options": {"registered": "No"}}


@frappe.whitelist()
def non_compliant(filters=None):
	value = _count_by_overall_status({"Non-Compliant"})

	return {"value": value, "route": REPORT_ROUTE, "route_options": {"overall_status": "Non-Compliant"}}


@frappe.whitelist()
def expiring_soon(filters=None):
	value = _count_by_overall_status({"Attention Required"})

	return {"value": value, "route": REPORT_ROUTE, "route_options": {"overall_status": "Attention Required"}}
