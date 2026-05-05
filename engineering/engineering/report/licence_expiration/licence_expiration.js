const LIC_DOC_CACHE = {};

frappe.query_reports["Licence Expiration"] = {
  filters: [
    {
      fieldname: "site",
      label: "Site",
      fieldtype: "Link",
      options: "Location"
    },
    {
      fieldname: "asset",
      label: "Asset",
      fieldtype: "Link",
      options: "Asset"
    },
    {
      fieldname: "start_date",
      label: "Start Date",
      fieldtype: "Date"
    },
    {
      fieldname: "end_date",
      label: "End Date",
      fieldtype: "Date"
    },
    {
      fieldname: "view",
      label: "View",
      fieldtype: "Select",
      options: "Summary\nAssets",
      default: "Summary",
      hidden: 1
    },
    {
      fieldname: "bucket",
      label: "Bucket",
      fieldtype: "Select",
      options: "\noverdue\nd0_7\nd8_14\nd15_21\nd22_28",
      hidden: 1
    }
  ],

  onload(report) {
    bind_doc_history_lazy_loader(report);

    report.page.add_inner_button("Back to Summary", () => {
      report.set_filter_value("view", "Summary");
      report.set_filter_value("bucket", "");
      frappe.query_report.refresh();
      $(report.page.wrapper).find("#lic-drilldown").remove();
    });

    $(report.page.wrapper)
      .off("click.lic_buckets")
      .on("click.lic_buckets", ".lic-bucket-pill", function () {
        const bucket = $(this).attr("data-bucket") || "";
        const site = frappe.query_report.get_filter_value("site") || "";
        const asset = frappe.query_report.get_filter_value("asset") || "";
        const start_date = frappe.query_report.get_filter_value("start_date") || "";
        const end_date = frappe.query_report.get_filter_value("end_date") || "";

        frappe.call({
          method: "engineering.engineering.report.licence_expiration.fetch_second_table.get_assets",
          args: { site, asset, start_date, end_date, bucket },
          callback: (r) => {
            const rows = (r && r.message && r.message.rows) ? r.message.rows : [];
            render_drilldown(report, { site, asset, start_date, end_date, bucket, rows });
          }
        });
      });

    $(report.page.wrapper)
      .off("click.lic_category")
      .on("click.lic_category", ".lic-cat-bubble", function () {
        const category = $(this).attr("data-category") || "";
        const site = frappe.query_report.get_filter_value("site") || "";
        open_category_summary(report, { site, category });
      });
  },

  after_refresh(report) {
    const view = frappe.query_report.get_filter_value("view") || "Summary";
    if (view !== "Summary") return;

    setTimeout(() => {
      ensure_summary_title(report);
      ensure_clean_summary_grid(report);
      refresh_dashboard(report);

      const site = frappe.query_report.get_filter_value("site") || "";
      const asset = frappe.query_report.get_filter_value("asset") || "";
      render_doc_history_tree(report, { site, asset });
    }, 0);
  },

  formatter(value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    const view = frappe.query_report.get_filter_value("view") || "Summary";
    if (view !== "Summary") return value;

    const bucketCols = {
      overdue: { bg: "#f6b3b3", fg: "#6b1b1b" },
      d0_7:    { bg: "#f6c59f", fg: "#6b3a00" },
      d8_14:   { bg: "#f5e29a", fg: "#5c4a00" },
      d15_21:  { bg: "#b8d6f6", fg: "#0b5394" },
      d22_28:  { bg: "#bfe5c6", fg: "#1f5e2b" }
    };

    const field = column.fieldname;
    if (!bucketCols[field]) return value;

    const n = (data && typeof data[field] !== "undefined") ? data[field] : 0;
    const style =
      `display:inline-block; min-width:34px; text-align:center; ` +
      `padding:0; width:34px; height:34px; line-height:34px; border-radius:10px; cursor:pointer; ` +
      `background:${bucketCols[field].bg}; color:${bucketCols[field].fg}; ` +
      `border:1px solid rgba(0,0,0,0.10); font-weight:800;`;

    return `<span class="lic-bucket-pill" data-bucket="${field}" style="${style}" title="Click to open assets">${n}</span>`;
  }
};

