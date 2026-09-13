# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime

from engineering.controllers.fleet_compliance import bulk_drivers, compute_all, get_expiring_threshold_days
from engineering.controllers.notifications import _get_outgoing_email_account
from engineering.engineering.doctype.fleet_management_settings.fleet_management_settings import (
	get_public_road_asset_categories,
)

DAY_NAMES = [
	"Monday",
	"Tuesday",
	"Wednesday",
	"Thursday",
	"Friday",
	"Saturday",
	"Sunday",
]

ATTENTION_STATUSES = ["Attention Required", "Non-Compliant"]


def _get_current_allocations():
	"""Base (real, stored) fields only — compliance is computed fresh per
	row via fleet_compliance.compute_all, never read from a cached column."""
	return frappe.get_all(
		"Vehicle Allocation",
		filters={"docstatus": 1, "status": "Current"},
		fields=["name", "asset", "asset_name", "location", "required_licence_type"],
	)


def _get_recipients_for_location(settings, location):
	emails = []

	for row in settings.get("recipients") or []:
		row_location = (row.location or "").strip()

		if row_location and row_location != location:
			continue

		email = frappe.db.get_value("User", row.user, "email") or row.user

		if email:
			emails.append(email)

	seen = set()
	out = []

	for e in emails:
		key = e.lower()

		if key in seen:
			continue

		seen.add(key)
		out.append(e)

	return out


def send_weekly_fleet_digest_gate():
	"""Run the weekly digest only on the configured day/hour (per Fleet
	Management Settings), once per week."""
	if not frappe.db.exists("DocType", "Fleet Management Settings"):
		return

	settings = frappe.get_single("Fleet Management Settings")

	if not settings.send_weekly_digest:
		return

	dt = now_datetime()  # server TZ
	configured_day = settings.digest_day or "Monday"
	configured_hour = settings.digest_hour if settings.digest_hour is not None else 6

	if DAY_NAMES[dt.weekday()] != configured_day or dt.hour != configured_hour:
		return

	iso_year, iso_week, _ = dt.isocalendar()
	key = f"fleet_weekly_digest_ran::{iso_year}-{iso_week}"

	if frappe.cache().get_value(key):
		return

	frappe.cache().set_value(key, 1, expires_in_sec=60 * 60 * 24 * 6)

	return send_weekly_fleet_digest(dry_run=False)


def _get_unregistered_assets():
	categories = get_public_road_asset_categories()

	if not categories:
		return []

	return frappe.db.sql(
		"""
		select a.name as asset, a.asset_name as asset_name, a.asset_category as asset_category, a.location as location
		from `tabAsset` a
		left join `tabVehicle Allocation` v on v.asset = a.name and v.docstatus = 1 and v.status = 'Current'
		where a.asset_category in %(categories)s and a.docstatus = 1 and v.name is null
		order by a.name
		""",
		{"categories": categories},
		as_dict=True,
	)


def send_weekly_fleet_digest(dry_run: bool = False):
	"""Group currently-open Vehicle Allocations needing attention — and
	unregistered public-road Assets — by Location and email the configured
	recipients for that Location. Compliance is computed fresh here (not
	read from any stored field). dry_run=True returns payloads instead of
	sending.

	Unlike the old Branch-based scheme (an allocation could have drivers
	across more than one Branch, needing a fan-out), each Vehicle
	Allocation — and each Asset — has exactly one Location, so this is a
	straight one-row-per-bucket grouping."""
	settings = frappe.get_single("Fleet Management Settings")
	threshold_days = get_expiring_threshold_days()

	flagged = []
	current_allocations = _get_current_allocations()
	drivers_by_parent = bulk_drivers([row.name for row in current_allocations])

	for row in current_allocations:
		driver_rows = drivers_by_parent.get(row.name, [])
		compliance = compute_all(
			row.asset,
			[d.driver for d in driver_rows],
			row.required_licence_type,
			threshold_days,
		)

		if compliance["overall_status"] in ATTENTION_STATUSES:
			flagged.append({**row, **compliance, "driver_rows": driver_rows})

	unregistered = _get_unregistered_assets()

	by_location = {}

	for r in flagged:
		location = (r.get("location") or "").strip() or "Unassigned"
		by_location.setdefault(location, {"flagged": [], "unregistered": []})["flagged"].append(r)

	for u in unregistered:
		location = (u.get("location") or "").strip() or "Unassigned"
		by_location.setdefault(location, {"flagged": [], "unregistered": []})["unregistered"].append(u)

	payloads = {}

	for location in sorted(by_location):
		bucket = by_location[location]
		recipients = _get_recipients_for_location(settings, None if location == "Unassigned" else location)

		lines = ["Hi Team", "", f"Location: {location}", ""]

		for r in bucket["flagged"]:
			issues = []

			if r["vehicle_licence_status"] in ("Expiring", "Expired", "Incomplete", "Outstanding"):
				issues.append(f"Vehicle Licence {r['vehicle_licence_status']}")

			if r["driver_licence_status"] in ("Expiring", "Expired", "Incomplete", "Outstanding"):
				issues.append(f"Driver Licence {r['driver_licence_status']}")

			if r["addendum_status"] == "Outstanding":
				issues.append("Company Vehicle Undertaking Outstanding")

			driver_display = ", ".join(d.driver_name or d.driver for d in r["driver_rows"]) or "no driver"

			lines.append(
				f"- {r['asset_name'] or r['asset']} — {driver_display}: {', '.join(issues) or r['overall_status']}"
			)

		if bucket["unregistered"]:
			lines.append("")
			lines.append("Unregistered public-road Assets (no Vehicle Allocation yet):")

			for u in bucket["unregistered"]:
				lines.append(f"- {u.asset_name or u.asset} ({u.asset_category})")

		if len(lines) <= 4:
			lines.append("No outstanding items.")

		total_items = len(bucket["flagged"]) + len(bucket["unregistered"])
		payloads[location] = {
			"recipients": recipients,
			"subject": f"Fleet Compliance Weekly Digest — {location} ({total_items})",
			"message": "<br>".join(lines),
		}

	if dry_run:
		return payloads

	email_account = _get_outgoing_email_account(match_by_doctype="Vehicle Allocation")

	if not email_account or not getattr(email_account, "email_id", None):
		frappe.log_error(
			"No outgoing Email Account configured/enabled. Skipping Fleet Compliance weekly digest.",
			"Fleet Compliance Weekly Digest",
		)
		return payloads

	for location, payload in payloads.items():
		if not payload["recipients"]:
			continue

		try:
			frappe.sendmail(
				recipients=payload["recipients"],
				sender=email_account.email_id,
				subject=payload["subject"],
				message=payload["message"],
				now=True,
			)
		except Exception:
			frappe.log_error(
				f"Failed to send Fleet Compliance weekly digest for location {location}",
				"Fleet Compliance Weekly Digest",
			)

	return payloads
