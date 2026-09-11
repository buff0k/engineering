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