function ensure_summary_title(report) {
  const main = $(report.page.main);
  const reportWrapper = main.find(".report-wrapper").first();
  if (!reportWrapper.length) return;

  let top = main.find("#lic-top-area");
  if (!top.length) {
    reportWrapper.before(`<div id="lic-top-area" style="margin:6px 0 10px;"></div>`);
    top = main.find("#lic-top-area");
  }

  if (!top.find("#lic-dashboard-title").length) {
    top.append(`<div id="lic-dashboard-title" style="text-align:center; font-weight:900; font-size:14px; margin:0 0 8px;">Total Fleet</div>`);
  }
  if (!top.find("#lic-dashboard").length) {
    top.append(`<div id="lic-dashboard" style="display:flex; gap:10px; flex-wrap:wrap; margin:0 0 14px;"></div>`);
  }
  if (!top.find("#lic-summary-title").length) {
    top.append(`<div id="lic-summary-title" style="text-align:center; margin:6px 0 10px; font-weight:900; font-size:14px;">SUMMARY</div>`);
  }
  if (!top.find("#lic-legend").length) {
    top.append(`
      <div id="lic-legend" style="display:flex; justify-content:center; gap:16px; flex-wrap:wrap; align-items:center; margin:0 0 10px; font-size:12px;">
        <span><span style="display:inline-block;width:20px;height:20px;border-radius:50%;background:#f6b3b3;border:1px solid rgba(0,0,0,.12);margin-right:6px;vertical-align:middle;"></span><b>Overdue</b></span>
        <span><span style="display:inline-block;width:20px;height:20px;border-radius:50%;background:#f6c59f;border:1px solid rgba(0,0,0,.12);margin-right:6px;vertical-align:middle;"></span><b>0–7 days</b></span>
        <span><span style="display:inline-block;width:20px;height:20px;border-radius:50%;background:#f5e29a;border:1px solid rgba(0,0,0,.12);margin-right:6px;vertical-align:middle;"></span><b>8–14 days</b></span>
        <span><span style="display:inline-block;width:20px;height:20px;border-radius:50%;background:#b8d6f6;border:1px solid rgba(0,0,0,.12);margin-right:6px;vertical-align:middle;"></span><b>15–21 days</b></span>
        <span><span style="display:inline-block;width:20px;height:20px;border-radius:50%;background:#bfe5c6;border:1px solid rgba(0,0,0,.12);margin-right:6px;vertical-align:middle;"></span><b>22–28 days</b></span>
      </div>
    `);
  }
}

function ensure_clean_summary_grid(report) {
  const wrap = $(report.page.wrapper);
  if (wrap.find("#lic-summary-style").length) return;

  wrap.append(`
    <style id="lic-summary-style">
      .report-wrapper .datatable .dt-cell--col-1 .dt-cell__content { font-weight: 900 !important; }
      .report-wrapper .dt-row-header,
      .report-wrapper .dt-cell--row-header,
      .report-wrapper .datatable .dt-row-header,
      .report-wrapper .datatable .dt-cell--row-header { display: none !important; }
      .report-wrapper .datatable { margin-left: auto !important; margin-right: auto !important; width: auto !important; }
      .report-wrapper .datatable .dt-scrollable,
      .report-wrapper .datatable .dt-body,
      .report-wrapper .datatable .dt-header { margin-left: auto !important; margin-right: auto !important; }
      .report-wrapper .datatable .dt-table { width: auto !important; }
      #lic-top-area, .report-wrapper { max-width: 1100px !important; margin-left: auto !important; margin-right: auto !important; }
      #lic-dashboard-title { text-align: center !important; width: 100% !important; }
      #lic-dashboard { width: 100% !important; justify-content: center !important; }
      #lic-drilldown { max-width: 1100px; margin-left: auto; margin-right: auto; }
      .report-wrapper .dt-cell--col-0,
      .report-wrapper .dt-header .dt-cell--col-0 { display: none !important; }
      .report-wrapper .dt-row-filter,
      .report-wrapper .datatable .dt-row-filter,
      .report-wrapper .dt-filter,
      .report-wrapper .datatable .dt-filter { display: none !important; }
      .report-wrapper .datatable .dt-cell,
      .report-wrapper .datatable .dt-header { border: none !important; }
      .report-wrapper .datatable .dt-cell__content { overflow: visible !important; text-overflow: clip !important; white-space: nowrap !important; }
      .report-wrapper .datatable .dt-scrollable__hint,
      .report-wrapper .datatable .dt-help,
      .report-wrapper .datatable .dt-ellipsis,
      .report-wrapper .datatable + .text-muted { display: none !important; }
    </style>
  `);
}

