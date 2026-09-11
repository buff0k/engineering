const VLE_DOC_CACHE = {};

const VLE_BUCKETS = [
	{ key: "overdue", label: __("Overdue"), bg: "var(--bg-red)", fg: "var(--text-on-red)" },
	{ key: "d0_7", label: __("0–7 days"), bg: "var(--bg-orange)", fg: "var(--text-on-orange)" },
	{ key: "d8_14", label: __("8–14 days"), bg: "var(--bg-yellow)", fg: "var(--text-on-yellow)" },
	{ key: "d15_21", label: __("15–21 days"), bg: "var(--bg-blue)", fg: "var(--text-on-blue)" },
	{ key: "d22_28", label: __("22–28 days"), bg: "var(--bg-green)", fg: "var(--text-on-green)" },
];

frappe.pages["vehicle-licence-expiration"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Vehicle Licence Expiration"),
		single_column: true,
	});

	const filters = {
		site: page.add_field({
			fieldname: "site",
			label: __("Site"),
			fieldtype: "Link",
			options: "Location",
			change: () => refresh(),
		}),
		asset: page.add_field({
			fieldname: "asset",
			label: __("Asset"),
			fieldtype: "Link",
			options: "Asset",
			change: () => refresh(),
		}),
		asset_category: page.add_field({
			fieldname: "asset_category",
			label: __("Asset Category"),
			fieldtype: "Link",
			options: "Asset Category",
			change: () => refresh(),
		}),
		start_date: page.add_field({
			fieldname: "start_date",
			label: __("Start Date"),
			fieldtype: "Date",
			change: () => refresh(),
		}),
		end_date: page.add_field({
			fieldname: "end_date",
			label: __("End Date"),
			fieldtype: "Date",
			change: () => refresh(),
		}),
	};

	page.set_primary_action(__("Refresh"), () => refresh(), "refresh");
	page.add_inner_button(__("Open as Report"), () => frappe.set_route("query-report", "Licence Expiration"));
	page.add_inner_button(__("New Vehicle Licence"), () => frappe.new_doc("Vehicle Licence"));

	const $container = $("<div class='vle-page'></div>").appendTo(page.main);

	$container.html(`
		<style>
			.vle-page { padding: 18px 4px 40px; color: var(--text-color); }
			.vle-page .vle-note { color: var(--text-muted); margin-bottom: 16px; font-size: 12px; }
			.vle-panel {
				background: var(--card-bg);
				border: 1px solid var(--border-color);
				border-radius: 10px;
				padding: 16px;
				margin-bottom: 18px;
			}
			.vle-panel h4 {
				margin: 0 0 12px;
				font-size: 14px;
				font-weight: 700;
				text-transform: uppercase;
				letter-spacing: 0.3px;
				color: var(--text-color);
			}
			.vle-panel-empty { color: var(--text-muted); padding: 10px 2px; font-size: 13px; }

			.vle-bucket-row { display: flex; gap: 12px; flex-wrap: wrap; }
			.vle-bucket-pill {
				flex: 1 1 140px;
				min-width: 120px;
				border-radius: 10px;
				padding: 12px 14px;
				cursor: pointer;
				border: 1px solid var(--border-color);
				transition: transform 0.08s ease;
			}
			.vle-bucket-pill:hover { transform: translateY(-2px); }
			.vle-bucket-pill.vle-active { outline: 2px solid var(--primary); outline-offset: 1px; }
			.vle-bucket-value { font-size: 26px; font-weight: 800; line-height: 1.1; }
			.vle-bucket-label { font-size: 11px; font-weight: 700; text-transform: uppercase; margin-top: 4px; opacity: 0.85; }

			.vle-bubble-row { display: flex; gap: 12px; flex-wrap: wrap; }
			.vle-bubble {
				border-radius: 10px;
				border: 2px solid var(--blue-500, #1a73e8);
				background: var(--card-bg);
				padding: 10px 14px;
				text-align: center;
				cursor: pointer;
				min-width: 150px;
			}
			.vle-bubble:hover { transform: translateY(-1px); }
			.vle-bubble-cat { font-size: 11px; font-weight: 800; text-transform: uppercase; color: var(--text-color); margin-bottom: 8px; }
			.vle-bubble-stats { display: flex; gap: 16px; justify-content: center; }
			.vle-bubble-stat-value { font-size: 18px; font-weight: 800; color: var(--text-color); line-height: 1.1; }
			.vle-bubble-stat-label { font-size: 9px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); margin-top: 3px; }

			.vle-table { width: 100%; border-collapse: collapse; font-size: 12px; }
			.vle-table th, .vle-table td {
				border-bottom: 1px solid var(--border-color);
				padding: 7px 10px;
				text-align: left;
				color: var(--text-color);
			}
			.vle-table th { color: var(--text-muted); font-weight: 700; text-transform: uppercase; font-size: 10.5px; }
			.vle-table tr:hover td { background: var(--fg-hover-color); }
			.vle-status-chip {
				display: inline-block;
				padding: 2px 8px;
				border-radius: 999px;
				font-size: 10.5px;
				font-weight: 700;
			}

			.vle-drilldown-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 10px; }
			.vle-drilldown-title { font-weight: 700; }
			.vle-drilldown-count { color: var(--text-muted); font-weight: 400; }

			.vle-tree details { border: 1px solid var(--border-color); border-radius: 8px; padding: 8px 10px; margin: 6px 0; background: var(--fg-color); }
			.vle-tree summary { cursor: pointer; font-weight: 700; color: var(--text-color); }
			.vle-tree .vle-tree-count { color: var(--text-muted); font-weight: 400; }
			.vle-tree .vle-fleet-body { margin-top: 8px; }

			.vle-legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 11px; font-weight: 700; color: var(--text-muted); margin-bottom: 12px; }
			.vle-legend-swatch { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: middle; }
		</style>

		<div class="vle-note">
			${__("Latest submitted Vehicle Licence per Asset, grouped by days remaining until expiry. Click a bucket or category to drill in.")}
		</div>

		<div class="vle-panel">
			<h4>${__("Fleet by Category")}</h4>
			<div class="vle-bubble-row" id="vle-bubbles"><div class="vle-panel-empty">${__("Loading…")}</div></div>
		</div>

		<div class="vle-panel">
			<h4>${__("Licence Status Summary")}</h4>
			<div class="vle-legend" id="vle-legend"></div>
			<div class="vle-bucket-row" id="vle-buckets"><div class="vle-panel-empty">${__("Loading…")}</div></div>
		</div>

		<div class="vle-panel" id="vle-drilldown-panel" hidden></div>

		<div class="vle-panel">
			<h4>${__("Licence History")}</h4>
			<div class="vle-tree" id="vle-history-tree"><div class="vle-panel-empty">${__("Loading…")}</div></div>
		</div>
	`);

	build_legend();
	bind_history_lazy_loader($container);

	let active_bucket = null;
	let active_category = null;

	function get_filter_values() {
		return {
			site: filters.site.get_value() || "",
			asset: filters.asset.get_value() || "",
			asset_category: filters.asset_category.get_value() || "",
			start_date: filters.start_date.get_value() || "",
			end_date: filters.end_date.get_value() || "",
		};
	}

	function refresh() {
		active_bucket = null;
		active_category = null;
		$container.find("#vle-drilldown-panel").attr("hidden", true).empty();
		render_buckets();
		render_bubbles();
		render_history_tree();
	}

	function build_legend() {
		const $legend = $container.find("#vle-legend");
		$legend.html(
			VLE_BUCKETS.map(
				(b) =>
					`<span><span class="vle-legend-swatch" style="background:${b.bg};"></span>${b.label}</span>`
			).join("")
		);
	}

	function render_buckets() {
		// Runs the standard "Licence Expiration" Report in the background —
		// this page only renders what the report already computed.
		frappe.call({
			method: "frappe.desk.query_report.run",
			args: {
				report_name: "Licence Expiration",
				filters: { ...get_filter_values(), view: "Summary" },
				ignore_prepared_report: 1,
			},
			callback: (r) => {
				const row = (r.message && r.message.result && r.message.result[0]) || {};
				render_bucket_pills(row);
			},
		});
	}

	function render_bucket_pills(row) {
		const $buckets = $container.find("#vle-buckets");
		$buckets.html(
			VLE_BUCKETS.map((b) => {
				const value = row[b.key] || 0;
				const active_cls = active_bucket === b.key ? "vle-active" : "";
				return `
					<div class="vle-bucket-pill ${active_cls}" data-bucket="${b.key}" style="background:${b.bg}; color:${b.fg};">
						<div class="vle-bucket-value">${frappe.utils.escape_html(String(value))}</div>
						<div class="vle-bucket-label">${b.label}</div>
					</div>
				`;
			}).join("")
		);

		$buckets.find(".vle-bucket-pill").on("click", function () {
			const bucket = $(this).attr("data-bucket");
			active_bucket = bucket;
			active_category = null;
			open_bucket_drilldown(bucket);
			render_buckets();
		});
	}

	function open_bucket_drilldown(bucket) {
		frappe.call({
			method: "frappe.desk.query_report.run",
			args: {
				report_name: "Licence Expiration",
				filters: { ...get_filter_values(), view: "Assets", bucket },
				ignore_prepared_report: 1,
			},
			callback: (r) => {
				const rows = (r.message && r.message.result) || [];
				const bucket_meta = VLE_BUCKETS.find((b) => b.key === bucket);
				render_asset_drilldown({
					title: __("Assets due: {0}", [bucket_meta ? bucket_meta.label : bucket]),
					rows,
					show_status: true,
				});
			},
		});
	}

	function render_bubbles() {
		frappe.call({
			method: "engineering.engineering.page.vehicle_licence_expiration.vehicle_licence_expiration.get_asset_category_counts",
			args: { site: get_filter_values().site },
			callback: (r) => {
				render_bubble_row((r && r.message) || []);
			},
		});
	}

	function render_bubble_row(rows) {
		const $bubbles = $container.find("#vle-bubbles");

		if (!rows.length) {
			$bubbles.html(`<div class="vle-panel-empty">${__("No assets found.")}</div>`);
			return;
		}

		$bubbles.html(
			rows
				.map((x) => {
					const cat = frappe.utils.escape_html(x.category || __("Unknown"));
					const active_cls = active_category === x.category ? "vle-active" : "";
					return `
						<div class="vle-bubble ${active_cls}" data-category="${frappe.utils.escape_html(x.category || "")}"
							title="${__("Assets in this Category vs. Vehicle Licence documents captured against them (current + historical)")}">
							<div class="vle-bubble-cat">${cat}</div>
							<div class="vle-bubble-stats">
								<div>
									<div class="vle-bubble-stat-value">${frappe.utils.escape_html(String(x.asset_count || 0))}</div>
									<div class="vle-bubble-stat-label">${__("Assets")}</div>
								</div>
								<div>
									<div class="vle-bubble-stat-value">${frappe.utils.escape_html(String(x.licence_count || 0))}</div>
									<div class="vle-bubble-stat-label">${__("Licences")}</div>
								</div>
							</div>
						</div>
					`;
				})
				.join("")
		);

		$bubbles.find(".vle-bubble").on("click", function () {
			const category = $(this).attr("data-category");
			active_category = category;
			active_bucket = null;
			open_category_drilldown(category);
			render_bubbles();
		});
	}

	function open_category_drilldown(category) {
		frappe.call({
			method: "engineering.engineering.page.vehicle_licence_expiration.vehicle_licence_expiration.get_category_summary",
			args: { site: get_filter_values().site, asset_category: category },
			callback: (r) => {
				const rows = ((r && r.message) || {}).rows || [];
				render_asset_drilldown({
					title: __("{0} Licence Summary", [category]),
					rows,
					show_status: false,
				});
			},
		});
	}

	function render_asset_drilldown({ title, rows, show_status }) {
		const $panel = $container.find("#vle-drilldown-panel");
		const esc = frappe.utils.escape_html;

		const status_colour = (status) => {
			const map = {
				Overdue: { bg: "var(--bg-red)", fg: "var(--text-on-red)" },
				"0-7 days": { bg: "var(--bg-orange)", fg: "var(--text-on-orange)" },
				"8-14 days": { bg: "var(--bg-yellow)", fg: "var(--text-on-yellow)" },
				"15-21 days": { bg: "var(--bg-blue)", fg: "var(--text-on-blue)" },
				"22-28 days": { bg: "var(--bg-green)", fg: "var(--text-on-green)" },
			};
			return map[status] || { bg: "var(--control-bg)", fg: "var(--text-color)" };
		};

		const rows_html = rows
			.map((r) => {
				const record_href = r.record_url || `/app/vehicle-licence/${encodeURIComponent(r.document || r.name || "")}`;
				const attachment_href = (r.attach || "").trim() ? encodeURI(r.attach) : "";
				const status_cell = show_status
					? (() => {
							const c = status_colour(r.status);
							return `<td><span class="vle-status-chip" style="background:${c.bg}; color:${c.fg};">${esc(r.status || "")}</span></td>`;
					  })()
					: "";

				return `
					<tr>
						<td><a href="${record_href}" target="_blank" rel="noopener noreferrer">${esc(r.fleet_number || "")}</a></td>
						<td>${esc(r.site || "")}</td>
						<td>${esc(r.registration_number || "")}</td>
						<td>${esc(r.issue_date ? String(r.issue_date) : "")}</td>
						<td>${esc(r.expiry_date ? String(r.expiry_date) : "")}</td>
						<td>${esc(String(r.days_left ?? ""))}</td>
						${status_cell}
						<td>${attachment_href ? `<a href="${attachment_href}" target="_blank" rel="noopener noreferrer">${__("Open")}</a>` : `<span style="color:var(--text-muted);">${__("No File")}</span>`}</td>
					</tr>
				`;
			})
			.join("");

		const status_header = show_status ? `<th>${__("Status")}</th>` : "";

		$panel.html(`
			<div class="vle-drilldown-head">
				<div class="vle-drilldown-title">${esc(title)} <span class="vle-drilldown-count">(${rows.length} ${__("records")})</span></div>
				<button class="btn btn-xs btn-default" id="vle-drilldown-close">${__("Close")}</button>
			</div>
			<div style="overflow:auto;">
				<table class="vle-table">
					<thead>
						<tr>
							<th>${__("Fleet Number")}</th>
							<th>${__("Site")}</th>
							<th>${__("Registration Number")}</th>
							<th>${__("Issue Date")}</th>
							<th>${__("Expiry Date")}</th>
							<th>${__("Days Left")}</th>
							${status_header}
							<th>${__("Document")}</th>
						</tr>
					</thead>
					<tbody>${rows_html || `<tr><td colspan="8" style="text-align:center; padding:14px;">${__("No records found")}</td></tr>`}</tbody>
				</table>
			</div>
		`);

		$panel.attr("hidden", false);
		$panel.find("#vle-drilldown-close").on("click", () => {
			$panel.attr("hidden", true).empty();
			active_bucket = null;
			active_category = null;
			render_buckets();
			render_bubbles();
		});
	}

	function render_history_tree() {
		const $tree = $container.find("#vle-history-tree");
		$tree.html(`<div class="vle-panel-empty">${__("Loading…")}</div>`);

		// This is a full historical audit-trail browser, not date-windowed —
		// only pass the filters get_doc_history_tree_meta actually accepts
		// (site/asset/asset_category); start_date/end_date don't apply here.
		const { site, asset, asset_category } = get_filter_values();

		frappe.call({
			method: "engineering.engineering.page.vehicle_licence_expiration.vehicle_licence_expiration.get_doc_history_tree_meta",
			args: { site, asset, asset_category },
			callback: (r) => {
				const tree = ((r && r.message) || {}).tree || [];
				$tree.html(build_tree_html(tree));
			},
		});
	}

	refresh();
};

