# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import json
import os

import frappe

# Frappe's generic per-app doctype-folder sync (frappe.model.sync.IMPORTABLE_DOCTYPES)
# does not include "dashboard" or "dashboard_chart" for non-core apps — only
# "Number Card" gets picked up automatically. Dashboard and Dashboard Chart
# records must therefore be created explicitly, or they simply never appear
# on a site that has never run this before (e.g. prod, on first deploy of
# this app version) even though the .json files are checked into the app.


def _load_json(*parts):
	path = os.path.join(frappe.get_app_path("engineering"), *parts)

	with open(path) as f:
		return json.load(f)


def execute():
	if frappe.db.exists("DocType", "Dashboard Chart") and not frappe.db.exists(
		"Dashboard Chart", "Fleet Compliance Breakdown"
	):
		data = _load_json("engineering", "dashboard_chart", "fleet_compliance_breakdown", "fleet_compliance_breakdown.json")
		frappe.get_doc(data).insert(ignore_permissions=True)

	if frappe.db.exists("DocType", "Dashboard") and not frappe.db.exists("Dashboard", "Fleet Management"):
		data = _load_json("engineering", "engineering_dashboard", "fleet_management", "fleet_management.json")
		frappe.get_doc(data).insert(ignore_permissions=True)

	frappe.db.commit()
