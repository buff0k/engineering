// availability_utilisation_report.js

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
		},
		{
			"fieldname": "site",
			"label": __("Site"),
			"fieldtype": "Link",
			"options": "Location"
		},
		{
			"fieldname": "asset_category",
			"label": __("Asset Category"),
			"fieldtype": "Link",
			"options": "Asset Category"
		},
		{
			"fieldname": "asset_name",
			"label": __("Asset Name"),
			"fieldtype": "Link",
			"options": "Asset"
		},
		{
			"fieldname": "display_by",
			"label": __("Display By"),
			"fieldtype": "Select",
			"options": "\nDays\nWeeks\nMonths",
			"default": "Months"
		}
	],
	onload: function(report) {
		// If you need to add any dynamic filter behavior, do so here.
	}
};
