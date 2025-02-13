// availability_utilisation_monthly_report.js
// Minimal configuration for the Availability & Utilisation Monthly Report

frappe.query_reports["Availability & Utilisation- Monthly"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		}
	]
};
