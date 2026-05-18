# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PartsRequisitionForm(Document):
	pass


@frappe.whitelist()
def get_asset_machine_details(asset_name):
	if not asset_name:
		return {
			"plant_make": "",
			"model": "",
			"vin_no": ""
		}

	asset = frappe.get_doc("Asset", asset_name)

	def pick_first(doc, fieldnames):
		for fieldname in fieldnames:
			if hasattr(doc, fieldname):
				value = getattr(doc, fieldname, None)
				if value:
					return value
		return ""

	plant_make = pick_first(asset, [
		"asset_category",
		"make",
		"brand",
		"machine_make",
		"plant_make"
	])

	model = pick_first(asset, [
		"model",
		"machine_model",
		"asset_model",
		"equipment_model"
	])

	vin_no = pick_first(asset, [
		"vin_no",
		"vin",
		"chassis_no",
		"serial_no"
	])

	return {
		"plant_make": plant_make or "",
		"model": model or "",
		"vin_no": vin_no or ""
	}



@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_assets_by_site_code(doctype, txt, searchfield, start, page_len, filters):
	company = filters.get("company")
	site = filters.get("site")

	if not company or not site:
		return []

	location = frappe.db.get_value("Site Code", site, "location")

	if not location:
		return []

	return frappe.db.sql("""
		SELECT
			asset.name,
			asset.asset_name
		FROM `tabAsset` asset
		WHERE
			asset.docstatus = 1
			AND asset.asset_owner_company = %(company)s
			AND asset.location = %(location)s
			AND (
				asset.name LIKE %(txt)s
				OR asset.asset_name LIKE %(txt)s
			)
		ORDER BY asset.name
		LIMIT %(start)s, %(page_len)s
	""", {
		"company": company,
		"location": location,
		"txt": f"%{txt}%",
		"start": start,
		"page_len": page_len
	})
