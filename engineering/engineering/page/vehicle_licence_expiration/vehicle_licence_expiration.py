# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

from urllib.parse import quote

import frappe
from frappe.utils import getdate, today

from engineering.engineering.doctype.fleet_management_settings.fleet_management_settings import (
	filter_asset_names_by_reporting_scope,
)

CATEGORIES_SHOWN = (
	"LDV",
	"Diesel Bowsers",
	"Water Bowser",
	"Service Truck",
	"Grader",
	"TLB",
	"Loader",
	"Lightning Plant",
)


def _asset_site_field():
	meta = frappe.get_meta("Asset")

	for fieldname in ("location", "site", "custom_location", "custom_site"):
		if meta.has_field(fieldname):
			return fieldname

	return None


@frappe.whitelist()
def get_asset_category_counts(site=None):
	"""One row per Asset Category: how many Assets exist in it, and how many
	Vehicle Licence documents (current + historical, any not-cancelled
	docstatus) have been captured against those Assets — two different,
	previously-conflated numbers shown separately so a category with lots
	of Assets but few Licences on file is visible at a glance.

	Assets are counted submitted-only (docstatus 1) — a Draft Asset isn't a
	real in-service vehicle yet, and a Cancelled one no longer is, so
	neither belongs in a "how many vehicles do we have" count. Also
	restricted to Fleet Management Settings' Reporting Scope (Included
	Companies/Suppliers/Customers), same as every other Fleet dashboard,
	report and export."""
	meta = frappe.get_meta("Asset")

	if not meta.has_field("asset_category"):
		return []

	site_field = _asset_site_field()
	asset_filters = {"docstatus": 1, "asset_category": ["in", CATEGORIES_SHOWN]}

	if site and site_field:
		asset_filters[site_field] = site

	assets = frappe.get_all("Asset", filters=asset_filters, fields=["name", "asset_category"])
	in_scope = set(filter_asset_names_by_reporting_scope([a.name for a in assets]))
	assets = [a for a in assets if a.name in in_scope]

	if not assets:
		return []

	fleet_numbers_by_category = {}

	for a in assets:
		fleet_numbers_by_category.setdefault(a.asset_category, []).append(a.name)

	all_fleet_numbers = [name for names in fleet_numbers_by_category.values() for name in names]
	licence_count_by_asset = {}

	if all_fleet_numbers and frappe.db.exists("DocType", "Vehicle Licence"):
		for lic in frappe.get_all(
			"Vehicle Licence",
			filters={"fleet_number": ["in", all_fleet_numbers], "docstatus": ["<", 2]},
			fields=["fleet_number"],
		):
			licence_count_by_asset[lic.fleet_number] = licence_count_by_asset.get(lic.fleet_number, 0) + 1

	out = []

	for category, fleet_numbers in fleet_numbers_by_category.items():
		licence_count = sum(licence_count_by_asset.get(fleet_number, 0) for fleet_number in fleet_numbers)

		out.append({
			"category": category,
			"asset_count": len(fleet_numbers),
			"licence_count": licence_count,
		})

	out.sort(key=lambda r: r["asset_count"], reverse=True)

	return out


@frappe.whitelist()
def get_category_summary(site=None, asset_category=None):
	if not asset_category:
		return {"rows": []}

	site_field = _asset_site_field()
	asset_filters = {"docstatus": 1, "asset_category": asset_category}

	if site and site_field:
		asset_filters[site_field] = site

	fleet_numbers = frappe.get_all("Asset", filters=asset_filters, pluck="name", limit_page_length=0)
	fleet_numbers = filter_asset_names_by_reporting_scope(fleet_numbers)

	if not fleet_numbers:
		return {"rows": []}

	docs = frappe.get_all(
		"Vehicle Licence",
		filters=[["docstatus", "<", 2], ["fleet_number", "in", fleet_numbers]],
		fields=["name", "site", "fleet_number", "registration_number", "issue_date", "expiry_date", "attach", "modified"],
		order_by="fleet_number asc, expiry_date desc, modified desc",
		limit_page_length=0,
	)

	latest = {}
	for d in docs:
		key = (d.get("site"), d.get("fleet_number"))
		if key not in latest:
			latest[key] = d

	as_at = getdate(today())
	out = []
	for d in latest.values():
		expiry = getdate(d.get("expiry_date")) if d.get("expiry_date") else None
		days_left = (expiry - as_at).days if expiry else None
		out.append({
			"name": d.get("name"),
			"site": d.get("site"),
			"fleet_number": d.get("fleet_number"),
			"registration_number": d.get("registration_number"),
			"issue_date": d.get("issue_date"),
			"expiry_date": d.get("expiry_date"),
			"days_left": days_left,
			"attach": d.get("attach"),
			"record_url": f"/app/vehicle-licence/{quote(d.get('name') or '')}",
		})

	return {"rows": out}


@frappe.whitelist()
def get_doc_history_tree_meta(site=None, asset=None, asset_category=None):
	filters = [["docstatus", "<", 2]]
	if site:
		filters.append(["site", "=", site])
	if asset:
		filters.append(["fleet_number", "=", asset])

	# Always narrow to the Reporting-Scope-permitted Assets (Included
	# Companies/Suppliers/Customers), same as every other Fleet
	# dashboard/report/export — not just when asset_category is given.
	asset_filters = {"docstatus": 1, "asset_category": asset_category or ["in", CATEGORIES_SHOWN]}
	fleet_numbers = frappe.get_all("Asset", filters=asset_filters, pluck="name")
	fleet_numbers = filter_asset_names_by_reporting_scope(fleet_numbers)
	filters.append(["fleet_number", "in", fleet_numbers or [""]])

	rows = frappe.get_all(
		"Vehicle Licence",
		filters=filters,
		fields=["site", "fleet_number"],
		order_by="site asc, fleet_number asc",
		limit_page_length=0,
	)

	tree_map = {}
	for r in rows:
		st = (r.get("site") or "Unknown").strip()
		fleet = (r.get("fleet_number") or "Unknown").strip()
		tree_map.setdefault(st, {})[fleet] = tree_map.setdefault(st, {}).get(fleet, 0) + 1

	out = []
	for st in sorted(tree_map):
		site_count = sum(tree_map[st].values())
		out.append({
			"label": st,
			"count": site_count,
			"children": [
				{"label": fleet, "count": count}
				for fleet, count in sorted(tree_map[st].items())
			],
		})

	return {"tree": out}


@frappe.whitelist()
def get_doc_history_docs(site=None, fleet_number=None, asset=None, limit=50, offset=0):
	if not fleet_number:
		return {"rows": [], "limit": int(limit or 50), "offset": int(offset or 0)}

	filters = [["docstatus", "<", 2], ["fleet_number", "=", fleet_number]]
	if site:
		filters.append(["site", "=", site])
	if asset:
		filters.append(["fleet_number", "=", asset])

	rows = frappe.get_all(
		"Vehicle Licence",
		filters=filters,
		fields=["name", "site", "fleet_number", "registration_number", "issue_date", "expiry_date", "attach", "modified"],
		order_by="expiry_date desc, modified desc",
		limit_start=int(offset or 0),
		limit_page_length=int(limit or 50),
	)

	out = []
	for r in rows:
		x = dict(r)
		x["record_url"] = f"/app/vehicle-licence/{quote(r.get('name') or '')}"
		out.append(x)

	return {"rows": out, "limit": int(limit or 50), "offset": int(offset or 0)}
