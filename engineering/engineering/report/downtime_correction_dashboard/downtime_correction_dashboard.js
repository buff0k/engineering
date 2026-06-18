frappe.query_reports["Downtime Correction Dashboard"] = {
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
		add_downtime_correction_dashboard_style();
		add_open_downtime_button();
		bind_downtime_correction_dashboard_events();
	},

	after_datatable_render: function () {
		render_downtime_correction_dashboard_html();
	},

	formatter: function () {
		return "";
	},
};

function render_downtime_correction_dashboard_html() {
	const report = frappe.query_report;

	if (!report || !report.data || !report.data.length) return;

	const html = report.data[0].dashboard_html || "";

	$(".dcd-dashboard-holder").remove();

	const wrapper = report.$report || $(".query-report");
	const datatable_wrapper = wrapper.find(".datatable").closest(".dt-scrollable, .datatable-wrapper, .frappe-datatable").first();

	if (datatable_wrapper.length) {
		datatable_wrapper.before(`<div class="dcd-dashboard-holder">${html}</div>`);
	} else {
		wrapper.prepend(`<div class="dcd-dashboard-holder">${html}</div>`);
	}

	wrapper.find(".dt-scrollable, .datatable-wrapper, .frappe-datatable").hide();
}

function add_open_downtime_button() {
	setTimeout(function () {
		if ($(".dcd-open-downtime").length) return;

		frappe.query_report.page.add_inner_button(__("Open Downtime"), function () {
			window.open("https://www.isambane.co.za/desk/plant-breakdown-or-maintenance", "_blank");
		}).addClass("dcd-open-downtime");
	}, 300);
}


function bind_downtime_correction_dashboard_events() {
	$(document).off("click", ".dcd-view").on("click", ".dcd-view", function () {
		const btn = $(this);
		const comments = JSON.parse(btn.attr("data-comments") || "[]");

		const comments_html = comments.map(function (row) {
			return `
				<div class="dcd-comment-block">
					<div class="dcd-comment-source">${frappe.utils.escape_html(row.source || "")}</div>
					<div class="dcd-popup-comment">${frappe.utils.escape_html(row.comment || "").replace(/\n/g, "<br>")}</div>
				</div>
			`;
		}).join("");

		frappe.msgprint({
			title: __("Downtime Correction Comment"),
			indicator: "red",
			message: `
				<div class="dcd-popup">
					<div><b>Fleet:</b> ${frappe.utils.escape_html(btn.data("fleet") || "")}</div>
					<div><b>Date:</b> ${frappe.utils.escape_html(String(btn.data("date") || ""))}</div>
					<hr>
					${comments_html}
				</div>
			`,
		});
	});

	$(document).off("change", ".dcd-fixed-checkbox").on("change", ".dcd-fixed-checkbox", function () {
		const checkbox = $(this);

		frappe.call({
			method: "engineering.engineering.report.downtime_correction_dashboard.downtime_correction_dashboard.set_fixed_status",
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
}

function add_downtime_correction_dashboard_style() {
	if ($("#dcd-style").length) return;

	$("head").append(`
		<style id="dcd-style">
			.dcd-dashboard-holder {
				padding: 16px 0;
			}

			.query-report .report-wrapper .dt-scrollable,
			.query-report .report-wrapper .datatable-wrapper,
			.query-report .report-wrapper .frappe-datatable {
				display: none !important;
			}

			.dcd-dashboard {
				padding: 4px 0 24px 0;
			}

			.dcd-grid {
				display: grid;
				grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
				gap: 16px;
			}

			.dcd-card {
				background: #ffffff;
				border: 1px solid #e5e7eb;
				border-radius: 18px;
				padding: 16px;
				box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
			}

			.dcd-top {
				display: flex;
				justify-content: space-between;
				align-items: center;
				gap: 12px;
				margin-bottom: 14px;
			}

			.dcd-fleet {
				display: inline-flex;
				align-items: center;
				justify-content: center;
				border-radius: 999px;
				padding: 8px 14px;
				background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
				border: 1px solid #cbd5e1;
				color: #0f172a;
				font-weight: 900;
				font-size: 14px;
			}

			.dcd-status {
				border-radius: 999px;
				padding: 7px 14px;
				font-weight: 900;
				font-size: 12px;
			}

			.dcd-open {
				background: #fee2e2;
				color: #991b1b;
				border: 1px solid #fecaca;
			}

			.dcd-fixed {
				background: #dcfce7;
				color: #166534;
				border: 1px solid #bbf7d0;
			}

			.dcd-meta {
				color: #475569;
				font-size: 13px;
				line-height: 1.7;
				margin-bottom: 14px;
			}

			.dcd-actions {
				display: flex;
				align-items: center;
				gap: 14px;
			}

			.dcd-view {
				border-radius: 999px !important;
				padding: 8px 18px !important;
				font-weight: 900 !important;
				border: 1px solid #2563eb !important;
				background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
				color: #ffffff !important;
				box-shadow: 0 5px 14px rgba(37, 99, 235, 0.28);
			}

			.dcd-check {
				display: inline-flex;
				align-items: center;
				gap: 7px;
				font-weight: 800;
				color: #334155;
			}

			.dcd-check input {
				width: 16px;
				height: 16px;
				cursor: pointer;
			}

			.dcd-empty {
				background: #f8fafc;
				border: 1px dashed #cbd5e1;
				border-radius: 16px;
				padding: 24px;
				text-align: center;
				font-weight: 800;
				color: #64748b;
			}

			.dcd-popup {
				font-size: 14px;
				line-height: 1.6;
			}

			.dcd-comment-block {
				margin-bottom: 14px;
			}

			.dcd-comment-source {
				display: inline-block;
				font-weight: 900;
				margin-bottom: 6px;
				padding: 4px 10px;
				border-radius: 999px;
				background: #eff6ff;
				color: #1d4ed8;
				border: 1px solid #bfdbfe;
			}

			.dcd-popup-comment {
				background: #f8fafc;
				border: 1px solid #e5e7eb;
				border-radius: 12px;
				padding: 12px;
				color: #0f172a;
			}
		</style>
	`);
}