# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Vehicle Allocation's single 'driver' Link field is being replaced by
	the 'drivers' Table MultiSelect field (Vehicle Allocation Driver child
	rows, parentfield 'drivers') — one mechanism for 0, 1, or many drivers,
	instead of a single field plus a separate "additional drivers" table.

	Must run in post_model_sync, AFTER sync_all() has created the Vehicle
	Allocation Driver table from its doctype file, but relies on Frappe
	never auto-dropping an orphaned column on its own (see
	drop_orphaned_fleet_virtual_columns, which runs right after this and
	actually removes 'driver'/'driver_name'/'driver_branch') — so the old
	'driver' column is still physically present and readable here even
	though it's already gone from Vehicle Allocation's meta.

	Uses raw SQL throughout since 'driver' is no longer a field the ORM
	knows about post-sync. Idempotent: skips any Vehicle Allocation that
	already has a matching 'drivers' row (e.g. this patch running twice)."""
	if not frappe.db.table_exists("Vehicle Allocation"):
		return  # fresh install — nothing to migrate

	existing_columns = set(frappe.db.get_table_columns("Vehicle Allocation"))

	if "driver" not in existing_columns:
		return  # already migrated + column already dropped on this site

	rows = frappe.db.sql(
		"select name, driver from `tabVehicle Allocation` where driver is not null and driver != ''",
		as_dict=True,
	)

	if not rows:
		return

	if not frappe.db.table_exists("Vehicle Allocation Driver"):
		# Shouldn't happen this late in post_model_sync, but don't hard-fail
		# a migration over it — the next migrate run will pick this up once
		# the table exists.
		return

	migrated = 0

	for row in rows:
		already = frappe.db.sql(
			"""
			select name from `tabVehicle Allocation Driver`
			where parent=%(parent)s and parentfield='drivers' and driver=%(driver)s
			""",
			{"parent": row.name, "driver": row.driver},
		)

		if already:
			continue

		driver_name = frappe.db.get_value("Employee", row.driver, "employee_name")

		frappe.db.sql(
			"""
			insert into `tabVehicle Allocation Driver`
				(name, owner, creation, modified, modified_by, docstatus, idx,
				 parent, parenttype, parentfield, driver, driver_name)
			values
				(%(name)s, 'Administrator', now(), now(), 'Administrator', 0, 1,
				 %(parent)s, 'Vehicle Allocation', 'drivers', %(driver)s, %(driver_name)s)
			""",
			{
				"name": frappe.generate_hash(length=10),
				"parent": row.name,
				"driver": row.driver,
				"driver_name": driver_name,
			},
		)
		migrated += 1

	frappe.db.commit()
	frappe.logger().info(f"migrate_vehicle_allocation_single_driver_to_table: migrated {migrated} row(s)")
