frappe.query_reports["Oil Sample Report"] = {
	filters: [
		{
			fieldname: "location",
			label: "Location",
			fieldtype: "Link",
			options: "Location",
			description: "Leave blank for All locations",
			on_change: function () {
				// reset asset when location changes
				frappe.query_report.set_filter_value("assets", []);
				frappe.query_report.refresh();
			},
		},

		{
			fieldname: "asset_category",
			label: "Asset Category",
			fieldtype: "Link",
			options: "Asset Category",
			description: "Optional: filter asset list by category",
			on_change: function () {
				// reset assets when category changes
				frappe.query_report.set_filter_value("assets", []);
				frappe.query_report.refresh();
			},
		},


		{
			fieldname: "assets",
			label: "Assets",
			fieldtype: "MultiSelectList",
			description: "Leave empty for All assets",
			get_data: function (txt) {
				return frappe.call({
					method: "engineering.engineering.report.oil_sample_report.oil_sample_report.search_assets",
					args: {
						txt,
						location: frappe.query_report.get_filter_value("location"),
						asset_category: frappe.query_report.get_filter_value("asset_category"),
					},
				}).then((r) => r.message || []);
			},
			on_change: function () {
				frappe.query_report.refresh();
			},
		},

		{
			fieldname: "start_date",
			label: "Start Date",
			fieldtype: "Date",
			reqd: 1,
		},
		{
			fieldname: "end_date",
			label: "End Date",
			fieldtype: "Date",
			reqd: 1,
		},
		{
			fieldname: "metrics",
			label: "Value Field",
			fieldtype: "MultiSelectList",
			reqd: 1,
			default: ["fe"],
			description: "Select one or more particles (each becomes its own bar/line colour).",
			get_data: function (txt) {
				const all = [
					"tan","tbn","fe","ag","al","ca","cr","cu","mg","na","ni","pb","si","sn","p","b","ba","mo","v","zn","ti",
					"v40","v100","oxi","soot","iso4","iso6","iso14","pq","profileid"
				];
				const t = (txt || "").toLowerCase();
				return all
					.filter(x => x.toLowerCase().includes(t))
					.map(x => ({ value: x, description: x.toUpperCase() }));
			},
			on_change: function () {
				frappe.query_report.refresh();
			},
		},

		{
			fieldname: "chart_type",
			label: "Chart Type",
			fieldtype: "Select",
			default: "Bar",
			options: ["Bar", "Line"].join("\n"),
		},
		{
			fieldname: "top_n",
			label: "Top Assets Partical",
			fieldtype: "Int",
			default: 30,
			description: "Shows only the top N assets with the highest selected particle in the date range (0 = show all).",
		},
		{
			fieldname: "include_zero",
			label: "Include Zero Values",
			fieldtype: "Check",
			default: 1,
		},
	],

	onload: function (report) {
		// Pretty styling (inject once)
		if (!document.getElementById("oil-sample-report-style")) {
			const style = document.createElement("style");
			style.id = "oil-sample-report-style";
			style.innerHTML = `
				/* Title area */
				.page-title .title-text { font-weight: 700; letter-spacing: .2px; }
				/* Filters */
				.query-report .filter-section { padding: 10px 12px; border-radius: 14px; }
				/* Summary cards */
				.report-summary .summary-item {
					border-radius: 14px !important;
					box-shadow: 0 6px 18px rgba(0,0,0,.06);
				}
				/* Table */
				.datatable .dt-cell__content { font-size: 12.5px; }
				.datatable .dt-row:hover { background: rgba(0,0,0,.02); }
			`;
			document.head.appendChild(style);
		}

		// Default last 30 days
		const end = frappe.datetime.get_today();
		const start = frappe.datetime.add_days(end, -30);
		if (!report.get_filter_value("start_date")) report.set_filter_value("start_date", start);
		if (!report.get_filter_value("end_date")) report.set_filter_value("end_date", end);

	},

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Make "value" column look premium (bold + colored)
		if (column.fieldname === "value" && data) {
			const raw = Number(data.value || 0);

			// Compute max from current table rows (for relative intensity)
			const rows = (frappe.query_report && frappe.query_report.data) || [];
			let max = 0;
			for (const r of rows) max = Math.max(max, Number(r.value || 0));
			const ratio = max > 0 ? Math.min(raw / max, 1) : 0;

			// Blue → Purple scale (via HSL). Looks “world-class”.
			const hue = 220 - Math.round(40 * ratio); // 220..180
			const color = `hsl(${hue}, 80%, 40%)`;

			return `<span style="font-weight:700; color:${color};">${value}</span>`;
		}


		// Comments / Actions -> View button popup
		if ((column.fieldname === "commentstext" || column.fieldname === "actiontext") && data) {
			const title = column.fieldname === "commentstext" ? "Comments" : "Actions";
			const text = (data[column.fieldname] || "").toString().trim();

			if (!text) {
				return `<span class="text-muted">—</span>`;
			}

			// store text safely (base64) so quotes/newlines don't break HTML
			const encoded = btoa(unescape(encodeURIComponent(text)));

			return `
				<button
					class="btn btn-xs btn-default"
					data-osr-title="${title}"
					data-osr-text="${encoded}"
					onclick="window.__osr_open_text_modal(this)"
				>
					View
				</button>
			`;
		}



		// Asset emphasized
		if (column.fieldname === "asset") {
			return `<span style="font-weight:600;">${value}</span>`;
		}

		return value;
	},
};


