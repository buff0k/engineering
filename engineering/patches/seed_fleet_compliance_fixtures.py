# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe

LICENCE_CODES = [
	"Drivers Licence - Code B",
	"Drivers Licence - Code EB",
	"Drivers Licence - Code C",
	"Drivers Licence - Code EC",
	"Drivers Licence - Code C1",
	"Drivers Licence - Code EC1",
]

COMPANY_VEHICLE_UNDERTAKING = "Company Vehicle Undertaking"


def execute():
	"""Seed the master data backing the fleet compliance workflow: the LDV
	Asset Category, the driver's-licence competency codes, and the
	'Company Vehicle Undertaking' Employee File Record type."""
	if frappe.db.exists("DocType", "Asset Category") and not frappe.db.exists("Asset Category", "LDV"):
		doc = frappe.new_doc("Asset Category")
		doc.asset_category_name = "LDV"
		doc.insert(ignore_permissions=True)

	if frappe.db.exists("DocType", "Employee Induction"):
		for training_name in LICENCE_CODES:
			if frappe.db.exists("Employee Induction", training_name):
				continue

			doc = frappe.new_doc("Employee Induction")
			doc.training_name = training_name
			doc.valid_for = "60"
			doc.is_licence = 1
			doc.is_training = 0
			doc.is_qualification = 0
			doc.is_authorisation = 0
			doc.insert(ignore_permissions=True)

	if frappe.db.exists("DocType", "Employee File Record") and not frappe.db.exists(
		"Employee File Record", COMPANY_VEHICLE_UNDERTAKING
	):
		doc = frappe.new_doc("Employee File Record")
		doc.record_name = COMPANY_VEHICLE_UNDERTAKING
		doc.insert(ignore_permissions=True)

	if frappe.db.exists("DocType", "Fleet Management Settings"):
		settings = frappe.get_single("Fleet Management Settings")
		existing = {row.asset_category for row in settings.get("public_road_asset_categories") or []}

		if "LDV" not in existing:
			settings.append("public_road_asset_categories", {"asset_category": "LDV"})
			settings.save(ignore_permissions=True)

	frappe.db.commit()