function refresh_dashboard(report) {
  const site = frappe.query_report.get_filter_value("site") || "";

  frappe.call({
    method: "engineering.engineering.report.licence_expiration.fetch_second_table.get_asset_category_counts",
    args: { site },
    callback: (r) => {
      const rows = (r && r.message) ? r.message : [];
      render_dashboard(report, rows, site);
    }
  });
}

function render_dashboard(report, rows, site) {
  const wrap = $(report.page.wrapper);
  const dash = wrap.find("#lic-dashboard");

  if (!rows.length) {
    dash.html(`<div style="opacity:.7;">No assets found for Site=${frappe.utils.escape_html(site || "All")}</div>`);
    return;
  }

  dash.html(rows.map(x => {
    const rawCat = x.category || "Unknown";
    const cat = frappe.utils.escape_html(rawCat);
    const cnt = frappe.utils.escape_html(String(x.count ?? 0));
    const w = Math.min(260, Math.max(140, (rawCat.length * 8) + 60));

    return `
      <div class="lic-cat-bubble" data-category="${frappe.utils.escape_html(rawCat)}" title="Click to view category summary"
        style="width:${w}px; padding:10px 12px; border-radius:999px; border:2px solid #118DFF; background:#fff; text-align:center; color:#262A76; font-weight:900; cursor:pointer;">
        <div style="font-size:12px; font-weight:900; margin-bottom:3px; color:#262A76;">${cat}</div>
        <div style="font-size:20px; font-weight:900; line-height:1; color:#262A76;">${cnt}</div>
      </div>
    `;
  }).join(""));
}

function open_category_summary(report, ctx) {
  frappe.call({
    method: "engineering.engineering.report.licence_expiration.fetch_second_table.get_category_summary",
    args: { site: ctx.site, asset_category: ctx.category },
    callback: (r) => {
      const payload = (r && r.message) ? r.message : {};
      render_category_summary(report, { site: ctx.site, category: ctx.category, rows: payload.rows || [] });
    }
  });
}

function render_category_summary(report, ctx) {
  const { category, rows } = ctx;
  const wrap = $(report.page.wrapper);
  wrap.find("#lic-drilldown").remove();
  const esc = frappe.utils.escape_html;

  const tableRows = (rows || []).map(r => {
    const recordHref = r.record_url || `/app/licence-registration/${encodeURIComponent(r.name || "")}`;
    const attachmentHref = (r.attach || "").trim() ? encodeURI(r.attach) : "";
    return `
      <tr>
        <td><a href="${recordHref}" target="_blank" rel="noopener noreferrer">${esc(r.fleet_number || "")}</a></td>
        <td>${esc(r.site || "")}</td>
        <td>${esc(r.registration_number || "")}</td>
        <td>${esc(r.issue_date ? String(r.issue_date) : "")}</td>
        <td>${esc(r.expiry_date ? String(r.expiry_date) : "")}</td>
        <td style="text-align:right;">${esc(String(r.days_left ?? ""))}</td>
        <td>${attachmentHref ? `<a href="${attachmentHref}" target="_blank" rel="noopener noreferrer">Open</a>` : `<span style="opacity:.5;">No File</span>`}</td>
      </tr>
    `;
  }).join("");

  const html = `
    <div id="lic-drilldown" style="margin-top:14px; padding:12px; border:1px solid rgba(0,0,0,0.08); border-radius:10px;">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:12px; flex-wrap:wrap;">
        <div style="font-weight:900;">${esc(category || "Category")} Licence Summary <span style="opacity:.65;">(${esc(String((rows || []).length))} records)</span></div>
        <button class="btn btn-sm btn-default" id="lic-drilldown-close">Close</button>
      </div>
      <div style="overflow:auto;">
        <table class="table table-bordered" style="margin:0;">
          <thead><tr><th>Fleet Number</th><th>Site</th><th>Registration Number</th><th>Issue Date</th><th>Expiry Date</th><th style="text-align:right;">Days Left</th><th>Document</th></tr></thead>
          <tbody>${tableRows || `<tr><td colspan="7" style="text-align:center; padding:14px;">No records found</td></tr>`}</tbody>
        </table>
      </div>
    </div>
  `;

  wrap.find(".report-wrapper").append(html);
  wrap.find("#lic-drilldown-close").on("click", () => wrap.find("#lic-drilldown").remove());
}

