# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FleetManagementSettings(Document):
	pass


@frappe.whitelist()
def get_public_road_asset_categories() -> list[str]:
	"""Asset Categories configured as usable on public roads. Used to filter
	Vehicle Allocation's Asset field and to enumerate the fleet for the
	compliance report/notifications."""
	if not frappe.db.exists("DocType", "Fleet Management Settings"):
		return []

	settings = frappe.get_single("Fleet Management Settings")

	return [row.asset_category for row in settings.get("public_road_asset_categories") or [] if row.asset_category]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def public_road_asset_category_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for any Asset Category field that should only ever offer
	the categories configured here (e.g. the Fleet Compliance Dashboard's
	category filter) — one place decides the list, same as
	public_road_asset_query does for the Asset field itself."""
	categories = get_public_road_asset_categories()

	if not categories:
		return []

	return frappe.db.sql(
		"""
		select name
		from `tabAsset Category`
		where name in %(categories)s and name like %(txt)s
		order by name
		limit %(start)s, %(page_len)s
		""",
		{"categories": categories, "txt": f"%{txt}%", "start": start, "page_len": page_len},
	)


def get_location_custodian(location):
	"""Resolve the Employee who should become Custodian of a shared vehicle
	(a Vehicle Allocation with more than one Driver) from the Recipients
	table here: prefer a row scoped to this exact Location, falling back
	to a blank-Location (catch-all) row if no Location-specific one is
	configured. Recipients are Users (the weekly digest emails them
	directly); resolved to an Employee via Employee.user_id. Returns None
	if nothing configured resolves to a real Employee — callers should
	leave the Asset's custodian untouched in that case rather than guess."""
	if not frappe.db.exists("DocType", "Fleet Management Settings"):
		return None

	settings = frappe.get_single("Fleet Management Settings")
	rows = settings.get("recipients") or []

	location = (location or "").strip()
	specific = [r for r in rows if location and (r.location or "").strip() == location]
	catch_all = [r for r in rows if not (r.location or "").strip()]

	for row in specific + catch_all:
		employee = frappe.db.get_value("Employee", {"user_id": row.user}, "name")

		if employee:
			return employee

	return None
