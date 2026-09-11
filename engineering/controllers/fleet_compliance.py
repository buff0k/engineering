# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

"""Shared fleet-compliance derivation logic, reused by Vehicle Allocation's
virtual fields (computed live, never stored — see that doctype's controller),
the Fleet Compliance Overview report, the Fleet Management dashboard Number
Cards, and the notifications controller — so there is exactly one place that
decides what "Valid" / "Expiring" / "Outstanding" mean.

Nothing here re-enters licence/undertaking data, and nothing here is cached:
every call reads straight from the existing sources of truth (ir's Employee
Induction Record, the driver's own Employee Records table, and this app's
Vehicle Licence) at read time."""

import frappe
from frappe.utils import add_days, cint, escape_html, getdate, nowdate

COMPANY_VEHICLE_UNDERTAKING = "Company Vehicle Undertaking"

# ---------------------------------------------------------------------
# SA driving-licence code hierarchy: a holder of a higher/combination code
# is legally entitled to drive anything a lower code covers (K53 code
# hierarchy). Keyed by short code; value is the set of codes (including
# itself) that a holder of that code is authorised to drive.
# ---------------------------------------------------------------------
LICENCE_CODE_AUTHORISES = {
	"B": {"B"},
	"C1": {"C1", "B"},
	"C": {"C", "C1", "B"},
	"EB": {"EB", "B"},
	"EC1": {"EC1", "C1", "EB", "B"},
	"EC": {"EC", "C", "EC1", "C1", "EB", "B"},
}

LICENCE_CODE_TO_INDUCTION_NAME = {
	"B": "Drivers Licence - Code B",
	"EB": "Drivers Licence - Code EB",
	"C": "Drivers Licence - Code C",
	"EC": "Drivers Licence - Code EC",
	"C1": "Drivers Licence - Code C1",
	"EC1": "Drivers Licence - Code EC1",
}
INDUCTION_NAME_TO_LICENCE_CODE = {v: k for k, v in LICENCE_CODE_TO_INDUCTION_NAME.items()}


def qualifying_licence_names(required_licence_type):
	"""Every Employee Induction (licence code) that legally entitles someone
	to drive whatever `required_licence_type` requires — i.e. the required
	code itself plus every higher code in the SA hierarchy. Falls back to an
	exact-match-only list for any licence type outside the standard 6 codes."""
	code = INDUCTION_NAME_TO_LICENCE_CODE.get(required_licence_type)

	if not code:
		return [required_licence_type]

	holder_codes = [c for c, authorises in LICENCE_CODE_AUTHORISES.items() if code in authorises]

	return [LICENCE_CODE_TO_INDUCTION_NAME[c] for c in holder_codes]


def get_expiring_threshold_days() -> int:
	try:
		days = frappe.db.get_single_value("Fleet Management Settings", "expiring_threshold_days")
	except Exception:
		days = None

	return cint(days) or 90


def _status_from_valid_to(valid_to, threshold_days, today):
	if not valid_to:
		return "Outstanding"

	if valid_to < today:
		return "Expired"

	if valid_to <= add_days(today, threshold_days):
		return "Expiring"

	return "Valid"


def compute_driver_licence_status(driver, required_licence_type, threshold_days=None):
	"""A driver is compliant if they hold ANY currently-submitted Employee
	Induction Record for the required code, or for a higher code in the SA
	licence hierarchy that legally covers it (e.g. a Code C holder may
	legally drive a Code C1 vehicle). Among all qualifying records, the one
	with the furthest valid_to is used."""
	if threshold_days is None:
		threshold_days = get_expiring_threshold_days()

	if not driver:
		return None, "Not Applicable", None

	if not required_licence_type:
		# A driver is assigned but nobody has said which licence code this
		# Asset requires — that is itself a compliance gap, not "N/A".
		return None, "Outstanding", None

	if not frappe.db.exists("DocType", "Employee Induction Record"):
		return None, "Outstanding", None

	qualifying_names = qualifying_licence_names(required_licence_type)

	records = frappe.get_all(
		"Employee Induction Record",
		filters={"employee": driver, "training": ["in", qualifying_names], "docstatus": 1},
		fields=["name", "valid_to"],
		order_by="valid_to desc",
		limit_page_length=1,
	)

	if not records:
		return None, "Outstanding", None

	row = records[0]
	valid_to = getdate(row.valid_to) if row.valid_to else None
	today = getdate(nowdate())

	return valid_to, _status_from_valid_to(valid_to, threshold_days, today), row.name


def compute_addendum_status(driver):
	"""Look up the 'Company Vehicle Undertaking' entry in the driver's own
	Employee Records table (Employee.ir_employee_records) rather than storing
	a duplicate upload anywhere — the returned value is the actual file URL
	already on that record, read fresh every time."""
	if not driver:
		return "Not Applicable", None, None

	if not frappe.db.exists("DocType", "Employee") or not frappe.get_meta("Employee").has_field(
		"ir_employee_records"
	):
		return "Outstanding", None, None

	rows = frappe.get_all(
		"Employee File Records",
		filters={"parent": driver, "parenttype": "Employee", "record_type": COMPANY_VEHICLE_UNDERTAKING},
		fields=["attach", "date_captured"],
		order_by="date_captured desc, idx desc",
		limit_page_length=1,
	)

	if not rows or not rows[0].attach:
		return "Outstanding", None, None

	return "On File", rows[0].date_captured, rows[0].attach


