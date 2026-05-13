# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, formatdate


def execute(filters=None):
	filters = filters or {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{"label": _("Asset Category"), "fieldname": "asset_category", "fieldtype": "Data", "width": 130},
		{"label": _("Shift Date"), "fieldname": "shift_date", "fieldtype": "Data", "width": 110},
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
	conditions = ["shift_date between %(from_date)s and %(to_date)s"]
	values = {
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
	}

	if filters.get("location"):
		conditions.append("location = %(location)s")
		values["location"] = filters.get("location")

	if filters.get("asset_category"):
		conditions.append("asset_category = %(asset_category)s")
		values["asset_category"] = filters.get("asset_category")

	records = frappe.db.sql(
		f"""
		select
			name,
			asset_category,
			shift_date,
			asset_name,
			location,
			shift_working_hours,
			shift_breakdown_hours,
			shift_required_hours,
			plant_shift_availability,
			plant_shift_utilisation,
			shift_other_lost_hours
		from `tabAvailability and Utilisation`
		where {" and ".join(conditions)}
		order by asset_category asc, shift_date asc, asset_name asc
		""",
		values,
		as_dict=True,
	)

	data = []

	for row in records:
		required_hours = flt(row.shift_required_hours)
		work_hrs = flt(row.shift_working_hours)
		mechanical_downtime = flt(row.shift_breakdown_hours)

		emp_avail_percent = 0
		if required_hours:
			emp_avail_percent = ((work_hrs + mechanical_downtime) / required_hours) * 100

		data.append({
			"asset_category": row.asset_category,
			"shift_date": formatdate(row.shift_date, "dd-MM-yyyy"),
			"asset_name": row.asset_name,
			"work_hrs": work_hrs,
			"mechanical_downtime": mechanical_downtime,
			"avail_percent": flt(row.plant_shift_availability, 1),
			"util_percent": flt(row.plant_shift_utilisation, 1),
			"emp_avail_percent": flt(emp_avail_percent, 1),
			"breakdown_reason": get_breakdown_reason(row),
			"other_delay_reason": get_other_delay_reason(row),
		})

	return data


def get_breakdown_reason(row):
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
			and date(update_date_time) = %(shift_date)s
			and ifnull(`{reason_field}`, '') != ''
		order by update_date_time asc
		""",
		{
			"asset_name": row.asset_name,
			"location": row.location,
			"shift_date": row.shift_date,
		},
		as_dict=True,
	)

	return "; ".join([d.get(reason_field) for d in reasons if d.get(reason_field)])


def get_other_delay_reason(row):
	reasons = []

	if flt(row.shift_other_lost_hours) > 0:
		reasons.append("Other lost hours")

	return "\n".join(reasons) if reasons else None