function build_tree_html(tree) {
	if (!tree.length) {
		return `<div class="vle-panel-empty">${__("No records")}</div>`;
	}

	const esc = frappe.utils.escape_html;

	return tree
		.map((site_node) => {
			const fleet_html = (site_node.children || [])
				.map(
					(fleet_node) => `
					<details class="vle-fleet-node" data-site="${esc(site_node.label || "")}" data-fleet="${esc(fleet_node.label || "")}">
						<summary>${esc(fleet_node.label || __("Unknown"))} <span class="vle-tree-count">(${esc(String(fleet_node.count ?? 0))})</span></summary>
						<div class="vle-fleet-body vle-panel-empty">${__("Expand to load…")}</div>
					</details>
				`
				)
				.join("");

			return `
				<details class="vle-site-node">
					<summary>${esc(site_node.label || __("Unknown"))} <span class="vle-tree-count">(${esc(String(site_node.count ?? 0))})</span></summary>
					<div>${fleet_html}</div>
				</details>
			`;
		})
		.join("");
}

function render_doc_rows_table(rows) {
	if (!rows || !rows.length) {
		return `<div class="vle-panel-empty">${__("No documents")}</div>`;
	}

	const esc = frappe.utils.escape_html;
	const trs = rows
		.map((d) => {
			const href = d.record_url || `/app/vehicle-licence/${encodeURIComponent(d.name || "")}`;
			const file_url = (d.attach || "").trim();
			return `
				<tr>
					<td><a href="${href}" target="_blank" rel="noopener noreferrer">${esc(d.name || "")}</a></td>
					<td>${esc(d.issue_date ? String(d.issue_date) : "")}</td>
					<td>${esc(d.expiry_date ? String(d.expiry_date) : "")}</td>
					<td>${file_url ? `<a href="${encodeURI(file_url)}" target="_blank" rel="noopener noreferrer">${__("Open")}</a>` : `<span style="color:var(--text-muted);">${__("No File")}</span>`}</td>
				</tr>
			`;
		})
		.join("");

	return `
		<table class="vle-table">
			<thead><tr><th>${__("Document")}</th><th>${__("Issue Date")}</th><th>${__("Expiry Date")}</th><th>${__("Attachment")}</th></tr></thead>
			<tbody>${trs}</tbody>
		</table>
	`;
}

function bind_history_lazy_loader($container) {
	$container.off("click.vle_history").on("click.vle_history", "details.vle-fleet-node > summary", function () {
		const node = $(this).closest("details.vle-fleet-node");
		if (node.data("loaded") || node.data("loading")) return;

		const site = node.attr("data-site") || "";
		const fleet = node.attr("data-fleet") || "";
		const body = node.find(".vle-fleet-body");
		const cache_key = `${site}|${fleet}`;

		if (VLE_DOC_CACHE[cache_key]) {
			node.data("loaded", 1);
			body.html(render_doc_rows_table(VLE_DOC_CACHE[cache_key]));
			return;
		}

		node.data("loading", 1);
		body.html(`<div class="vle-panel-empty">${__("Loading…")}</div>`);

		frappe.call({
			method: "engineering.engineering.page.vehicle_licence_expiration.vehicle_licence_expiration.get_doc_history_docs",
			args: { site, fleet_number: fleet, limit: 50, offset: 0 },
			callback: (r) => {
				const rows = (r && r.message && r.message.rows) || [];
				VLE_DOC_CACHE[cache_key] = rows;
				node.data("loading", 0);
				node.data("loaded", 1);
				body.html(render_doc_rows_table(rows));
			},
		});
	});
}
