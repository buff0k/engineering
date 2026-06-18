import hashlib
import re

import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate


FIXES_FIELD = "fixes"


def execute(filters=None):
	filters = filters or {}

	to_date = getdate(filters.get("to_date") or nowdate())
	from_date = getdate(filters.get("from_date") or add_days(to_date, -7))

	return get_columns(), get_data(from_date, to_date)


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 110},
		{"label": _("Fleet / Source"), "fieldname": "fleet_source", "fieldtype": "HTML", "width": 260},
		{"label": _("Status"), "fieldname": "status_html", "fieldtype": "HTML", "width": 120},
		{"label": _("Action"), "fieldname": "action_html", "fieldtype": "HTML", "width": 220},
	]


def get_data(from_date, to_date):
	rows = frappe.db.sql(
		"""
		SELECT
			c.name,
			c.parent,
			c.fixes,
			c.date_time_io,
			c.date_time_p,
			c.date_time_e,
			c.comments1,
			c.comments2,
			c.comments3
		FROM `tabMechanical Downtime sign-off child` c
		WHERE c.parenttype = 'Mechanical Downtime sign-off'
		ORDER BY COALESCE(c.date_time_io, c.date_time_p, c.date_time_e) DESC
		""",
		as_dict=True,
	)

	data = []

	for row in rows:
		comment_groups = [
			("Information Officer", row.date_time_io, row.comments1),
			("Production Manager", row.date_time_p, row.comments2),
			("Engineering Manager", row.date_time_e, row.comments3),
		]

		for source, dt, comments in comment_groups:
			if not dt or not comments:
				continue

			comment_date = getdate(dt)

			if comment_date < from_date or comment_date > to_date:
				continue

			for item in split_fleet_comments(comments):
				fixed_key = make_fixed_key(row.name, source, comment_date, item["fleet"], item["comment"])
				is_fixed = get_fixed_status(row.fixes, fixed_key)

				data.append({
					"date": comment_date,
					"fleet_source": f"""
						<div class="dmd-fleet">{frappe.utils.escape_html(item["fleet"])}</div>
						<div class="dmd-source">{frappe.utils.escape_html(source)}</div>
					""",
					"status_html": get_status_html(is_fixed),
					"action_html": get_action_html(row.name, fixed_key, item["fleet"], source, comment_date, item["comment"], is_fixed),
				})

	return data


def split_fleet_comments(text):
	blocks = []
	current_fleet = None
	current_comment = []

	for raw_line in text.splitlines():
		line = raw_line.strip()

		if not line:
			continue

		if looks_like_fleet(line):
			if current_fleet:
				blocks.append({
					"fleet": current_fleet,
					"comment": "\n".join(current_comment).strip() or "No comment",
				})

			current_fleet = line
			current_comment = []
			continue

		if current_fleet:
			current_comment.append(line)

	if current_fleet:
		blocks.append({
			"fleet": current_fleet,
			"comment": "\n".join(current_comment).strip() or "No comment",
		})

	if not blocks and text.strip():
		blocks.append({"fleet": "Unknown Fleet", "comment": text.strip()})

	return blocks


def looks_like_fleet(line):
	value = str(line or "").strip().upper()

	if len(value) > 20:
		return False

	if " " in value:
		return False

	return bool(re.match(r"^[A-Z]{2,8}\d{2,6}[A-Z]?$", value))


def make_fixed_key(child_row, source, date, fleet, comment):
	raw = f"{child_row}|{source}|{date}|{fleet}|{comment}"
	return hashlib.sha256(raw.encode()).hexdigest()


def get_fixed_status(fixes_json, fixed_key):
	fixes = frappe.parse_json(fixes_json or "{}") or {}
	return 1 if fixes.get(fixed_key) else 0


def get_status_html(is_fixed):
	if is_fixed:
		return '<span class="dmd-status dmd-fixed">Fixed</span>'

	return '<span class="dmd-status dmd-open">Open</span>'


def get_action_html(child_row, fixed_key, fleet, source, date, comment, is_fixed):
	checked = "checked" if is_fixed else ""

	return f"""
		<button class="btn btn-xs btn-default dmd-view"
			data-fleet="{frappe.utils.escape_html(fleet)}"
			data-source="{frappe.utils.escape_html(source)}"
			data-date="{date}"
			data-comment="{frappe.utils.escape_html(comment)}">
			View
		</button>

		<label class="dmd-check">
			<input type="checkbox" class="dmd-fixed-checkbox" data-row="{child_row}" data-key="{fixed_key}" {checked}>
			Fixed
		</label>
	"""


@frappe.whitelist()
def set_fixed_status(child_row, fixed_key, fixed):
	fixed = int(fixed)

	row = frappe.get_doc("Mechanical Downtime sign-off child", child_row)
	fixes = frappe.parse_json(row.fixes or "{}") or {}

	if fixed:
		fixes[fixed_key] = {
			"fixed": 1,
			"fixed_by": frappe.session.user,
			"fixed_on": frappe.utils.now(),
		}
	else:
		fixes.pop(fixed_key, None)

	row.db_set(FIXES_FIELD, frappe.as_json(fixes), update_modified=False)

	return {"ok": 1}