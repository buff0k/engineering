# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime

from engineering.controllers.fleet_compliance import compute_all, get_expiring_threshold_days
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
		fields=["name", "asset", "asset_name", "location", "driver", "driver_name", "driver_branch", "required_licence_type"],
	)


def _get_recipients_for_branch(settings, branch):
	emails = []

	for row in settings.get("recipients") or []:
		row_branch = (row.branch or "").strip()

		if row_branch and row_branch != branch:
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
		select a.name as asset, a.asset_name as asset_name, a.asset_category as asset_category
		from `tabAsset` a
		left join `tabVehicle Allocation` v on v.asset = a.name and v.docstatus = 1 and v.status = 'Current'
		where a.asset_category in %(categories)s and a.docstatus < 2 and v.name is null
		order by a.name
		""",
		{"categories": categories},
		as_dict=True,
	)


def send_weekly_fleet_digest(dry_run: bool = False):
	"""Group currently-open Vehicle Allocations needing attention by the
	driver's Branch and email the configured recipients; also surfaces
	unregistered public-road Assets. Compliance is computed fresh here (not
	read from any stored field). dry_run=True returns payloads instead of
	sending."""
	settings = frappe.get_single("Fleet Management Settings")
	threshold_days = get_expiring_threshold_days()

	flagged = []

	for row in _get_current_allocations():
		compliance = compute_all(row.asset, row.driver, row.required_licence_type, threshold_days)

		if compliance["overall_status"] in ATTENTION_STATUSES:
			flagged.append({**row, **compliance})

	unregistered = _get_unregistered_assets()

	by_branch = {}

	for r in flagged:
		branch = (r.get("driver_branch") or "Unassigned").strip() or "Unassigned"
		by_branch.setdefault(branch, []).append(r)

	branches = sorted(by_branch) or (["Unassigned"] if unregistered else [])
	payloads = {}

	for branch in branches:
		branch_rows = by_branch.get(branch, [])
		recipients = _get_recipients_for_branch(settings, None if branch == "Unassigned" else branch)

		lines = ["Hi Team", "", f"Branch: {branch}", ""]

		for r in branch_rows:
			issues = []

			if r["vehicle_licence_status"] in ("Expiring", "Expired", "Incomplete", "Outstanding"):
				issues.append(f"Vehicle Licence {r['vehicle_licence_status']}")

			if r["driver_licence_status"] in ("Expiring", "Expired", "Incomplete", "Outstanding"):
				issues.append(f"Driver Licence {r['driver_licence_status']}")

			if r["addendum_status"] == "Outstanding":
				issues.append("Company Vehicle Undertaking Outstanding")

			lines.append(
				f"- {r['asset_name'] or r['asset']} ({r['location'] or 'no location'})"
				f" — {r['driver_name'] or r['driver'] or 'no driver'}: {', '.join(issues) or r['overall_status']}"
			)

		if branch == "Unassigned" and unregistered:
			lines.append("")
			lines.append("Unregistered public-road Assets (no Vehicle Allocation yet):")

			for u in unregistered:
				lines.append(f"- {u.asset_name or u.asset} ({u.asset_category})")

		if len(lines) <= 4:
			lines.append("No outstanding items.")

		payloads[branch] = {
			"recipients": recipients,
			"subject": f"Fleet Compliance Weekly Digest — {branch} ({len(branch_rows)})",
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

	for branch, payload in payloads.items():
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
				f"Failed to send Fleet Compliance weekly digest for branch {branch}",
				"Fleet Compliance Weekly Digest",
			)

	return payloads
