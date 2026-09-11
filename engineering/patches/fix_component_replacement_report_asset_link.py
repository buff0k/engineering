# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""The Asset -> Component Replacement Report connection (shown on the
	Asset form's Connections tab) points at a link_fieldname of 'plant_no',
	which does not exist on Component Replacement Report (the actual Link
	field back to Asset is 'fleet_no'). This makes the Connections tab throw
	'Unknown column plant_no in WHERE' whenever it loads a count for Asset.
	"""
	if not frappe.db.exists("DocType", "Component Replacement Report"):
		return

	rows = frappe.get_all(
		"DocType Link",
		filters={
			"parent": "Asset",
			"link_doctype": "Component Replacement Report",
			"link_fieldname": "plant_no",
		},
		pluck="name",
	)

	if not rows:
		return

	for name in rows:
		frappe.db.set_value("DocType Link", name, "link_fieldname", "fleet_no")

	frappe.clear_cache(doctype="Asset")
	frappe.db.commit()
