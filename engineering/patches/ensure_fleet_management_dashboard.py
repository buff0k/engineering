# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import json
import os

import frappe

# Frappe's generic per-app doctype-folder sync (frappe.model.sync.IMPORTABLE_DOCTYPES)
# does not reliably cover "number_card", "dashboard", or "dashboard_chart" for
# non-core apps, so none of these can be trusted to appear on their own after
# a plain `bench migrate` on a site that has never had them before. Every one
# of them is created here explicitly and idempotently, in dependency order:
# Number Cards first, then the Dashboard Chart, then the Dashboard itself
# (whose "cards"/"charts" child rows link-validate against the other two).
NUMBER_CARDS = [
	"total_public_road_assets",
	"currently_allocated",
	"unregistered_assets",
	"fleet_non_compliant",
	"fleet_expiring_soon",
]


def _load_json(*parts):
	path = os.path.join(frappe.get_app_path("engineering"), *parts)

	with open(path) as f:
		return json.load(f)


def _insert_with_exact_name(data):
	"""frappe.get_doc(data).insert() still runs the doctype's own autoname()
	(e.g. Number Card names itself from `label`, not from the `name` we pass
	in), which silently produces the wrong name whenever label != name. This
	is the same flag frappe.modules.import_file's file-sync path relies on
	(Document.set_new_name() skips autoname entirely when name_set is
	already True) — it trusts the name already on the dict, exactly as
	intended here."""
	doc = frappe.get_doc(data)
	doc.flags.name_set = True
	doc.insert(ignore_permissions=True)
	return doc


def _ensure(doctype, name, *path_parts):
	if not frappe.db.exists("DocType", doctype):
		return

	if frappe.db.exists(doctype, name):
		return

	data = _load_json(*path_parts)
	_insert_with_exact_name(data)


def execute():
	if not frappe.db.exists("DocType", "Number Card"):
		return

	for folder in NUMBER_CARDS:
		data = _load_json("engineering", "number_card", folder, f"{folder}.json")
		if not frappe.db.exists("Number Card", data.get("name")):
			_insert_with_exact_name(data)

	_ensure(
		"Dashboard Chart",
		"Fleet Compliance Breakdown",
		"engineering",
		"dashboard_chart",
		"fleet_compliance_breakdown",
		"fleet_compliance_breakdown.json",
	)

	_ensure(
		"Dashboard",
		"Fleet Management",
		"engineering",
		"engineering_dashboard",
		"fleet_management",
		"fleet_management.json",
	)

	frappe.db.commit()
