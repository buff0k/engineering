// Copyright (c) 2026, BuFf0k and contributors
// For license information, please see license.txt

frappe.query_reports["Availability and Utilisation Month End Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start()
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_end()
		},
		{
			fieldname: "location",
			label: __("Production Site"),
			fieldtype: "Link",
			options: "Location"
		},
		{
			fieldname: "asset_category",
			label: __("Asset Category"),
			fieldtype: "Select",
			options: "\nADT\nDozer\nExcavator\nRigid"
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) {
			return value;
		}




		if (data.is_separator) {
			return "";
		}

		if (data.is_category_total) {
			return `
				<span style="
					display: block;
					padding: 2px 4px;
					color: #0f172a;
					font-weight: 800;
					font-size: 14px;
					border-bottom: 2px solid #94a3b8;
				">
					${value || ""}
				</span>
			`;
		}




		const percent_fields = [
			"avail_percent",
			"util_percent",
			"emp_avail_percent"
		];

		if (percent_fields.includes(column.fieldname)) {
			const raw_value = flt(data[column.fieldname]);

			let bg = "#fee2e2";
			let color = "#991b1b";

			if (raw_value >= 90) {
				bg = "#dcfce7";
				color = "#166534";
			} else if (raw_value >= 75) {
				bg = "#fef9c3";
				color = "#854d0e";
			}

			return `
				<span style="
					display: inline-block;
					min-width: 70px;
					text-align: center;
					padding: 4px 10px;
					border-radius: 999px;
					background: ${bg};
					color: ${color};
					font-weight: 700;
					font-size: 12px;
				">
					${value}
				</span>
			`;
		}

		if (column.fieldname === "asset_category") {
			return `
				<span style="
					display: inline-block;
					padding: 4px 10px;
					border-radius: 8px;
					background: #eef2ff;
					color: #3730a3;
					font-weight: 700;
				">
					${value}
				</span>
			`;
		}

		if (column.fieldname === "mechanical_downtime" && flt(data.mechanical_downtime) > 0) {
			return `
				<span style="
					color: #b91c1c;
					font-weight: 700;
				">
					${value}
				</span>
			`;
		}

		if (column.fieldname === "work_hrs" || column.fieldname === "required_hrs") {
			return `
				<span style="
					color: #0f172a;
					font-weight: 700;
				">
					${value}
				</span>
			`;
		}

		return value;
	}
};