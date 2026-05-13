# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from is_production.production.report.avail_and_util_summary import avail_and_util_summary as summary


def execute(filters=None):
	filters = filters or {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{"label": _("Asset Category"), "fieldname": "asset_category", "fieldtype": "Data", "width": 130},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 110},
		{"label": _("Work Hrs"), "fieldname": "work_hrs", "fieldtype": "Float", "precision": 1, "width": 90},
		{"label": _("Mechanical Downtime"), "fieldname": "mechanical_downtime", "fieldtype": "Float", "precision": 1, "width": 160},
		{"label": _("Avail (%)"), "fieldname": "avail_percent", "fieldtype": "Percent", "precision": 1, "width": 100},
		{"label": _("Util (%)"), "fieldname": "util_percent", "fieldtype": "Percent", "precision": 1, "width": 100},
		{"label": _("Emp Avail (%)"), "fieldname": "emp_avail_percent", "fieldtype": "Percent", "precision": 1, "width": 120},
		{"label": _("Breakdown Reason"), "fieldname": "breakdown_reason", "fieldtype": "Small Text", "width": 300},
		{"label": _("Other Delay Reason"), "fieldname": "other_delay_reason", "fieldtype": "Small Text", "width": 300},
	]






def get_data(filters):
	summary_filters = {
		"start_date": filters.get("from_date"),
		"end_date": filters.get("to_date"),
		"location": filters.get("location"),
	}

	summary_rows = summary.get_grouped_data(summary_filters)

	machine_rows = [
		row for row in summary_rows
		if row.get("indent") == 2
	]

	if filters.get("asset_category"):
		machine_rows = [
			row for row in machine_rows
			if row.get("asset_category") == filters.get("asset_category")
		]

	grouped = {}

	for row in machine_rows:
		key = (
			row.get("asset_category"),
			row.get("asset_name"),
			row.get("location"),
		)

		if key not in grouped:
			grouped[key] = {
				"asset_category": row.get("asset_category"),
				"asset_name": row.get("asset_name"),
				"location": row.get("location"),
				"shift_required_hours": 0,
				"shift_working_hours": 0,
				"shift_breakdown_hours": 0,
				"shift_available_hours": 0,
				"shift_other_lost_hours": 0,
				"avail_percentages": [],
				"util_percentages": [],
				"emp_avail_percentages": [],
				"breakdown_reason": [],
				"other_delay_reason": [],
			}

		target = grouped[key]

		target["shift_required_hours"] += flt(row.get("shift_required_hours"))
		target["shift_working_hours"] += flt(row.get("shift_working_hours"))
		target["shift_breakdown_hours"] += flt(row.get("shift_breakdown_hours"))
		target["shift_available_hours"] += flt(row.get("shift_available_hours"))
		target["shift_other_lost_hours"] += flt(row.get("shift_other_lost_hours"))

		target["avail_percentages"].append(flt(row.get("plant_shift_availability")))
		target["util_percentages"].append(flt(row.get("plant_shift_utilisation")))
		target["emp_avail_percentages"].append(flt(row.get("employee_availability")))

		if row.get("breakdown_reason"):
			target["breakdown_reason"].append(row.get("breakdown_reason"))

		if row.get("other_delay_reason"):
			target["other_delay_reason"].append(row.get("other_delay_reason"))

	data = []

	for row in grouped.values():
		required_hrs = flt(row["shift_required_hours"])
		available_hrs = flt(row["shift_available_hours"])
		work_hrs = flt(row["shift_working_hours"])
		mechanical_downtime = flt(row["shift_breakdown_hours"])
		other_lost_hrs = flt(row["shift_other_lost_hours"])

		data.append({
			"asset_category": row["asset_category"],
			"asset_name": row["asset_name"],
			"work_hrs": summary.r1(work_hrs),
			"mechanical_downtime": summary.r1(mechanical_downtime),
			"avail_percent": average_percent(row["avail_percentages"]),
			"util_percent": average_percent(row["util_percentages"]),
			"emp_avail_percent": average_percent(row["emp_avail_percentages"]),
			"breakdown_reason": clean_join(row["breakdown_reason"]),
			"other_delay_reason": clean_join(row["other_delay_reason"]),
		})
	return data


def average_percent(values):
	valid_values = [flt(value) for value in values if value is not None]

	if not valid_values:
		return 0

	return summary.r1(sum(valid_values) / len(valid_values))




def clean_join(values):
	cleaned = []

	for value in values:
		if not value:
			continue

		for part in str(value).split(";"):
			part = part.strip()
			if part and part not in cleaned:
				cleaned.append(part)

	return "\n".join(cleaned)




def get_breakdown_reason(row, filters):
	if not frappe.db.exists("DocType", "Breakdown History"):
		return None

	meta = frappe.get_meta("Breakdown History")
	possible_fields = [
		"breakdown_reason",
		"reason",
		"remarks",
		"description",
		"comment",
		"comments",
	]

	reason_field = None
	for fieldname in possible_fields:
		if meta.has_field(fieldname):
			reason_field = fieldname
			break

	if not reason_field:
		return None

	reasons = frappe.db.sql(
		f"""
		select distinct `{reason_field}`
		from `tabBreakdown History`
		where asset_name = %(asset_name)s
			and location = %(location)s
			and date(update_date_time) between %(from_date)s and %(to_date)s
			and ifnull(`{reason_field}`, '') != ''
		order by update_date_time asc
		""",
		{
			"asset_name": row.asset_name,
			"location": row.location,
			"from_date": filters.get("from_date"),
			"to_date": filters.get("to_date"),
		},
		as_dict=True,
	)

	return "; ".join([d.get(reason_field) for d in reasons if d.get(reason_field)])







def get_other_delay_reason(row):
	reasons = []

	if flt(row.other_lost_hrs) > 0:
		reasons.append("Other lost hours")

	return "\n".join(reasons) if reasons else None