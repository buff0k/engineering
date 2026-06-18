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
			const comments = JSON.parse(btn.attr("data-comments") || "[]");

			const comments_html = comments.map(function (row) {
				return `
					<div class="dmd-comment-block">
						<div class="dmd-comment-source">${frappe.utils.escape_html(row.source || "")}</div>
						<div class="dmd-popup-comment">${frappe.utils.escape_html(row.comment || "").replace(/\n/g, "<br>")}</div>
					</div>
				`;
			}).join("");

			frappe.msgprint({
				title: __("Downtime Mistake Comment"),
				indicator: "red",
				message: `
					<div class="dmd-popup">
						<div><b>Fleet:</b> ${frappe.utils.escape_html(btn.data("fleet") || "")}</div>
						<div><b>Date:</b> ${frappe.utils.escape_html(String(btn.data("date") || ""))}</div>
						<hr>
						${comments_html}
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
			.query-report .datatable {
				background: transparent !important;
				border: none !important;
			}

			.query-report .dt-header,
			.query-report .dt-row-filter {
				display: none !important;
			}

			.query-report .dt-scrollable {
				width: 100% !important;
				max-width: 900px !important;
				margin: 16px auto 0 auto !important;
				border: none !important;
				box-shadow: none !important;
				background: transparent !important;
				overflow: visible !important;
			}

			.query-report .dt-row {
				border: none !important;
				background: transparent !important;
			}

			.query-report .dt-cell {
				border: none !important;
				background: transparent !important;
			}

			.query-report .dt-cell__content {
				padding: 0 !important;
				white-space: normal !important;
				height: auto !important;
				min-height: 0 !important;
				overflow: visible !important;
				display: block !important;
			}
			.query-report .dt-cell__content > div {
				width: 100%;
			}
			.dmd-card {
				width: 100%;
				background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
				border: 1px solid #e5e7eb;
				border-radius: 18px;
				padding: 18px;
				margin-bottom: 12px;
				box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
				box-sizing: border-box;
			}

			.dmd-card-main {
				display: flex;
				align-items: center;
				justify-content: space-between;
				gap: 14px;
			}

			.dmd-fleet-large {
				font-size: 20px;
				font-weight: 900;
				color: #0f172a;
				letter-spacing: 0.3px;
			}

			.dmd-meta {
				display: flex;
				flex-wrap: wrap;
				gap: 8px;
				margin-top: 7px;
			}

			.dmd-meta span {
				background: #f8fafc;
				border: 1px solid #e2e8f0;
				border-radius: 999px;
				padding: 4px 10px;
				font-size: 12px;
				font-weight: 700;
				color: #475569;
			}

			.dmd-card-actions {
				display: flex;
				align-items: center;
				justify-content: flex-end;
				gap: 10px;
				flex-wrap: wrap;
			}

			.dmd-status {
				display: inline-flex;
				align-items: center;
				justify-content: center;
				border-radius: 999px;
				padding: 6px 13px;
				font-weight: 900;
				font-size: 12px;
				min-width: 68px;
			}

			.dmd-open {
				background: #fee2e2;
				color: #991b1b;
				border: 1px solid #fecaca;
			}

			.dmd-fixed {
				background: #dcfce7;
				color: #166534;
				border: 1px solid #bbf7d0;
			}

			.dmd-view {
				border-radius: 999px !important;
				padding: 8px 18px !important;
				font-weight: 900 !important;
				border: 1px solid #4674e0 !important;
				background: #3165dd !important;
				color: #ffffff !important;
				box-shadow: 0 4px 10px rgba(50, 98, 211, 0.18);
			}

			.dmd-view:hover {
				background: #0f3675 !important;
				border-color: #1c64d8 !important;
			}

			.dmd-check {
				display: inline-flex;
				align-items: center;
				gap: 6px;
				font-weight: 800;
				color: #334155;
			}

			.dmd-check input {
				width: 16px;
				height: 16px;
				cursor: pointer;
			}

			.dmd-popup {
				font-size: 14px;
				line-height: 1.6;
			}

			.dmd-comment-block {
				margin-bottom: 14px;
			}

			.dmd-comment-source {
				display: inline-block;
				font-weight: 900;
				margin-bottom: 6px;
				padding: 4px 10px;
				border-radius: 999px;
				background: #eff6ff;
				color: #1d4ed8;
				border: 1px solid #bfdbfe;
			}

			.dmd-popup-comment {
				white-space: normal;
				background: #f8fafc;
				border: 1px solid #e5e7eb;
				border-radius: 12px;
				padding: 12px;
				color: #0f172a;
			}

			@media (max-width: 768px) {
				.dmd-card-main {
					align-items: flex-start;
					flex-direction: column;
				}

				.dmd-card-actions {
					width: 100%;
					justify-content: space-between;
				}
			}
		</style>
	`);
}