function render_drilldown(report, ctx) {
  const { site, asset, start_date, end_date, bucket, rows } = ctx;
  const wrap = $(report.page.wrapper);
  wrap.find("#lic-drilldown").remove();

  const title = `Licence assets due: Site=${site || "All"}, Asset=${asset || "All"}, Bucket=${bucket}`;

  const tableRows = rows.map(r => {
    const recordHref = `/app/licence-registration/${encodeURIComponent(r.name || "")}`;
    const attachmentHref = (r.attach || "").trim() ? encodeURI(r.attach) : "";
    return `
      <tr>
        <td><a href="${recordHref}" target="_blank" rel="noopener noreferrer">${frappe.utils.escape_html(r.fleet_number || "")}</a></td>
        <td>${frappe.utils.escape_html(r.site || "")}</td>
        <td>${frappe.utils.escape_html(r.registration_number || "")}</td>
        <td>${frappe.utils.escape_html(r.issue_date ? String(r.issue_date) : "")}</td>
        <td>${frappe.utils.escape_html(r.expiry_date ? String(r.expiry_date) : "")}</td>
        <td style="text-align:right;">${frappe.utils.escape_html(String(r.days_left ?? ""))}</td>
        <td>${frappe.utils.escape_html(r.status || "")}</td>
        <td>${attachmentHref ? `<a href="${attachmentHref}" target="_blank" rel="noopener noreferrer">Open</a>` : `<span style="opacity:.5;">No File</span>`}</td>
      </tr>
    `;
  }).join("");

  const html = `
    <div id="lic-drilldown" style="margin-top:14px; padding:12px; border:1px solid rgba(0,0,0,0.08); border-radius:10px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
        <div style="font-weight:800;">${frappe.utils.escape_html(title)}</div>
        <button class="btn btn-sm btn-default" id="lic-drilldown-close">Close</button>
      </div>
      <div style="overflow:auto;">
        <table class="table table-bordered" style="margin:0;">
          <thead><tr><th>Fleet Number</th><th>Site</th><th>Registration Number</th><th>Issue Date</th><th>Expiry Date</th><th style="text-align:right;">Days Left</th><th>Status</th><th>Document</th></tr></thead>
          <tbody>${tableRows || `<tr><td colspan="8" style="text-align:center; padding:14px;">No assets found</td></tr>`}</tbody>
        </table>
      </div>
    </div>
  `;

  wrap.find(".report-wrapper").append(html);
  wrap.find("#lic-drilldown-close").on("click", () => wrap.find("#lic-drilldown").remove());
}

function render_doc_history_tree(report, ctx) {
  const { site, asset } = ctx;
  const main = $(report.page.main);

  let host = main.find("#lic-doc-history");
  if (!host.length) {
    main.append(`<div id="lic-doc-history" style="max-width:1100px; margin:18px auto 0;"></div>`);
    host = main.find("#lic-doc-history");
  }

  host.html(`<div style="text-align:center; font-weight:900; font-size:16px; margin-bottom:6px;">Licence History</div><div style="text-align:center; opacity:.7;">Loading…</div>`);

  frappe.call({
    method: "engineering.engineering.report.licence_expiration.fetch_second_table.get_doc_history_tree_meta",
    args: { site, asset },
    callback: (r) => {
      const payload = (r && r.message) ? r.message : {};
      const tree = payload.tree || [];
      host.html(build_doc_history_html(tree));
    }
  });
}

