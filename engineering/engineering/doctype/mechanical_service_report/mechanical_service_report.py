# Copyright (c) 2025, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MechanicalServiceReport(Document):
	pass

@frappe.whitelist()
def get_last_preuse_hours(asset: str):
    """Return eng_hrs_start of the last Pre-Use Hours document where
    Pre-use Assets.asset_name = given asset.

    Pre-Use Hours is not submittable, so we do NOT filter on docstatus.
    """

    if not asset:
        return None

    result = frappe.db.sql("""
        SELECT pua.eng_hrs_start
        FROM `tabPre-use Assets` pua
        JOIN `tabPre-Use Hours` puh
            ON pua.parent = puh.name
        WHERE pua.asset_name = %s
        ORDER BY puh.shift_date DESC, puh.creation DESC
        LIMIT 1
    """, (asset,), as_dict=True)

    if result:
        return result[0].eng_hrs_start

    return None