def compute_vehicle_licence_status(asset, threshold_days=None):
	"""The current Vehicle Licence for an Asset is simply the most recently
	*issued* submitted one — by construction that is never the superseded
	one, so there is no need to depend on Vehicle Licence's own (also
	virtual) status field here."""
	if threshold_days is None:
		threshold_days = get_expiring_threshold_days()

	if not asset or not frappe.db.exists("DocType", "Vehicle Licence"):
		return None, "Outstanding", None

	records = frappe.get_all(
		"Vehicle Licence",
		filters={"fleet_number": asset, "docstatus": 1},
		fields=["name", "expiry_date"],
		order_by="issue_date desc",
		limit_page_length=1,
	)

	if not records:
		return None, "Outstanding", None

	row = records[0]
	valid_to = getdate(row.expiry_date) if row.expiry_date else None
	today = getdate(nowdate())

	return valid_to, _status_from_valid_to(valid_to, threshold_days, today), row.name


def compute_overall_status(vehicle_licence_status, driver, driver_licence_status, addendum_status):
	non_compliant_flags = [vehicle_licence_status in ("Expired", "Outstanding")]

	if driver:
		non_compliant_flags.append(driver_licence_status in ("Expired", "Outstanding"))
		non_compliant_flags.append(addendum_status == "Outstanding")

	if any(non_compliant_flags):
		return "Non-Compliant"

	expiring_flags = [vehicle_licence_status == "Expiring"]

	if driver:
		expiring_flags.append(driver_licence_status == "Expiring")

	if any(expiring_flags):
		return "Attention Required"

	return "Compliant"


def render_service_history_html(asset, limit=10):
	if not asset or not frappe.db.exists("DocType", "Plant Breakdown or Maintenance"):
		return "<p class='text-muted'>No service history available.</p>"

	rows = frappe.get_all(
		"Plant Breakdown or Maintenance",
		filters={"asset_name": asset},
		fields=["name", "breakdown_start_datetime", "resolved_datetime", "open_closed"],
		order_by="breakdown_start_datetime desc",
		limit_page_length=limit,
	)

	if not rows:
		return "<p class='text-muted'>No breakdown/maintenance history recorded for this Asset.</p>"

	body_rows = []

	for r in rows:
		status_colour = "orange" if (r.open_closed or "").lower() == "open" else "green"
		body_rows.append(
			"<tr>"
			f"<td><a href='/app/plant-breakdown-or-maintenance/{escape_html(r.name)}'>{escape_html(r.name)}</a></td>"
			f"<td>{escape_html(str(r.breakdown_start_datetime or ''))}</td>"
			f"<td>{escape_html(str(r.resolved_datetime or ''))}</td>"
			f"<td style='color:{status_colour}; font-weight:600;'>{escape_html(r.open_closed or '')}</td>"
			"</tr>"
		)

	return (
		"<table class='table table-bordered' style='margin-bottom:0;'>"
		"<thead><tr><th>Record</th><th>Start</th><th>Resolved</th><th>Status</th></tr></thead>"
		f"<tbody>{''.join(body_rows)}</tbody>"
		"</table>"
	)


def compute_all(asset, driver, required_licence_type, threshold_days=None):
	"""Bulk-friendly single entry point: returns every compliance field as a
	dict, for callers (the report, dashboard number cards, notifications)
	that loop many allocations and don't want to load a full Document (and
	therefore its virtual-field properties) per row."""
	if threshold_days is None:
		threshold_days = get_expiring_threshold_days()

	vehicle_licence_valid_to, vehicle_licence_status, vehicle_licence_source = compute_vehicle_licence_status(
		asset, threshold_days
	)

	if driver:
		driver_licence_valid_to, driver_licence_status, driver_licence_source = compute_driver_licence_status(
			driver, required_licence_type, threshold_days
		)
		addendum_status, addendum_date, addendum_url = compute_addendum_status(driver)
	else:
		driver_licence_valid_to, driver_licence_status, driver_licence_source = None, "Not Applicable", None
		addendum_status, addendum_date, addendum_url = "Not Applicable", None, None

	overall_status = compute_overall_status(vehicle_licence_status, driver, driver_licence_status, addendum_status)

	return {
		"vehicle_licence_valid_to": vehicle_licence_valid_to,
		"vehicle_licence_status": vehicle_licence_status,
		"vehicle_licence_source": vehicle_licence_source,
		"driver_licence_valid_to": driver_licence_valid_to,
		"driver_licence_status": driver_licence_status,
		"driver_licence_source": driver_licence_source,
		"addendum_status": addendum_status,
		"addendum_date": addendum_date,
		"addendum_url": addendum_url,
		"overall_status": overall_status,
	}
