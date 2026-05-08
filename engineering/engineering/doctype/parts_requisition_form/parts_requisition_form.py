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
def get_items_by_expense_account(doctype, txt, searchfield, start, page_len, filters):
	default_expense_account = filters.get("default_expense_account")

	if not default_expense_account:
		return []

	return frappe.db.sql("""
		SELECT
			item.name,
			item.item_name
		FROM `tabItem` item
		INNER JOIN `tabItem Default` item_default
			ON item_default.parent = item.name
		WHERE
			item.disabled = 0
			AND item_default.expense_account = %(default_expense_account)s
			AND (
				item.name LIKE %(txt)s
				OR item.item_name LIKE %(txt)s
			)
		ORDER BY item.name
		LIMIT %(start)s, %(page_len)s
	""", {
		"default_expense_account": default_expense_account,
		"txt": f"%{txt}%",
		"start": start,
		"page_len": page_len
	})	