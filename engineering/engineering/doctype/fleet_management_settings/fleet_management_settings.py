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


def get_included_owner_scope():
	"""Reads the Reporting Scope tab: (included_companies, included_suppliers,
	included_customers), each either a set of names or None if that table
	is empty."""
	if not frappe.db.exists("DocType", "Fleet Management Settings"):
		return None, None, None

	settings = frappe.get_single("Fleet Management Settings")
	companies = {row.company for row in settings.get("included_companies") or [] if row.company}
	suppliers = {row.supplier for row in settings.get("included_suppliers") or [] if row.supplier}
	customers = {row.customer for row in settings.get("included_customers") or [] if row.customer}

	return (companies or None), (suppliers or None), (customers or None)


def is_asset_owner_in_scope(
	asset_owner, company, supplier, customer, included_companies, included_suppliers, included_customers
):
	"""Whether an Asset's effective owner (see
	engineering.controllers.fleet_compliance.effective_asset_owner) passes
	the configured Reporting Scope. Each of the three tables is a strict
	allow-list for its own owner type: an EMPTY Included Suppliers table
	means no Supplier-owned Asset qualifies at all — it does not fall back
	to "every Supplier is fine" just because that particular table has
	nothing in it. Same for Included Companies and Included Customers.

	Callers must resolve included_companies/included_suppliers/
	included_customers via get_included_owner_scope() first and
	short-circuit the "all three tables are completely empty" case
	themselves (see get_reportable_asset_names) — that is the ONLY
	situation with no restriction at all; reaching this function at all
	means at least one of the three tables has rows."""
	owner = (asset_owner or "").strip().lower()

	if owner == "supplier":
		return bool(included_suppliers) and (supplier or "") in included_suppliers

	if owner == "customer":
		return bool(included_customers) and (customer or "") in included_customers

	# Company, or Asset Owner never captured (falls back to Company — see
	# effective_asset_owner).
	return bool(included_companies) and (company or "") in included_companies


@frappe.whitelist()
def get_reportable_asset_names():
	"""The definitive set of Asset names every Fleet dashboard, report,
	Excel export and email notification should ever mention: submitted, a
	Public Road Asset Category, and — if Reporting Scope is configured —
	an included Company/Supplier/Customer. This is the one place all of
	those pull their asset universe from, so Reporting Scope applies
	everywhere consistently. Returns None if there are no Public Road
	Asset Categories configured at all (nothing can ever be in scope, same
	signal get_public_road_asset_categories() gives its own callers);
	otherwise a set of Asset names (possibly empty, if Reporting Scope
	excludes everything that matched the category filter)."""
	categories = get_public_road_asset_categories()

	if not categories:
		return None

	included_companies, included_suppliers, included_customers = get_included_owner_scope()

	if included_companies is None and included_suppliers is None and included_customers is None:
		# No Reporting Scope restriction configured — skip the extra
		# per-Asset ownership check, category + docstatus is the whole story.
		return set(
			frappe.get_all("Asset", filters={"asset_category": ["in", categories], "docstatus": 1}, pluck="name")
		)

	assets = frappe.get_all(
		"Asset",
		filters={"asset_category": ["in", categories], "docstatus": 1},
		fields=["name", "asset_owner", "company", "supplier", "customer"],
	)

	return {
		asset.name
		for asset in assets
		if is_asset_owner_in_scope(
			asset.asset_owner,
			asset.company,
			asset.supplier,
			asset.customer,
			included_companies,
			included_suppliers,
			included_customers,
		)
	}


def filter_asset_names_by_reporting_scope(asset_names):
	"""Given Asset names a caller has already narrowed down by its own
	category/site rules, returns the subset that also passes Reporting
	Scope. For callers whose "in scope" universe isn't Public Road Asset
	Categories (e.g. the Vehicle Licence Expiration page, which covers its
	own broader set of plant/equipment categories) — get_reportable_asset_names()
	itself always applies the Public Road Asset Category filter too, so it
	isn't a fit there. Reporting Scope's Company/Supplier/Customer rule is
	the same everywhere though, hence this shared helper."""
	asset_names = [name for name in asset_names if name]

	if not asset_names:
		return []

	included_companies, included_suppliers, included_customers = get_included_owner_scope()

	if included_companies is None and included_suppliers is None and included_customers is None:
		return asset_names

	assets = frappe.get_all(
		"Asset",
		filters={"name": ["in", asset_names]},
		fields=["name", "asset_owner", "company", "supplier", "customer"],
	)

	return [
		asset.name
		for asset in assets
		if is_asset_owner_in_scope(
			asset.asset_owner,
			asset.company,
			asset.supplier,
			asset.customer,
			included_companies,
			included_suppliers,
			included_customers,
		)
	]


def get_location_custodian(location):
	"""Resolve the Employee who should become Custodian of a shared vehicle
	(a Vehicle Allocation with more than one Driver) from the Weekly
	Compliance Digest Recipients — the most general-purpose of the three
	recipient lists, so it's the one used to mean "who's generally
	responsible for this Location's fleet". Prefers a row scoped to this
	exact Location, falling back to a blank-Location (catch-all) row if no
	Location-specific one is configured. Recipients are Users (the digest
	emails them directly); resolved to an Employee via Employee.user_id.
	Returns None if nothing configured resolves to a real Employee —
	callers should leave the Asset's custodian untouched in that case
	rather than guess."""
	if not frappe.db.exists("DocType", "Fleet Management Settings"):
		return None

	settings = frappe.get_single("Fleet Management Settings")
	rows = settings.get("weekly_digest_recipients") or []

	location = (location or "").strip()
	specific = [r for r in rows if location and (r.location or "").strip() == location]
	catch_all = [r for r in rows if not (r.location or "").strip()]

	for row in specific + catch_all:
		employee = frappe.db.get_value("Employee", {"user_id": row.user}, "name")

		if employee:
			return employee

	return None
