frappe.query_reports["Downtime mistake dashboard"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -7),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "site",
			label: __("Site"),
			fieldtype: "Link",
			options: "Location",
		},
	],

	onload: function () {
		add_downtime_mistake_dashboard_style();

		$(document).off("click", ".dmd-view").on("click", ".dmd-view", function () {
			const btn = $(this);

			frappe.msgprint({
				title: __("Downtime Mistake Comment"),
				indicator: "red",
				message: `
					<div class="dmd-popup">
						<div><b>Fleet:</b> ${btn.data("fleet")}</div>
						<div><b>From:</b> ${btn.data("source")}</div>
						<div><b>Date:</b> ${btn.data("date")}</div>
						<hr>
						<div class="dmd-popup-comment">${String(btn.data("comment")).replace(/\n/g, "<br>")}</div>
					</div>
				`,
			});
		});

		$(document).off("change", ".dmd-fixed-checkbox").on("change", ".dmd-fixed-checkbox", function () {
			const checkbox = $(this);

			frappe.call({
				method: "engineering.engineering.report.downtime_mistake_dashboard.downtime_mistake_dashboard.set_fixed_status",
				args: {
					child_row: checkbox.data("row"),
					fixed_key: checkbox.data("key"),
					fixed: checkbox.is(":checked") ? 1 : 0,
				},
				callback: function () {
					frappe.query_report.refresh();
				},
			});
		});
	},
};

function add_downtime_mistake_dashboard_style() {
	if ($("#dmd-style").length) return;

	$("head").append(`
		<style id="dmd-style">
			.dmd-fleet {
				font-weight: 700;
				font-size: 14px;
			}

			.dmd-source {
				font-size: 12px;
				color: #6b7280;
				margin-top: 3px;
			}

			.dmd-status {
				display: inline-block;
				border-radius: 999px;
				padding: 4px 10px;
				font-weight: 700;
				font-size: 12px;
			}

			.dmd-open {
				background: #fee2e2;
				color: #991b1b;
			}

			.dmd-fixed {
				background: #dcfce7;
				color: #166534;
			}

			.dmd-check {
				margin-left: 10px;
				font-weight: 600;
			}

			.dmd-popup {
				font-size: 14px;
				line-height: 1.6;
			}

			.dmd-popup-comment {
				white-space: normal;
				background: #f8fafc;
				border: 1px solid #e5e7eb;
				border-radius: 8px;
				padding: 12px;
			}
		</style>
	`);
}