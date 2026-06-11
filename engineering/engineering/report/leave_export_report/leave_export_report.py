import frappe
from frappe.utils import getdate, now_datetime


def execute(filters=None):
	filters = filters or {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{"label": "ID", "fieldname": "name", "fieldtype": "Link", "options": "Leave Application", "width": 180},
		{"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 220},
		{"label": "Leave Type", "fieldname": "leave_type", "fieldtype": "Data", "width": 160},
		{"label": "Company", "fieldname": "company", "fieldtype": "Data", "width": 220},
		{"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 180},
		{"label": "From Date", "fieldname": "from_date", "fieldtype": "Date", "width": 120},
		{"label": "To Date", "fieldname": "to_date", "fieldtype": "Date", "width": 120},
		{"label": "Total Leave Days", "fieldname": "total_leave_days", "fieldtype": "Float", "width": 140},
		{"label": "Total Leave Hours", "fieldname": "ir_total_leave_hours", "fieldtype": "Float", "width": 140},
		{"label": "Working Days Leave", "fieldname": "ir_working_days_leave", "fieldtype": "Float", "width": 150},
		{"label": "Leave Days as per Payroll", "fieldname": "ir_leave_as_per_payroll", "fieldtype": "Float", "width": 180},
		{"label": "Signed Leave Form", "fieldname": "ir_attach_signed_leave_form", "fieldtype": "Data", "width": 220},
		{"label": "Description", "fieldname": "description", "fieldtype": "Text", "width": 300},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": "Docstatus", "fieldname": "docstatus", "fieldtype": "Int", "width": 90},
		{"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": "Creation", "fieldname": "creation", "fieldtype": "Datetime", "width": 180},
		{"label": "Modified", "fieldname": "modified", "fieldtype": "Datetime", "width": 180},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters.get("from_date"):
		conditions.append("la.from_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("la.to_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

	return frappe.db.sql(
		f"""
		SELECT
			la.name,
			la.employee,
			la.employee_name,
			la.leave_type,
			la.company,
			la.department,
			la.from_date,
			la.to_date,
			la.total_leave_days,
			la.ir_total_leave_hours,
			la.ir_working_days_leave,
			la.ir_leave_as_per_payroll,
			la.ir_attach_signed_leave_form,
			la.description,
			la.status,
			la.docstatus,
			la.posting_date,
			la.creation,
			la.modified
		FROM `tabLeave Application` la
		{where_clause}
		ORDER BY la.from_date DESC, la.employee_name ASC
		""",
		values,
		as_dict=True,
	)


@frappe.whitelist()
def export_sage_vip_txt(from_date=None, to_date=None):
	filters = {
		"from_date": from_date,
		"to_date": to_date,
	}

	rows = get_data(filters)

	lines = []
	for row in rows:
		lines.append(build_sage_vip_leave_line(row))

	content = "\r\n".join(lines)

	file_name = f"LVEXP{now_datetime().strftime('%H%M')}.txt"

	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": file_name,
		"is_private": 0,
		"content": content,
	})

	file_doc.save(ignore_permissions=True)

	return {
		"file_url": file_doc.file_url,
		"file_name": file_name,
		"rows": len(rows),
	}


def build_sage_vip_leave_line(row):
	company = "014"
	transaction_type = "1"
	employee = fixed(row.employee, 8)
	leave_type = get_sage_leave_type(row.leave_type)
	method = "1"
	reason = get_sage_leave_reason(row.leave_type)
	from_date = format_yyyymmdd(row.from_date)
	to_date = format_yyyymmdd(row.to_date)
	days = row.ir_leave_as_per_payroll or row.total_leave_days or 0
	total_taken = format_sage_amount(days)
	sign = "+"
	note_received = "N"
	reference = fixed(row.name, 15)
	doctor_name = fixed("", 20)
	practice_number = fixed("", 15)
	comment = fixed(row.description or row.employee_name or "", 50)

	return (
		"D"
		+ company
		+ "@"
		+ transaction_type
		+ employee
		+ leave_type
		+ " "
		+ method
		+ reason
		+ from_date
		+ to_date
		+ total_taken
		+ sign
		+ note_received
		+ reference
		+ doctor_name
		+ practice_number
		+ comment
		+ "Z"
	)


def fixed(value, length):
	value = str(value or "")
	value = value[:length]
	return value.ljust(length)


def format_yyyymmdd(value):
	if not value:
		return "00000000"

	return getdate(value).strftime("%Y%m%d")


def format_sage_amount(value):
	value = float(value or 0)
	value = int(round(value * 10000))
	return str(value).zfill(9)


def get_sage_leave_type(leave_type):
	mapping = {
		"Annual Leave": "A",
		"Family Responsibility": "F",
		"Sick Leave": "S",
		"Maternity Leave": "M",
		"Leave Without Pay": "U",
	}

	return mapping.get(leave_type, "A")


def get_sage_leave_reason(leave_type):
	mapping = {
		"Annual Leave": "ANN",
		"Family Responsibility": "FAM",
		"Sick Leave": "SIC",
		"Maternity Leave": "MAT",
		"Leave Without Pay": "LWP",
	}

	return mapping.get(leave_type, "ANN")