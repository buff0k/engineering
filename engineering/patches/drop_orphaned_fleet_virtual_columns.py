# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe

# These fields were converted to virtual (computed live, never stored) but
# Frappe's schema sync never drops abandoned columns on its own — clean them
# up explicitly so the DB schema doesn't keep a stale, misleading copy of
# data that now lives only in ir's Employee Induction Record / the driver's
# Employee Records table / Vehicle Licence.
COLUMNS_TO_DROP = {
	"Vehicle Allocation": [
		"driver_licence_status",
		"driver_licence_valid_to",
		"driver_licence_source",
		"addendum_status",
		"addendum_date",
		"addendum_attach",
		"vehicle_licence_status",
		"vehicle_licence_valid_to",
		"vehicle_licence_source",
		"overall_status",
		"last_checked_on",
	],
	"Vehicle Licence": [
		"days_left",
		"status",
	],
}


def execute():
	for doctype, columns in COLUMNS_TO_DROP.items():
		table = f"tab{doctype}"

		if not frappe.db.table_exists(doctype):
			continue

		existing_columns = set(frappe.db.get_table_columns(doctype))

		for column in columns:
			if column not in existing_columns:
				continue

			frappe.db.sql_ddl(f"alter table `{table}` drop column `{column}`")

	frappe.db.commit()
