# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

from urllib.parse import quote

import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count
from frappe.utils import getdate, today

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
	neither belongs in a "how many vehicles do we have" count."""
	meta = frappe.get_meta("Asset")

	if not meta.has_field("asset_category"):
		return []

	site_field = _asset_site_field()
	Asset = DocType("Asset")

	asset_q = (
		frappe.qb.from_(Asset)
		.select(Asset.asset_category.as_("category"), Count(Asset.name).as_("asset_count"))
		.where(Asset.docstatus == 1)
		.where(Asset.asset_category.isin(CATEGORIES_SHOWN))
		.groupby(Asset.asset_category)
		.orderby(Count(Asset.name), order=frappe.qb.desc)
	)

	if site and site_field:
		asset_q = asset_q.where(getattr(Asset, site_field) == site)

	asset_rows = asset_q.run(as_dict=True)
	categories = [r["category"] for r in asset_rows if r.get("category")]

	if not categories:
		return []

	asset_filters = {"asset_category": ["in", categories], "docstatus": 1}

	if site and site_field:
		asset_filters[site_field] = site

	fleet_numbers_by_category = {}

	for a in frappe.get_all("Asset", filters=asset_filters, fields=["name", "asset_category"]):
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

	for r in asset_rows:
		category = r.get("category")

		if not category:
			continue

		licence_count = sum(
			licence_count_by_asset.get(fleet_number, 0)
			for fleet_number in fleet_numbers_by_category.get(category, [])
		)

		out.append({
			"category": category,
			"asset_count": int(r.get("asset_count") or 0),
			"licence_count": licence_count,
		})

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
	if asset_category:
		fleet_numbers = frappe.get_all(
			"Asset", filters={"asset_category": asset_category, "docstatus": 1}, pluck="name"
		)
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