window.__osr_open_text_modal = function (btn) {
	const title = btn.getAttribute("data-osr-title") || "Details";
	const encoded = btn.getAttribute("data-osr-text") || "";
	let text = "";
	try {
		text = decodeURIComponent(escape(atob(encoded)));
	} catch (e) {
		text = "(Could not decode text)";
	}

	const d = new frappe.ui.Dialog({
		title: title,
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "body",
				options: `
					<div class="osr-modal-card">
						<div class="osr-modal-badge">${frappe.utils.escape_html(title)}</div>
						<div class="osr-modal-text">${frappe.utils.escape_html(text)}</div>
					</div>
				`,
			},
		],
		primary_action_label: "Close",
		primary_action: () => d.hide(),
	});

	d.show();

	// Inject styles once + apply header gradient to this dialog
	if (!document.getElementById("osr-modal-style")) {
		const style = document.createElement("style");
		style.id = "osr-modal-style";
		style.innerHTML = `
			/* Dialog shell */
			.osr-dialog .modal-content { border-radius: 18px; overflow: hidden; box-shadow: 0 18px 45px rgba(0,0,0,.18); }
			/* Header gradient */
			.osr-dialog .modal-header {
				background: linear-gradient(90deg, rgba(37,99,235,1), rgba(124,58,237,1));
				color: #fff;
				border-bottom: none;
			}
			.osr-dialog .modal-header .modal-title { font-weight: 800; letter-spacing: .2px; }
			.osr-dialog .modal-header .close { opacity: 1; color: #fff; text-shadow: none; }
			/* Body */
			.osr-dialog .modal-body { background: #f8fafc; }
			.osr-modal-card {
				background: #fff;
				border-radius: 16px;
				padding: 14px 14px 12px 14px;
				border: 1px solid rgba(15, 23, 42, .08);
				box-shadow: 0 10px 24px rgba(0,0,0,.07);
			}
			.osr-modal-badge {
				display: inline-block;
				font-size: 11px;
				font-weight: 800;
				letter-spacing: .3px;
				padding: 6px 10px;
				border-radius: 999px;
				color: #0f172a;
				background: linear-gradient(90deg, rgba(59,130,246,.18), rgba(168,85,247,.18));
				margin-bottom: 10px;
			}
			.osr-modal-text {
				white-space: pre-wrap;
				font-size: 13px;
				line-height: 1.55;
				color: #0f172a;
				max-height: 60vh;
				overflow: auto;
				padding-right: 6px;
			}
			/* Primary button */
			.osr-dialog .modal-footer .btn-primary {
				border-radius: 12px;
				font-weight: 700;
				background: linear-gradient(90deg, rgba(37,99,235,1), rgba(124,58,237,1));
				border: none;
				box-shadow: 0 10px 20px rgba(37,99,235,.25);
			}
			.osr-dialog .modal-footer .btn-primary:hover {
				filter: brightness(1.03);
			}
		`;
		document.head.appendChild(style);
	}

	// Tag this dialog so CSS targets only our popups
	d.$wrapper.closest(".modal").addClass("osr-dialog");
};

