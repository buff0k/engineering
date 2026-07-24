# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, get_datetime, getdate, nowdate

_ = frappe._

MONTH_END_CATEGORIES = [
    "ADT",
    "Dozer",
    "Excavator",
    "Grader",
    "Service Truck",
    "TLB",
    "Water Bowser",
    "Diesel Bowsers",
    "Drills",
    "Loader",
]



CATEGORY_MAP = {
    "ADT": "ADT",
    "ADT's": "ADT",
    "Dozer": "Dozer",
    "Dozer's": "Dozer",
    "Excavator": "Excavator",
    "Excavator's": "Excavator",
    "Grader": "Grader",
    "Service Truck": "Service Truck",
    "TLB": "TLB",
    "Water Bowser": "Water Bowser",
    "Diesel Bowsers": "Diesel Bowsers",
    "Drills": "Drills",
    "Loader": "Loader",
}

UI_CATEGORIES = [
    "ADT",
    "Dozer",
    "Excavator",
    "Grader",
    "Service Truck",
    "TLB",
    "Water Bowser",
    "Diesel Bowsers",
    "Drills",
    "Loader",
]

from is_production.production.report.avail_and_util_summary import avail_and_util_summary as summary

def safe_msr_datetime(value, service_date=None):
    if value in (None, ""):
        return None

    value_text = str(value).strip()
    if not value_text:
        return None

    service_date_text = str(service_date).strip() if service_date else None

    if (
        "0000-00-00" in value_text
        or "-00-" in value_text
        or value_text.startswith("2008-00-00")
    ):
        if service_date_text and " " in value_text:
            time_text = value_text.split()[-1].split(".")[0]
            try:
                return safe_msr_datetime(f"{service_date_text} {time_text}")
            except Exception:
                return None
        return None

    try:
        return get_datetime(value)
    except Exception:
        if service_date_text and ":" in value_text:
            time_text = value_text.split()[-1].split(".")[0]
            try:
                return safe_msr_datetime(f"{service_date_text} {time_text}")
            except Exception:
                return None
        return None


def safe_getdate(value):
    if value in (None, ""):
        return None

    value_text = str(value).strip()
    if not value_text:
        return None

    if "0000-00-00" in value_text or "-00-" in value_text or value_text.startswith("2008-00-00"):
        return None

    try:
        return getdate(value)
    except Exception:
        return None

def get_au_target_multiplier(filters):
	filters = filters or {}
	au_target_filter = filters.get("au_target_filter") or "85% A & U"

	if au_target_filter == "85% A & U":
		return 0.85

	return 1.0


def apply_au_target(value, filters):
	if value in (None, ""):
		return value

	multiplier = get_au_target_multiplier(filters)

	return summary.r1(flt(value) * multiplier)

def execute(filters=None):
	filters = filters or {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{"label": _("Asset Category"), "fieldname": "asset_category", "fieldtype": "Data", "width": 130},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 110},
		{"label": _("Req Hrs"), "fieldname": "required_hrs", "fieldtype": "Float", "precision": 1, "width": 90},
		{"label": _("Work Hrs"), "fieldname": "work_hrs", "fieldtype": "Float", "precision": 1, "width": 90},
		{"label": _("Mechanical Downtime"), "fieldname": "mechanical_downtime", "fieldtype": "Float", "precision": 1, "width": 160},
		{"label": _("Avail (%)"), "fieldname": "avail_percent", "fieldtype": "Percent", "precision": 1, "width": 100},
		{"label": _("Util (%)"), "fieldname": "util_percent", "fieldtype": "Percent", "precision": 1, "width": 100},
		{"label": _("Emp Avail (%)"), "fieldname": "emp_avail_percent", "fieldtype": "Percent", "precision": 1, "width": 120},
		{"label": _("Breakdown Reason"), "fieldname": "breakdown_reason", "fieldtype": "Small Text", "width": 300},
		{"label": _("Other Delay Reason"), "fieldname": "other_delay_reason", "fieldtype": "Small Text", "width": 300},
	]