function build_doc_history_html(tree) {
  if (!tree.length) return `<div style="text-align:center; opacity:.7;">No records</div>`;

  const esc = frappe.utils.escape_html;
  return tree.map(siteNode => {
    const fleetHtml = (siteNode.children || []).map(fleetNode => `
      <details class="lic-fleet-node" data-site="${esc(siteNode.label || "")}" data-fleet="${esc(fleetNode.label || "")}" style="border:1px solid rgba(0,0,0,0.08); border-radius:10px; padding:8px 10px; margin:8px 0;">
        <summary style="cursor:pointer; font-weight:900;">→ ${esc(fleetNode.label || "Unknown")} <span style="opacity:.65;">(${esc(String(fleetNode.count ?? 0))})</span></summary>
        <div class="lic-fleet-body" style="margin-top:8px; opacity:.7;">Expand to load…</div>
      </details>
    `).join("");

    return `
      <details class="lic-site-node" style="border:1px solid rgba(0,0,0,0.12); border-radius:14px; padding:12px 14px; margin:12px 0;">
        <summary style="cursor:pointer; font-weight:900; font-size:15px;">▼ ${esc(siteNode.label || "Unknown")} <span style="opacity:.65;">(${esc(String(siteNode.count ?? 0))})</span></summary>
        <div style="margin-top:10px;">${fleetHtml}</div>
      </details>
    `;
  }).join("");
}

function render_doc_rows_table(rows) {
  if (!rows || !rows.length) return `<div style="text-align:center; padding:10px;">No docs</div>`;

  const esc = frappe.utils.escape_html;
  const trs = rows.map(d => {
    const href = d.record_url || `/app/licence-registration/${encodeURIComponent(d.name || "")}`;
    const fileUrl = (d.attach || "").trim();
    return `
      <tr>
        <td><a href="${href}" target="_blank" rel="noopener noreferrer">${esc(d.name || "")}</a></td>
        <td>${esc(d.issue_date ? String(d.issue_date) : "")}</td>
        <td>${esc(d.expiry_date ? String(d.expiry_date) : "")}</td>
        <td>${fileUrl ? `<a href="${encodeURI(fileUrl)}" target="_blank" rel="noopener noreferrer">Open</a>` : `<span style="opacity:.5;">No File</span>`}</td>
      </tr>
    `;
  }).join("");

  return `<div style="overflow:auto;"><table class="table table-bordered" style="margin:0;"><thead><tr><th>Document</th><th>Issue Date</th><th>Expiry Date</th><th>Attachment</th></tr></thead><tbody>${trs}</tbody></table></div>`;
}

function bind_doc_history_lazy_loader(report) {
  const wrap = $(report.page.wrapper);

  wrap.off("click.lic_doc_history").on("click.lic_doc_history", "details.lic-fleet-node > summary", function () {
    const node = $(this).closest("details.lic-fleet-node");
    if (node.data("loaded") || node.data("loading")) return;

    const site = node.attr("data-site") || "";
    const fleet = node.attr("data-fleet") || "";
    const asset = frappe.query_report.get_filter_value("asset") || "";
    const body = node.find(".lic-fleet-body");
    const cache_key = `${site}|${fleet}`;

    if (LIC_DOC_CACHE[cache_key]) {
      node.data("loaded", 1);
      body.html(render_doc_rows_table(LIC_DOC_CACHE[cache_key]));
      return;
    }

    node.data("loading", 1);
    body.html("Loading…");

    frappe.call({
      method: "engineering.engineering.report.licence_expiration.fetch_second_table.get_doc_history_docs",
      args: { site, fleet_number: fleet, asset, limit: 50, offset: 0 },
      callback: (r) => {
        const rows = (r && r.message && r.message.rows) ? r.message.rows : [];
        LIC_DOC_CACHE[cache_key] = rows;
        node.data("loading", 0);
        node.data("loaded", 1);
        body.html(render_doc_rows_table(rows));
      }
    });
  });
}
