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
			options: `
ADT
Dozer
Excavator
Grader
Service Truck
TLB
Water Bowser
Diesel Bowsers
Drills`
		},
		{
			fieldname: "machine_scope",
			label: __("Machine Filter"),
			fieldtype: "Select",
			options: [
				"Production Machines",
				"Swing/Spare Machines",
				"Include Swing/Spare"
			].join("\n"),
			default: "Include Swing/Spare",
			reqd: 1
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

		if (column.fieldname === "breakdown_reason" || column.fieldname === "other_delay_reason") {
			const detail_field = column.fieldname === "breakdown_reason"
				? "breakdown_reason_details"
				: "other_delay_reason_details";

			let details = data[detail_field] || [];

			if (!details.length && data[column.fieldname]) {
				details = [{
					date: "",
					reason: data[column.fieldname]
				}];
			}

			if (!details.length) {
				return "";
			}

			window.au_month_end_reason_details = window.au_month_end_reason_details || {};

			const key = `${column.fieldname}-${data.asset_name || ""}-${Math.random()}`;
			window.au_month_end_reason_details[key] = details;

			const title = column.fieldname === "breakdown_reason"
				? "Breakdown Reasons"
				: "Other Delay Reasons";

			const button_style = data.is_spare_swing_unit
				? "background:#e6d6ff;color:#4b0082;border:1px solid #7b2cbf;"
				: "background:#dbeafe;color:#1d4ed8;border:1px solid #2563eb;";

			return `
				<button class="btn btn-xs"
					style="
						${button_style}
						font-weight:800;
						border-radius:999px;
						padding:3px 12px;
					"
					onclick="window.show_au_month_end_reason_dialog('${key}', '${title}', '${frappe.utils.escape_html(data.asset_name || '')}', '${data.is_spare_swing_unit ? "purple" : "blue"}')">
					View
				</button>
			`;
		}


		if (data.is_spare_swing_unit) {
			const reason = data.spare_swing_reason || "Spare/Swing unit in Monthly Production Planning";

			return `
				<span style="
					display: block;
					margin: -8px -10px;
					padding: 8px 10px;
					background: #e6d6ff;
					color: #4b0082;
					font-weight: 700;
					border-left: 3px solid #7b2cbf;
					min-height: 100%;
				" title="${frappe.utils.escape_html ? frappe.utils.escape_html(reason) : reason}">
					${value || ""}
				</span>
			`;
		}

		if (data.is_category_total) {
			if (!value || String(value).trim() === "") {
				return "";
			}

			return `
				<span style="
					display: block;
					padding: 2px 4px;
					color: #0f172a;
					font-weight: 800;
					font-size: 14px;
					border-bottom: 2px solid #94a3b8;
				">
					${value}
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

			if (column.fieldname === "avail_percent") {
				if (raw_value >= 85) {
					bg = "#dcfce7";
					color = "#166534";
				} else if (raw_value >= 75) {
					bg = "#fef9c3";
					color = "#854d0e";
				}
			} else if (column.fieldname === "util_percent") {
				if (raw_value >= 80) {
					bg = "#dcfce7";
					color = "#166534";
				} else if (raw_value >= 70) {
					bg = "#fef9c3";
					color = "#854d0e";
				}
			} else if (column.fieldname === "emp_avail_percent") {
				if (raw_value >= 85) {
					bg = "#dcfce7";
					color = "#166534";
				} else if (raw_value >= 75) {
					bg = "#fef9c3";
					color = "#854d0e";
				}
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

window.show_au_month_end_reason_dialog = function(key, title, asset_name, theme) {
	const details = (window.au_month_end_reason_details || {})[key] || [];

	const colours = theme === "purple"
		? {
			border: "#7b2cbf",
			header_bg: "#e6d6ff",
			head_bg: "#f3e8ff",
			text: "#4b0082",
			line: "#eadcff",
		}
		: {
			border: "#2563eb",
			header_bg: "#dbeafe",
			head_bg: "#eff6ff",
			text: "#1d4ed8",
			line: "#dbeafe",
		};

	const format_total_time = function(start_datetime, resolved_datetime) {
		if (!start_datetime || !resolved_datetime) {
			return "Open";
		}

		const start = moment(start_datetime);
		const resolved = moment(resolved_datetime);

		if (!start.isValid() || !resolved.isValid() || resolved.isBefore(start)) {
			return "-";
		}

		const total_minutes = resolved.diff(start, "minutes");
		const hours = Math.floor(total_minutes / 60);
		const minutes = total_minutes % 60;

		if (hours && minutes) {
			return `${hours}h ${minutes}m`;
		}

		if (hours) {
			return `${hours}h`;
		}

		return `${minutes}m`;
	};

	const has_times = details.some(detail => detail.start_datetime || detail.resolved_datetime);

	const header = has_times
		? `
			<tr style="background:${colours.head_bg};color:${colours.text};">
				<th style="padding:8px 10px;text-align:left;width:160px;">Start</th>
				<th style="padding:8px 10px;text-align:left;width:160px;">Resolved</th>
				<th style="padding:8px 10px;text-align:left;width:110px;">Total Time</th>
				<th style="padding:8px 10px;text-align:left;">Reason</th>
			</tr>
		`
		: `
			<tr style="background:${colours.head_bg};color:${colours.text};">
				<th style="padding:8px 10px;text-align:left;width:130px;">Date</th>
				<th style="padding:8px 10px;text-align:left;">Reason</th>
			</tr>
		`;

	const rows = details.map(detail => {
		const date_value = frappe.utils.escape_html(detail.date || "");
		const start_value = frappe.utils.escape_html(detail.start_datetime || "");
		const resolved_value = frappe.utils.escape_html(detail.resolved_datetime || "");
		const total_time_value = frappe.utils.escape_html(format_total_time(detail.start_datetime, detail.resolved_datetime));
		const reason_value = frappe.utils.escape_html(detail.reason || "");

		if (has_times) {
			return `
				<tr>
					<td style="padding:8px 10px;border-bottom:1px solid ${colours.line};font-weight:700;white-space:nowrap;">
						${start_value || "-"}
					</td>
					<td style="padding:8px 10px;border-bottom:1px solid ${colours.line};font-weight:700;white-space:nowrap;">
						${resolved_value || "Open"}
					</td>
					<td style="padding:8px 10px;border-bottom:1px solid ${colours.line};font-weight:700;white-space:nowrap;">
						${total_time_value}
					</td>
					<td style="padding:8px 10px;border-bottom:1px solid ${colours.line};">
						${reason_value}
					</td>
				</tr>
			`;
		}

		return `
			<tr>
				<td style="padding:8px 10px;border-bottom:1px solid ${colours.line};font-weight:700;white-space:nowrap;">
					${date_value || "-"}
				</td>
				<td style="padding:8px 10px;border-bottom:1px solid ${colours.line};">
					${reason_value}
				</td>
			</tr>
		`;
	}).join("");

	const dialog = new frappe.ui.Dialog({
		title: `${title} - ${asset_name || ""}`,
		size: "large"
	});

	dialog.$body.html(`
		<div style="border:1px solid ${colours.border};border-radius:10px;overflow:hidden;">
			<div style="background:${colours.header_bg};color:${colours.text};font-weight:900;padding:10px 12px;">
				${frappe.utils.escape_html(title)} for ${frappe.utils.escape_html(asset_name || "Machine")}
			</div>

			<table style="width:100%;border-collapse:collapse;">
				<thead>
					${header}
				</thead>
				<tbody>
					${rows || `<tr><td colspan="4" style="padding:10px;">No reasons found.</td></tr>`}
				</tbody>
			</table>
		</div>
	`);

	dialog.show();
};