def get_data(filters):
	filters = frappe._dict(filters or {})

	# Do not calculate dates after today.
	to_date = filters.get("to_date") or filters.get("end_date")

	if to_date and getdate(to_date) > getdate(nowdate()):
		filters["to_date"] = nowdate()
		filters["end_date"] = nowdate()

	machine_scope = (
		filters.get("machine_scope")
		or "Production + Swing/Spare Machines"
	)

	source_machine_scope = machine_scope

	if machine_scope == "Production + Swing/Spare Machines":
		source_machine_scope = "Include Swing/Spare"

	summary_filters = {
		"start_date": filters.get("from_date"),
		"end_date": filters.get("to_date"),
		"location": filters.get("location"),
		"machine_scope": source_machine_scope,
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

	category_total_rows = [
		row for row in summary_rows
		if row.get("indent") == 0
	]

	if filters.get("asset_category"):
		category_total_rows = [
			row for row in category_total_rows
			if row.get("asset_category") == filters.get("asset_category")
		]

	for row in category_total_rows:
		category = row.get("asset_category")

		category_machines = [
			machine
			for machine in grouped.values()
			if machine.get("asset_category") == category
		]

		machine_avail_values = [
			average_percent(machine.get("avail_percentages") or [])
			for machine in category_machines
		]

		machine_util_values = [
			average_percent(machine.get("util_percentages") or [])
			for machine in category_machines
		]

		data.append({
			"asset_category": category,
			"asset_name": "",
			"required_hrs": summary.r1(row.get("shift_required_hours")),
			"work_hrs": summary.r1(row.get("shift_working_hours")),
			"mechanical_downtime": summary.r1(row.get("shift_breakdown_hours")),
			"avail_percent": apply_au_target(
				average_percent(machine_avail_values),
				filters,
			),
			"util_percent": apply_au_target(
				average_percent(machine_util_values),
				filters,
			),
			"emp_avail_percent": summary.r1(
				row.get("employee_availability")
			),
			"breakdown_reason": "",
			"other_delay_reason": "",
			"is_category_total": 1,
		})

	data.append({
		"asset_category": "",
		"asset_name": "",
		"required_hrs": None,
		"work_hrs": None,
		"mechanical_downtime": None,
		"avail_percent": None,
		"util_percent": None,
		"emp_avail_percent": None,
		"breakdown_reason": "",
		"other_delay_reason": "",
		"is_separator": 1,
	})

	for row in grouped.values():
		required_hrs = flt(row["shift_required_hours"])
		work_hrs = flt(row["shift_working_hours"])
		mechanical_downtime = flt(row["shift_breakdown_hours"])

		data.append({
			"asset_category": row["asset_category"],
			"asset_name": row["asset_name"],
			"required_hrs": summary.r1(required_hrs),
			"work_hrs": summary.r1(work_hrs),
			"mechanical_downtime": summary.r1(mechanical_downtime),
			"avail_percent": apply_au_target(
				average_percent(row["avail_percentages"]),
				filters,
			),
			"util_percent": apply_au_target(
				average_percent(row["util_percentages"]),
				filters,
			),
			"emp_avail_percent": average_percent(
				row["emp_avail_percentages"]
			),
			"breakdown_reason": clean_join(row["breakdown_reason"]),
			"other_delay_reason": clean_join(row["other_delay_reason"]),
		})

	return data


def ensure_all_category_total_rows(data):
    existing_categories = {
        row.get("asset_category")
        for row in data
        if row.get("asset_category") and not row.get("asset_name")
    }

    insert_at = 0

    for category in UI_CATEGORIES:
        if category in existing_categories:
            continue

        data.insert(insert_at, {
            "asset_category": category,
            "asset_name": "",
            "required_hrs": 0,
            "work_hrs": 0,
            "mechanical_downtime": 0,
            "avail_percent": 0,
            "util_percent": 0,
            "emp_avail_percent": 0,
            "breakdown_reason": "",
            "other_delay_reason": "",
            "is_category_total": 1,
        })

        insert_at += 1

    data.sort(
        key=lambda row: (
            UI_CATEGORIES.index(row.get("asset_category"))
            if row.get("asset_category") in UI_CATEGORIES
            else 999,
            0 if not row.get("asset_name") else 1,
            row.get("asset_name") or "",
        )
    )

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

def clean_reason_details(details):
	cleaned = []
	seen = set()

	for detail in details or []:
		date_value = str(detail.get("date") or "")[:10]
		start_datetime = str(detail.get("start_datetime") or "")[:16]
		resolved_datetime = str(detail.get("resolved_datetime") or "")[:16]
		reason_value = detail.get("reason") or ""
		total_minutes = int(flt(detail.get("total_minutes")))
		startup_fatigue_minutes = int(flt(detail.get("startup_fatigue_minutes")))
		au_minutes = int(flt(detail.get("au_minutes")))

		for part in str(reason_value).replace("\n", ";").split(";"):
			part = part.strip()

			if not part:
				continue

			key = (date_value, start_datetime, resolved_datetime, part)

			if key in seen:
				continue

			seen.add(key)
			cleaned.append({
				"date": date_value,
				"start_datetime": start_datetime,
				"resolved_datetime": resolved_datetime,
				"total_minutes": total_minutes,
				"startup_fatigue_minutes": startup_fatigue_minutes,
				"au_minutes": au_minutes,
				"reason": part,
			})

	return cleaned



def get_startup_fatigue_minutes_for_breakdown(filters, asset_name, start_datetime, resolved_datetime):
	if not start_datetime or not resolved_datetime:
		return 0

	try:
		from engineering.engineering.doctype.availability_and_utilisation import availability_and_utilisation as au
	except Exception:
		return 0

	filters = frappe._dict(filters or {})
	location = _month_end_get_filter_value(filters, "location", "site", "production_site")

	start_dt = get_datetime(start_datetime)
	end_dt = get_datetime(resolved_datetime)

	if not start_dt or not end_dt or end_dt <= start_dt:
		return 0

	au_rows = frappe.db.sql("""
		SELECT
			name,
			shift_date,
			shift,
			shift_system,
			location,
			asset_name
		FROM `tabAvailability and Utilisation`
		WHERE asset_name = %(asset_name)s
		  AND shift_date >= DATE(%(start_datetime)s) - INTERVAL 1 DAY
		  AND shift_date <= DATE(%(resolved_datetime)s) + INTERVAL 1 DAY
		  AND (%(location)s = '' OR location = %(location)s)
		ORDER BY shift_date ASC, FIELD(shift, 'Day', 'Night') ASC
	""", {
		"asset_name": asset_name,
		"location": location or "",
		"start_datetime": start_dt,
		"resolved_datetime": end_dt,
	}, as_dict=True)

	excluded_hours = 0.0

	for row in au_rows:
		try:
			shift_start, shift_end = au.get_shift_timings(
				row.shift_system,
				row.shift,
				str(row.shift_date),
			)

			excluded_windows = au._exclusion_windows(
				row.location,
				row.shift,
				shift_start,
				shift_end,
			)

			for window_start, window_end in excluded_windows:
				excluded_hours += au._overlap_hours(
					start_dt,
					end_dt,
					window_start,
					window_end,
				)
		except Exception:
			continue

	return int(round(excluded_hours * 60))




def get_plant_breakdown_reason_details(filters, asset_names):
	if not asset_names:
		return {}

	if not frappe.db.exists("DocType", "Plant Breakdown or Maintenance"):
		return {}

	filters = frappe._dict(filters or {})

	from_date = _month_end_get_filter_value(filters, "from_date", "start_date")
	to_date = _month_end_get_filter_value(filters, "to_date", "end_date")
	location = _month_end_get_filter_value(filters, "location", "site", "production_site")

	if not from_date or not to_date:
		return {}

	values = {
		"from_datetime": f"{from_date} 00:00:00",
		"to_datetime": f"{to_date} 23:59:59",
		"asset_names": tuple(asset_names),
		"plant_breakdown_trust_datetime": "2026-01-01 00:00:00",
	}

	conditions = [
		"IFNULL(asset_name, '') != ''",
		"IFNULL(breakdown_reason, '') != ''",
		"IFNULL(exclude_from_au, 0) = 0",
		"asset_name in %(asset_names)s",
		"breakdown_start_datetime >= %(plant_breakdown_trust_datetime)s",
		"breakdown_start_datetime <= %(to_datetime)s",
		"(resolved_datetime >= %(from_datetime)s OR resolved_datetime IS NULL)",
	]

	if location:
		conditions.append("location = %(location)s")
		values["location"] = location

	rows = frappe.db.sql(
		f"""
		SELECT
			asset_name,
			breakdown_start_datetime,
			resolved_datetime,
			breakdown_reason
		FROM `tabPlant Breakdown or Maintenance`
		WHERE {" AND ".join(conditions)}
		ORDER BY breakdown_start_datetime ASC
		""",
		values,
		as_dict=True,
	)

	details_by_asset = {}

	for row in rows:
		start_datetime = row.get("breakdown_start_datetime")
		resolved_datetime = row.get("resolved_datetime")

		total_minutes = 0
		startup_fatigue_minutes = 0
		au_minutes = 0

		display_start_datetime = start_datetime
		display_resolved_datetime = resolved_datetime

		if start_datetime:
			start_dt = get_datetime(start_datetime)
			end_dt = get_datetime(resolved_datetime) if resolved_datetime else get_datetime(values["to_datetime"])
			filter_start_dt = get_datetime(values["from_datetime"])
			filter_end_dt = get_datetime(values["to_datetime"])

			if start_dt and end_dt and end_dt > start_dt:
				clipped_start_dt = max(start_dt, filter_start_dt)
				clipped_end_dt = min(end_dt, filter_end_dt)

				if clipped_end_dt > clipped_start_dt:
					display_start_datetime = clipped_start_dt
					display_resolved_datetime = clipped_end_dt

					total_minutes = int(round((clipped_end_dt - clipped_start_dt).total_seconds() / 60))
					startup_fatigue_minutes = get_startup_fatigue_minutes_for_breakdown(
						filters,
						row.get("asset_name"),
						clipped_start_dt,
						clipped_end_dt,
					)
					au_minutes = max(total_minutes - startup_fatigue_minutes, 0)

		details_by_asset.setdefault(row.get("asset_name"), []).append({
			"date": str(display_start_datetime or "")[:10],
			"start_datetime": display_start_datetime,
			"resolved_datetime": display_resolved_datetime,
			"total_minutes": total_minutes,
			"startup_fatigue_minutes": startup_fatigue_minutes,
			"au_minutes": au_minutes,
			"reason": row.get("breakdown_reason"),
		})

	return details_by_asset


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


# BEGIN DIRECT AU MONTH END TOTALS

MONTH_END_CATEGORIES = [
    "ADT",
    "Dozer",
    "Excavator",
    "Grader",
    "Service Truck",
    "TLB",
    "Water Bowser",
    "Diesel Bowsers",
    "Drills",
    "Loader",
]


def _month_end_get_filter_value(filters, *keys):
    filters = frappe._dict(filters or {})
    for key in keys:
        value = filters.get(key)
        if value not in (None, ""):
            return value
    return None


def _month_end_category_sort(category):
    return MONTH_END_CATEGORIES.index(category) if category in MONTH_END_CATEGORIES else 999


def _month_end_percent(value):
    value = flt(value)

    if value < 0:
        return 0

    if value > 100:
        return 100

    return round(value, 1)


def _month_end_calc_row(asset_category, asset_name, required_hrs, work_hrs, mechanical_downtime):
    required_hrs = flt(required_hrs)
    work_hrs = flt(work_hrs)
    mechanical_downtime = flt(mechanical_downtime)
    available_hrs = required_hrs - mechanical_downtime

    avail_percent = _month_end_percent((available_hrs / required_hrs * 100) if required_hrs else 0)
    util_percent = _month_end_percent((work_hrs / available_hrs * 100) if available_hrs else 0)
    emp_avail_percent = _month_end_percent((mechanical_downtime / required_hrs * 100) if required_hrs else 0)

    return {
        "asset_category": asset_category,
        "asset_name": asset_name or "",
        "required_hrs": round(required_hrs, 1),
        "work_hrs": round(work_hrs, 1),
        "mechanical_downtime": round(mechanical_downtime, 3),
        "avail_percent": _month_end_percent(avail_percent),
        "util_percent": _month_end_percent(util_percent),
        "emp_avail_percent": _month_end_percent(emp_avail_percent),
        "breakdown_reason": "",
        "other_delay_reason": "",
        "is_category_total": 0 if asset_name else 1,
    }


def _asset_columns():
    return {row.Field for row in frappe.db.sql("SHOW COLUMNS FROM `tabAsset`", as_dict=True)}


def _asset_condition_and_values(categories, location):
    columns = _asset_columns()
    conditions = ["asset_category in %(categories)s"]
    values = {"categories": tuple(categories)}

    if "docstatus" in columns:
        conditions.append("docstatus = 1")

    location_field = None
    for candidate in ["location", "current_location", "custodian_location"]:
        if candidate in columns:
            location_field = candidate
            break

    if location and location_field:
        conditions.append(f"{location_field} = %(location)s")
        values["location"] = location

    return conditions, values

SPARE_SWING_PURPLE = "#e6d6ff"
SPARE_SWING_TEXT = "#4b0082"


def add_asset_identifiers(asset_set, asset_name):
    if not asset_name:
        return

    value = str(asset_name).strip()
    if not value:
        return

    asset_set.add(value)

    try:
        asset_doc = frappe.db.get_value("Asset", value, ["name", "asset_name"], as_dict=True)
        if asset_doc:
            if asset_doc.get("name"):
                asset_set.add(str(asset_doc.get("name")).strip())
            if asset_doc.get("asset_name"):
                asset_set.add(str(asset_doc.get("asset_name")).strip())
    except Exception:
        pass


def get_spare_swing_asset_map(filters):
    filters = frappe._dict(filters or {})

    start_date = _month_end_get_filter_value(filters, "from_date", "start_date")
    end_date = _month_end_get_filter_value(filters, "to_date", "end_date")
    location = _month_end_get_filter_value(filters, "location", "site", "production_site")

    if not start_date or not end_date:
        return {}

    args = {
        "start_date": start_date,
        "end_date": end_date,
    }

    conditions = [
        "mpp.docstatus < 2",
        "mpp.prod_month_start_date <= %(end_date)s",
        "mpp.prod_month_end_date >= %(start_date)s",
    ]

    if location:
        conditions.append("mpp.location = %(location)s")
        args["location"] = location

    condition_sql = " AND ".join(conditions)
    spare_map = {}

    def add_reason(asset_name, reason):
        identifiers = set()
        add_asset_identifiers(identifiers, asset_name)

        for identifier in identifiers:
            spare_map.setdefault(identifier, set()).add(reason)

    try:
        truck_rows = frappe.db.sql(f"""
            SELECT DISTINCT etl.truck AS asset_name
            FROM `tabMonthly Production Planning` mpp
            INNER JOIN `tabExcavator Truck Link` etl
                ON etl.parent = mpp.name
               AND etl.parenttype = 'Monthly Production Planning'
            WHERE {condition_sql}
              AND IFNULL(etl.truck, '') != ''
              AND IFNULL(etl.excavator, '') = ''
        """, args, as_dict=True)

        for row in truck_rows:
            add_reason(row.get("asset_name"), "Spare/Swing unit Truck")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Month End Spare/Swing Trucks")
        frappe.clear_messages()

    try:
        excavator_rows = frappe.db.sql(f"""
            SELECT DISTINCT etl.excavator AS asset_name
            FROM `tabMonthly Production Planning` mpp
            INNER JOIN `tabExcavator Truck Link` etl
                ON etl.parent = mpp.name
               AND etl.parenttype = 'Monthly Production Planning'
            WHERE {condition_sql}
              AND IFNULL(etl.excavator, '') != ''
              AND IFNULL(etl.truck, '') = ''
              AND NOT EXISTS (
                  SELECT 1
                  FROM `tabExcavator Truck Link` assigned_etl
                  WHERE assigned_etl.parent = etl.parent
                    AND assigned_etl.parenttype = etl.parenttype
                    AND assigned_etl.excavator = etl.excavator
                    AND IFNULL(assigned_etl.truck, '') != ''
              )
        """, args, as_dict=True)

        for row in excavator_rows:
            add_reason(row.get("asset_name"), "Spare/Swing unit Excavator")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Month End Spare/Swing Excavators")
        frappe.clear_messages()

    try:
        dozer_rows = frappe.db.sql(f"""
            SELECT DISTINCT dp.asset_name AS asset_name
            FROM `tabMonthly Production Planning` mpp
            INNER JOIN `tabDozers Planned` dp
                ON dp.parent = mpp.name
               AND dp.parenttype = 'Monthly Production Planning'
            WHERE {condition_sql}
              AND IFNULL(dp.asset_name, '') != ''
              AND IFNULL(dp.dozing_type, '') = ''
        """, args, as_dict=True)

        for row in dozer_rows:
            add_reason(row.get("asset_name"), "Spare/Swing unit Dozer")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Month End Spare/Swing Dozers")
        frappe.clear_messages()

    return {
        asset_name: ", ".join(sorted(reasons))
        for asset_name, reasons in spare_map.items()
    }


def is_spare_swing_asset(asset_name, spare_swing_asset_map):
    if not asset_name or not spare_swing_asset_map:
        return False

    value = str(asset_name).strip()
    if value in spare_swing_asset_map:
        return True

    identifiers = set()
    add_asset_identifiers(identifiers, value)
    return any(identifier in spare_swing_asset_map for identifier in identifiers)


def get_spare_swing_reason(asset_name, spare_swing_asset_map):
    if not asset_name or not spare_swing_asset_map:
        return ""

    value = str(asset_name).strip()
    if value in spare_swing_asset_map:
        return spare_swing_asset_map.get(value) or ""

    identifiers = set()
    add_asset_identifiers(identifiers, value)

    for identifier in identifiers:
        if identifier in spare_swing_asset_map:
            return spare_swing_asset_map.get(identifier) or ""

    return ""


def apply_spare_swing_flags(row, spare_swing_asset_map):
    reason = get_spare_swing_reason(row.get("asset_name"), spare_swing_asset_map)

    if reason:
        row["is_spare_swing_unit"] = 1
        row["spare_swing_reason"] = reason
        row["spare_swing_background"] = SPARE_SWING_PURPLE
        row["spare_swing_text_colour"] = SPARE_SWING_TEXT

    return row


def _get_submitted_assets(categories, location):
    columns = _asset_columns()

    if "asset_category" not in columns or "name" not in columns:
        return []

    conditions, values = _asset_condition_and_values(categories, location)

    rows = frappe.db.sql(
        f"""
        SELECT
            asset_category,
            name AS asset_name
        FROM `tabAsset`
        WHERE {" AND ".join(conditions)}
        ORDER BY asset_category, name
        """,
        values,
        as_dict=True,
    )

    return rows or []


def _month_end_direct_rows(filters):
    filters = frappe._dict(filters or {})

    from_date = _month_end_get_filter_value(
        filters,
        "from_date",
        "start_date",
    )

    selected_to_date = _month_end_get_filter_value(
        filters,
        "to_date",
        "end_date",
    )

    location = _month_end_get_filter_value(
        filters,
        "location",
        "site",
        "production_site",
    )

    mpp_end_date = None

    if location and from_date:
        mpp_end_date = frappe.db.get_value(
            "Monthly Production Planning",
            {
                "location": location,
                "prod_month_start_date": ("<=", from_date),
                "prod_month_end_date": (">=", from_date),
                "docstatus": ("<", 2),
            },
            "prod_month_end_date",
            order_by="prod_month_end_date desc",
        )

    possible_end_dates = [
        getdate(value)
        for value in [
            selected_to_date,
            mpp_end_date,
            nowdate(),
        ]
        if value
    ]

    to_date = min(possible_end_dates) if possible_end_dates else getdate(nowdate())

    filters["to_date"] = to_date
    filters["end_date"] = to_date
    selected_category = _month_end_get_filter_value(filters, "asset_category")
    machine_scope = _month_end_get_filter_value(filters, "machine_scope") or "Include Swing/Spare"
    spare_swing_asset_map = get_spare_swing_asset_map(filters)

    categories = [selected_category] if selected_category else list(MONTH_END_CATEGORIES)

    asset_rows = _get_submitted_assets(categories, location)
    summary_rows = summary.get_grouped_data({
        "start_date": from_date,
        "end_date": to_date,
        "location": location,
        "machine_scope": machine_scope,
    })

    other_delay_reasons_by_key = {}

    for row in summary_rows:
        if row.get("indent") != 2:
            continue

        key = (row.get("asset_category"), row.get("asset_name"))
        reason_date = row.get("shift_date") or row.get("date") or row.get("posting_date") or ""

        other_delay_reasons_by_key.setdefault(key, {
            "other_delay_reason_details": [],
        })

        if row.get("other_delay_reason"):
            other_delay_reasons_by_key[key]["other_delay_reason_details"].append({
                "date": reason_date,
                "reason": row.get("other_delay_reason"),
            })
    machines_by_category = {category: set() for category in categories}
    for row in asset_rows:
        if row.asset_category in machines_by_category and row.asset_name:
            machines_by_category[row.asset_category].add(row.asset_name)

    au_conditions = ["1=1"]
    au_values = {}

    if from_date:
        au_conditions.append("shift_date >= %(from_date)s")
        au_values["from_date"] = from_date

    if to_date:
        au_conditions.append("shift_date <= %(to_date)s")
        au_values["to_date"] = to_date

    if location:
        au_conditions.append("location = %(location)s")
        au_values["location"] = location

    au_conditions.append("asset_category in %(categories)s")
    au_values["categories"] = tuple(categories)

    au_machine_rows = frappe.db.sql(
        f"""
        SELECT
            asset_category,
            asset_name,
            SUM(COALESCE(shift_required_hours, 0)) AS required_hrs,
            SUM(COALESCE(shift_working_hours, 0)) AS work_hrs,
            SUM(COALESCE(shift_breakdown_hours, 0)) AS mechanical_downtime
        FROM `tabAvailability and Utilisation`
        WHERE {" AND ".join(au_conditions)}
          AND COALESCE(asset_name, '') != ''
        GROUP BY asset_category, asset_name
        """,
        au_values,
        as_dict=True,
    )

    au_by_key = {}
    for row in au_machine_rows:
        key = (row.asset_category, row.asset_name)
        au_by_key[key] = row

        if row.asset_category in machines_by_category and row.asset_name:
            machines_by_category[row.asset_category].add(row.asset_name)

    all_asset_names = sorted({
        asset_name
        for asset_names in machines_by_category.values()
        for asset_name in asset_names
        if asset_name
    })

    plant_breakdown_details_by_asset = get_plant_breakdown_reason_details(filters, all_asset_names)

    output = []

    for category in categories:
        machine_rows = []

        for asset_name in sorted(machines_by_category.get(category) or []):
            is_spare = is_spare_swing_asset(asset_name, spare_swing_asset_map)

            if machine_scope == "Production Machines" and is_spare:
                continue

            if machine_scope == "Swing/Spare Machines" and not is_spare:
                continue

            au_row = au_by_key.get((category, asset_name))

            breakdown_details = clean_reason_details(plant_breakdown_details_by_asset.get(asset_name) or [])
            pbm_total_minutes = sum(int(flt(d.get("total_minutes"))) for d in breakdown_details)
            pbm_mechanical_downtime = pbm_total_minutes / 60

            if au_row:
                machine_row = _month_end_calc_row(
                    category,
                    asset_name,
                    au_row.get("required_hrs"),
                    au_row.get("work_hrs"),
                    pbm_mechanical_downtime,
                )
                reason_row = other_delay_reasons_by_key.get((category, asset_name), {})

                other_delay_details = clean_reason_details(reason_row.get("other_delay_reason_details") or [])

                machine_row["breakdown_reason_details"] = breakdown_details
                machine_row["other_delay_reason_details"] = other_delay_details

                machine_row["breakdown_reason"] = "\n".join([d.get("reason") for d in breakdown_details])
                machine_row["other_delay_reason"] = "\n".join([d.get("reason") for d in other_delay_details])
            else:
                machine_row = _month_end_calc_row(category, asset_name, 0, 0, pbm_mechanical_downtime)
                machine_row["breakdown_reason_details"] = breakdown_details
                machine_row["other_delay_reason_details"] = []
                machine_row["breakdown_reason"] = "\n".join([d.get("reason") for d in breakdown_details])

            machine_rows.append(apply_spare_swing_flags(machine_row, spare_swing_asset_map))

        if not machine_rows:
            continue

        total_required = sum(flt(row.get("required_hrs")) for row in machine_rows)
        total_work = sum(flt(row.get("work_hrs")) for row in machine_rows)
        total_down = sum(flt(row.get("mechanical_downtime")) for row in machine_rows)

        category_row = _month_end_calc_row(
            category,
            "",
            total_required,
            total_work,
            total_down,
        )

        category_row["avail_percent"] = average_percent([
            row.get("avail_percent")
            for row in machine_rows
        ])

        category_row["util_percent"] = average_percent([
            row.get("util_percent")
            for row in machine_rows
        ])

        output.append(category_row)
        output.extend(machine_rows)

    for row in output:
        row["avail_percent"] = apply_au_target(
            row.get("avail_percent"),
            filters,
        )
        row["util_percent"] = apply_au_target(
            row.get("util_percent"),
            filters,
        )

    return output


def get_data(filters):
    return _month_end_direct_rows(filters)

# END DIRECT AU MONTH END TOTALS

