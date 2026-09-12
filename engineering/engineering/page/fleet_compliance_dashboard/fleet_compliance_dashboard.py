# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

"""Whitelisted data sources for the Fleet Compliance Dashboard page. This
page is a visual front end over the exact same data as the "Fleet
Compliance Overview" Script Report — nothing here recomputes compliance
independently, it all goes through that report's own get_data(), so the
numbers on this page and in the report can never disagree."""

import frappe

from engineering.engineering.report.fleet_compliance_overview.fleet_compliance_overview import get_data

# Fixed display order — worst first, matching the report's own triage sort.
OVERALL_STATUSES = ["Non-Compliant", "Attention Required", "Not Registered", "Compliant"]


def _get_rows(filters):
	if not frappe.has_permission("Vehicle Allocation", "read"):
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)

	return get_data(
		{
			"location": filters.get("location"),
			"asset_category": filters.get("asset_category"),
			"driver": filters.get("driver"),
			"overall_status": filters.get("overall_status"),
		}
	)


@frappe.whitelist()
def get_summary(location=None, asset_category=None, driver=None):
	"""Bubble counts, unfiltered by overall_status (that's the thing being
	counted) but respecting the other filters — so the bubbles reflect
	whatever Location/Category/Driver the user has narrowed to."""
	rows = _get_rows({"location": location, "asset_category": asset_category, "driver": driver})

	counts = dict.fromkeys(OVERALL_STATUSES, 0)

	for row in rows:
		status = row.get("overall_status")
		counts[status] = counts.get(status, 0) + 1

	return {
		"total": len(rows),
		"by_status": [{"status": status, "count": counts[status]} for status in OVERALL_STATUSES],
	}


@frappe.whitelist()
def get_rows(location=None, asset_category=None, driver=None, overall_status=None):
	"""Full drill-down row set — same shape as the Fleet Compliance Overview
	report, grouped client-side by Asset Category for the tree view."""
	return _get_rows(
		{
			"location": location,
			"asset_category": asset_category,
			"driver": driver,
			"overall_status": overall_status,
		}
	)
