import hashlib
import re

import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate


FIXED_DOCTYPE = "Downtime Mistake Fixed"


def execute(filters=None):
	filters = filters or {}

	to_date = getdate(filters.get("to_date") or nowdate())
	from_date = getdate(filters.get("from_date") or add_days(to_date, -7))

	columns = get_columns()
	data = get_data(from_date, to_date)

	return columns, data


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
				is_fixed = get_fixed_status(fixed_key)

				data.append(
					{
						"date": comment_date,
						"fleet_source": f"""
							<div class="dmd-fleet">{frappe.utils.escape_html(item["fleet"])}</div>
							<div class="dmd-source">{frappe.utils.escape_html(source)}</div>
						""",
						"status_html": get_status_html(is_fixed),
						"action_html": get_action_html(fixed_key, item["fleet"], source, comment_date, item["comment"], is_fixed),
					}
				)

	return data


def split_fleet_comments(text):
	blocks = []
	lines = [line.strip() for line in text.splitlines() if line.strip()]

	current_fleet = None
	current_comment = []

	for line in lines:
		if looks_like_fleet(line):
			if current_fleet and current_comment:
				blocks.append({"fleet": current_fleet, "comment": "\n".join(current_comment).strip()})
			current_fleet = line
			current_comment = []
		else:
			current_comment.append(line)

	if current_fleet and current_comment:
		blocks.append({"fleet": current_fleet, "comment": "\n".join(current_comment).strip()})

	if not blocks and text.strip():
		blocks.append({"fleet": "Unknown Fleet", "comment": text.strip()})

	return blocks


def looks_like_fleet(line):
	if len(line) > 30:
		return False
	return bool(re.match(r"^[A-Z]{2,6}[-\s]?\d{1,5}[A-Z]?$", line.upper()))


def make_fixed_key(child_row, source, date, fleet, comment):
	raw = f"{child_row}|{source}|{date}|{fleet}|{comment}"
	return hashlib.sha256(raw.encode()).hexdigest()


def get_fixed_status(fixed_key):
	if not frappe.db.exists("DocType", FIXED_DOCTYPE):
		return 0

	return 1 if frappe.db.exists(FIXED_DOCTYPE, {"fixed_key": fixed_key}) else 0


def get_status_html(is_fixed):
	if is_fixed:
		return '<span class="dmd-status dmd-fixed">Fixed</span>'
	return '<span class="dmd-status dmd-open">Open</span>'


def get_action_html(fixed_key, fleet, source, date, comment, is_fixed):
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
			<input type="checkbox" class="dmd-fixed-checkbox" data-key="{fixed_key}" {checked}>
			Fixed
		</label>
	"""


@frappe.whitelist()
def set_fixed_status(fixed_key, fixed):
	if not frappe.db.exists("DocType", FIXED_DOCTYPE):
		frappe.throw(_("Missing helper DocType: Downtime Mistake Fixed"))

	fixed = int(fixed)

	existing = frappe.db.exists(FIXED_DOCTYPE, {"fixed_key": fixed_key})

	if fixed and not existing:
		doc = frappe.get_doc(
			{
				"doctype": FIXED_DOCTYPE,
				"fixed_key": fixed_key,
				"fixed_by": frappe.session.user,
			}
		)
		doc.insert(ignore_permissions=True)

	if not fixed and existing:
		frappe.delete_doc(FIXED_DOCTYPE, existing, ignore_permissions=True)

	frappe.db.commit()
	return {"ok": 1}