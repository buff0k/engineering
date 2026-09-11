frappe.query_reports["Licence Expiration"] = {
	filters: [
		{
			fieldname: "site",
			label: __("Site"),
			fieldtype: "Link",
			options: "Location",
		},
		{
			fieldname: "asset",
			label: __("Asset"),
			fieldtype: "Link",
			options: "Asset",
		},
		{
			fieldname: "asset_category",
			label: __("Asset Category"),
			fieldtype: "Link",
			options: "Asset Category",
		},
		{
			fieldname: "start_date",
			label: __("Start Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "end_date",
			label: __("End Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "view",
			label: __("View"),
			fieldtype: "Select",
			options: "Summary\nAssets",
			default: "Summary",
		},
		{
			fieldname: "bucket",
			label: __("Bucket"),
			fieldtype: "Select",
			options: "\noverdue\nd0_7\nd8_14\nd15_21\nd22_28",
			depends_on: "eval:doc.view == 'Assets'",
		},
	],
};
