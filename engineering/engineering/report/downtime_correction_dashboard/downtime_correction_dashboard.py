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

	items = get_items(from_date, to_date, filters.get("site"))

	return get_columns(), [{"dashboard_html": get_dashboard_html(items)}]


def get_columns():
	return [
		{"label": _("Dashboard"), "fieldname": "dashboard_html", "fieldtype": "HTML", "width": 1200},
	]


def get_items(from_date, to_date, site=None):
	conditions = ["c.parenttype = 'Mechanical Downtime sign-off'"]
	values = {}

	if site:
		conditions.append("p.site = %(site)s")
		values["site"] = site

	rows = frappe.db.sql(
		f"""
		SELECT
			c.name,
			c.parent,
			p.site,
			c.fixes,
			c.date_time_io,
			c.date_time_p,
			c.date_time_e,
			c.comments1,
			c.comments2,
			c.comments3
		FROM `tabMechanical Downtime sign-off child` c
		LEFT JOIN `tabMechanical Downtime sign-off` p ON p.name = c.parent
		WHERE {" AND ".join(conditions)}
		ORDER BY COALESCE(c.date_time_io, c.date_time_p, c.date_time_e) DESC
		""",
		values,
		as_dict=True,
	)

	grouped = {}

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
				group_key = (row.name, str(comment_date), row.site or "", item["fleet"])

				if group_key not in grouped:
					grouped[group_key] = {
						"date": comment_date,
						"site": row.site,
						"shift": get_shift_from_parent(row.parent),
						"fleet": item["fleet"],
						"child_row": row.name,
						"fixes": row.fixes,
						"comments": [],
					}

				grouped[group_key]["comments"].append({
					"source": source,
					"comment": item["comment"],
				})

	items = []

	for item in grouped.values():
		fixed_key = make_fixed_key(
			item["child_row"],
			"Combined",
			item["date"],
			item["fleet"],
			frappe.as_json(item["comments"]),
		)
		is_fixed = get_fixed_status(item["fixes"], fixed_key)

		items.append({
			"date": item["date"],
			"site": item["site"],
			"shift": item["shift"],
			"fleet": item["fleet"],
			"child_row": item["child_row"],
			"fixed_key": fixed_key,
			"comments": item["comments"],
			"is_fixed": is_fixed,
		})

	return items


def get_dashboard_html(items):
	if not items:
		return """
			<div class="dcd-dashboard">
				<div class="dcd-empty">No downtime corrections found for this filter.</div>
			</div>
		"""

	cards = [get_card_html(item) for item in items]

	return f"""
		<div class="dcd-dashboard">
			<div class="dcd-grid">
				{''.join(cards)}
			</div>
		</div>
	"""


def get_card_html(item):
	status_class = "dcd-fixed" if item["is_fixed"] else "dcd-open"
	status_text = "Fixed" if item["is_fixed"] else "Not Fixed"
	card_class = "dcd-card-fixed" if item["is_fixed"] else "dcd-card-not-fixed"
	checked = "checked" if item["is_fixed"] else ""
	comments_json = frappe.utils.escape_html(frappe.as_json(item["comments"]))

	return f"""
		<div class="dcd-card {card_class}">
			<div class="dcd-top">
				<div class="dcd-fleet">{frappe.utils.escape_html(item["fleet"])}</div>
				<div class="dcd-status {status_class}">{status_text}</div>
			</div>

			<div class="dcd-meta">
				<div><b>Date:</b> {item["date"]} <b style="margin-left: 10px;">Shift:</b> {frappe.utils.escape_html(item["shift"] or "")}</div>
				<div><b>Site:</b> {frappe.utils.escape_html(item["site"] or "")}</div>
			</div>

			<div class="dcd-actions">
				<button class="btn btn-xs btn-default dcd-view"
					data-fleet="{frappe.utils.escape_html(item["fleet"])}"
					data-date="{item["date"]}"
					data-comments="{comments_json}">
					View Comment
				</button>

				<label class="dcd-check">
					<input type="checkbox" class="dcd-fixed-checkbox"
						data-row="{item["child_row"]}"
						data-key="{item["fixed_key"]}" {checked}>
					Fixed
				</label>
			</div>
		</div>
	"""

def get_shift_from_parent(parent_name):
	value = str(parent_name or "")

	if "Night Shift" in value:
		return "Night Shift"

	if "Day Shift" in value:
		return "Day Shift"

	return ""


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