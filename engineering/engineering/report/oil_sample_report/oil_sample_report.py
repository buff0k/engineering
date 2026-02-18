import frappe
from frappe import _


ALLOWED_METRICS = {
	"tan","tbn","fe","ag","al","ca","cr","cu","mg","na","ni","pb","si","sn","p","b","ba","mo","v","zn","ti",
	"v40","v100","oxi","soot","iso4","iso6","iso14","pq","profileid"
}


def execute(filters: dict | None = None):
	filters = filters or {}

	metrics = normalize_metrics(filters.get("metrics"))
	if not metrics:
		metrics = ["fe"]

	columns = get_columns(metrics)
	rows = get_data(filters, metrics)

	chart = get_chart(rows, metrics, (filters.get("chart_type") or "Bar"))
	report_summary = get_report_summary(rows, metrics)

	return columns, rows, None, chart, report_summary


def normalize_metrics(raw) -> list[str]:
	# MultiSelectList can arrive as list or comma-separated string
	if raw is None:
		return []
	if isinstance(raw, list):
		items = raw
	else:
		items = [x.strip() for x in str(raw).split(",") if x.strip()]

	out = []
	for m in items:
		m = (m or "").strip()
		if m in ALLOWED_METRICS and m not in out:
			out.append(m)
	return out


@frappe.whitelist()
def get_locations():
	# Select filter needs a list of strings
	return [d.name for d in frappe.get_all("Location", fields=["name"], order_by="name asc")]


@frappe.whitelist()
def get_assets(location="All"):
	# If location is "All" -> return all assets
	filters = {}
	if location and location != "All":
		filters["location"] = location

	return [d.name for d in frappe.get_all("Asset", filters=filters, fields=["name"], order_by="name asc")]

def get_columns(metrics: list[str]) -> list[dict]:
	cols = [
		{"label": _("Asset"), "fieldname": "asset", "fieldtype": "Link", "options": "Asset", "width": 240},

	]

	for m in metrics:
		cols.append(
			{"label": _(m.upper()), "fieldname": f"m__{m}", "fieldtype": "Float", "width": 120}
		)

	cols += [
		{"label": _("Sample Date"), "fieldname": "sampledate", "fieldtype": "Date", "width": 120},
		{"label": _("Location"), "fieldname": "location", "fieldtype": "Data", "width": 170},
		{"label": _("Sample No"), "fieldname": "sampno", "fieldtype": "Data", "width": 140},
		{"label": _("Comments"), "fieldname": "commentstext", "fieldtype": "Small Text", "width": 260},
		{"label": _("Actions"), "fieldname": "actiontext", "fieldtype": "Small Text", "width": 260},
	]
	return cols

def normalize_assets(raw) -> list[str]:
	if not raw:
		return []
	if isinstance(raw, list):
		return [x for x in raw if x]
	return [x.strip() for x in str(raw).split(",") if x.strip()]


def get_data(filters: dict, metrics: list[str]) -> list[dict]:

	conditions = []
	params: dict = {}

	start_date = filters.get("start_date")
	end_date = filters.get("end_date")
	if not start_date or not end_date:
		end_date = frappe.utils.nowdate()
		start_date = frappe.utils.add_days(end_date, -30)

	conditions.append("sampledate between %(start_date)s and %(end_date)s")
	params["start_date"] = start_date
	params["end_date"] = end_date

	location = (filters.get("location") or "").strip()
	if location:
		conditions.append("location = %(location)s")
		params["location"] = location

	assets = normalize_assets(filters.get("assets"))
	if assets:
		conditions.append("asset in %(assets)s")
		params["assets"] = tuple(assets)



	include_zero = int(filters.get("include_zero") or 0)
	if not include_zero:
		# exclude rows where ALL selected metrics are 0
		conditions.append("(" + " or ".join([f"ifnull({m}, 0) != 0" for m in metrics]) + ")")


	where_sql = " and ".join(conditions)

	# Pick the row with the MAX of the FIRST selected metric per asset in the date range
	rank_metric = metrics[0]
	metric_select_sql = ", ".join([f"cast({m} as decimal(18,6)) as {m}" for m in metrics])

	rows = frappe.db.sql(
		f"""
		select
			t.asset,
			t.sampledate,
			t.location,
			t.sampno,
			{", ".join([f"t.{m}" for m in metrics])},
			t.commentstext,
			t.actiontext
		from (
			select
				asset,
				sampledate,
				location,
				sampno,
				{metric_select_sql},
				commentstext,
				actiontext,
				row_number() over (
					partition by asset
					order by ifnull({rank_metric}, 0) desc, sampledate desc, modified desc
				) as rn
			from `tabWearCheck Results`
			where {where_sql}
		) t
		where t.rn = 1
		order by ifnull(t.{rank_metric}, 0) desc, t.asset asc
		""",
		params,
		as_dict=True,
	)

	# map raw metric fields -> m__* so your table columns populate
	for r in rows:
		for m in metrics:
			r[f"m__{m}"] = r.get(m)



	top_n = int(filters.get("top_n") or 0)
	if top_n and top_n > 0:
		rows = rows[:top_n]

	return rows


def get_chart(rows: list[dict], metrics: list[str], chart_type: str) -> dict:
	labels = [r["asset"] for r in rows]
	ctype = "bar" if (chart_type or "").lower().startswith("b") else "line"

	datasets = []
	for m in metrics:
		datasets.append(
			{"name": m.upper(), "values": [float(r.get(m) or 0) for r in rows]}
		)

	colors = [
		"#2563EB", "#7C3AED", "#06B6D4", "#22C55E", "#F59E0B",
		"#EF4444", "#0EA5E9", "#A855F7", "#14B8A6", "#84CC16"
	]

	return {
		"data": {"labels": labels, "datasets": datasets},
		"type": ctype,
		"colors": colors[: max(1, len(datasets))],
	}



def get_report_summary(rows: list[dict], metrics: list[str]) -> list[dict]:
	first = metrics[0]
	values = [float(r.get(first) or 0) for r in rows]

	if not values:
		return [
			{"label": _("Assets"), "value": 0, "indicator": "grey"},
			{"label": _("Metrics"), "value": ", ".join([m.upper() for m in metrics]), "indicator": "blue"},
		]

	count = len(values)
	_min = min(values)
	_max = max(values)
	_avg = sum(values) / count

	return [
		{"label": _("Assets"), "value": count, "indicator": "blue"},
		{"label": _("Metrics"), "value": ", ".join([m.upper() for m in metrics]), "indicator": "blue"},
	]


