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
			.query-report .dt-scrollable {
				border-radius: 14px;
				border: 1px solid #e5e7eb;
				overflow: hidden;
				box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
			}

			.query-report .dt-header .dt-cell__content {
				font-weight: 800;
				color: #334155;
				text-align: center;
			}

			.query-report .dt-cell__content {
				display: flex;
				align-items: center;
				justify-content: center;
				min-height: 38px;
			}

			.dmd-fleet {
				display: inline-flex;
				align-items: center;
				justify-content: center;
				min-width: 82px;
				border-radius: 999px;
				padding: 6px 12px;
				background: #f8fafc;
				border: 1px solid #cbd5e1;
				color: #0f172a;
				font-weight: 900;
				font-size: 13px;
				letter-spacing: 0.3px;
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
				padding: 6px 14px !important;
				font-weight: 800 !important;
				border: 1px solid #cbd5e1 !important;
				background: #ffffff !important;
				color: #0f172a !important;
				box-shadow: 0 2px 6px rgba(15, 23, 42, 0.08);
			}

			.dmd-view:hover {
				background: #f8fafc !important;
				border-color: #94a3b8 !important;
			}

			.dmd-check {
				display: inline-flex;
				align-items: center;
				gap: 6px;
				margin-left: 12px;
				font-weight: 800;
				color: #334155;
			}

			.dmd-check input {
				width: 15px;
				height: 15px;
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
		</style>
	`);
}