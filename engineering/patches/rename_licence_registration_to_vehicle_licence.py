# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Licence Registration was renamed to Vehicle Licence (repurposed as the
	per-Asset AARTO vehicle-licence record backing the fleet compliance
	workflow). This MUST run in pre_model_sync, before sync_all() creates a
	fresh empty 'Vehicle Licence' table and before remove_orphan_doctypes()
	strips the DocType meta off any surviving 'Licence Registration' data —
	otherwise every existing Licence Registration record becomes invisible to
	the app on any site that still has the old doctype.

	Idempotent: no-ops once the rename has already happened (e.g. this was
	applied directly on the lab site before this patch existed).
	"""
	if frappe.db.exists("DocType", "Vehicle Licence"):
		return

	if not frappe.db.exists("DocType", "Licence Registration"):
		# Fresh install — nothing to rename, sync_all() will create
		# "Vehicle Licence" from the doctype files directly.
		return

	# Files on disk are already named/shaped for "Vehicle Licence"; only the
	# DocType record, its table, and cross-doctype references need renaming.
	frappe.flags.in_patch = True
	frappe.rename_doc("DocType", "Licence Registration", "Vehicle Licence", force=True)
	frappe.db.commit()
