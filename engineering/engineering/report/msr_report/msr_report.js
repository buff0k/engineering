(function () {
  const FRAME_ID = "msr-framed-view";
  const STYLE_ID = "msr-framed-style";
  const REPORT_NAME = "MSR Report";

  // -----------------------------
  // Helpers
  // -----------------------------
  function as_dom_node(x) {
    if (!x) return null;
    if (x instanceof HTMLElement) return x;
    if (typeof x.get === "function") {
      const n = x.get(0);
      if (n instanceof HTMLElement) return n;
    }
    if (x.wrapper instanceof HTMLElement) return x.wrapper;
    if (x.body instanceof HTMLElement) return x.body;
    if (x.main instanceof HTMLElement) return x.main;
    return null;
  }

  function get_root(report) {
    const a = report && report.page ? report.page.main : null;
    const node = as_dom_node(a);
    if (node) return node;
    return (
      document.querySelector(".page-content") ||
      document.querySelector(".page-body") ||
      document.querySelector(".layout-main-section") ||
      document.body
    );
  }

  function strip_html(val) {
    if (val === null || val === undefined) return "";
    return String(val).replace(/<[^>]*>/g, "").replace(/\s+/g, " ").trim();
  }

  function status_color(t) {
    t = (t || "").trim();
    if (t === "Service") return "#2e7d32";
    if (t === "Breakdown") return "#c62828";
    if (t === "Planned Maintenance") return "#ef6c00";
    if (t === "Inspection") return "#1565c0";
    return "#6b7280";
  }

  function format_hours(val) {
    if (val === null || val === undefined || val === "") return "";
    if (typeof val === "number") return val.toLocaleString(undefined, { maximumFractionDigits: 0 });
    const s = strip_html(val);
    const n = Number(String(s).replace(/,/g, "").replace(/\s/g, ""));
    if (!Number.isNaN(n)) return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
    return s;
  }

  function remove_existing_frame(container) {
    const root = as_dom_node(container) || container || document;
    const existing = root.querySelector ? root.querySelector("#" + FRAME_ID) : document.getElementById(FRAME_ID);
    if (existing) existing.remove();
  }

  function inject_style_once() {
    if (document.getElementById(STYLE_ID)) return;

    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      /* Hide standard query report UI */
      .report-filters,
      .report-filter-area,
      .standard-filter-section,
      .filter-section,
      .page-form,
      .form-inline.page-form,
      .page-form.row,

      /* Query report table + empty/footers/messages (varies by version) */
      .query-report .datatable,
      .datatable,
      .dt-scrollable,
      .dt-header,
      .dt-footer,
      .dt-row-filter,
      .dt-cell__edit,
      .dt-filter-help,
      .dt-help,
      .datatable-footer,
      .datatable .datatable-footer,
      .datatable .dt-pagination,
      .dt-pagination,
      .query-report .report-footer,
      .query-report .datatable-footer,
      .query-report .dt-pagination,
      .query-report .dt-empty,
      .query-report .dt-empty-state,
      .query-report .datatable-empty,
      .query-report .empty-state,
      .query-report .no-result,
      .query-report .no-result-row,
      .query-report .result,
      .query-report .result-container,
      .query-report .result-wrapper,
      .query-report .help-box,
      .query-report .form-message,
      .query-report .msgprint,
      .query-report .alert,
      .query-report .frappe-alert,
      .query-report .indicator-pill,
      .query-report .text-muted {
        display: none !important;
      }

      #${FRAME_ID}{
        margin-top: 12px;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        overflow: hidden;
        background: #fff;
      }
      #${FRAME_ID} .msr-frame-header{
        padding: 12px 16px;
        border-bottom: 1px solid #eee;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
      }
      #${FRAME_ID} .msr-frame-legend{
        display:flex;
        gap:14px;
        font-size:13px;
        align-items:center;
        flex-wrap:wrap;
        white-space: nowrap;
      }
      #${FRAME_ID} .msr-frame-filters{
        padding: 12px 16px;
        border-bottom: 1px solid #eee;
        display: flex;
        gap: 16px;
        align-items: flex-end;
        flex-wrap: wrap;
      }
      #${FRAME_ID} .msr-frame-filters .form-group{ margin: 0 !important; }
      #${FRAME_ID} .msr-frame-filters .control-label{
        font-size: 12px !important;
        color: #6b7280 !important;
        margin-bottom: 4px !important;
      }
      #${FRAME_ID} .msr-frame-filters .control-input,
      #${FRAME_ID} .msr-frame-filters .control-input input,
      #${FRAME_ID} .msr-frame-filters .control-input select{
        border-radius: 10px !important;
        height: 38px !important;
      }

      #${FRAME_ID} .msr-btn{
        padding: 8px 14px;
        border: 1px solid #d1d5db;
        border-radius: 10px;
        background: #f9fafb;
        cursor: pointer;
        font-size: 14px;
        height: 38px;
      }
      #${FRAME_ID} .msr-btn:hover{ background:#f3f4f6; }
      #${FRAME_ID} .msr-btn[disabled]{ opacity: 0.55; cursor: not-allowed; }

      #${FRAME_ID} .msr-loading{
        padding: 10px 16px;
        color: #6b7280;
        font-size: 13px;
      }

      #${FRAME_ID} table{ width: 100%; border-collapse: collapse; }
      #${FRAME_ID} th, #${FRAME_ID} td{ padding: 10px; border-bottom: 1px solid #eee; vertical-align: top; }
      #${FRAME_ID} th{ background:#fafafa; font-weight:600; text-align:left; }
      #${FRAME_ID} th.num, #${FRAME_ID} td.num{ text-align:right; }
      #${FRAME_ID} th.center, #${FRAME_ID} td.center{ text-align:center; }
      #${FRAME_ID} a{ text-decoration: underline; }
    `;
    document.head.appendChild(style);
  }

  // Hide/remove any leftover standard report "empty/help/footer" text blocks that some versions render
  // (e.g. "For comparison, use >5..." or "Nothing to show") even after hiding datatable.
  function suppress_standard_messages(report) {
    const root = get_root(report);

    const kill_if_matches = (el) => {
      try {
        const t = (el.innerText || "").trim();
        if (!t) return;
        if (
          t.includes("For comparison, use") ||
          t.toLowerCase().includes("nothing to show") ||
          t.toLowerCase().includes("no result") ||
          t.toLowerCase().includes("no rows")
        ) {
          el.style.display = "none";
        }
      } catch (e) {}
    };

    // Common containers
    root.querySelectorAll("div, p, span").forEach((el) => {
      // only target small/help-like blocks (avoid hiding real content)
      const cls = (el.className || "").toString();
      if (
        cls.includes("text-muted") ||
        cls.includes("help") ||
        cls.includes("datatable") ||
        cls.includes("report") ||
        cls.includes("dt-") ||
        cls.includes("result")
      ) {
        kill_if_matches(el);
      } else {
        // also catch that specific footer text even if class differs
        const t = (el.innerText || "").trim();
        if (t && (t.includes("For comparison, use") || t.toLowerCase().includes("nothing to show"))) {
          kill_if_matches(el);
        }
      }
    });
  }

  function attach_message_suppressor(report) {
    const root = get_root(report);
    if (report._msr_msg_observer) return;

    // Run once immediately
    suppress_standard_messages(report);

    // Observe changes and suppress again
    const obs = new MutationObserver(() => suppress_standard_messages(report));
    obs.observe(root, { childList: true, subtree: true });
    report._msr_msg_observer = obs;
  }


  // -----------------------------
  // Controls
  // -----------------------------
  function make_controls(report, frame, initial_asset, initial_type) {
    report._msr_controls = report._msr_controls || {};

    // Asset
    const assetParent = frame.querySelector("#msr_asset_link");
    if (report._msr_controls.asset && report._msr_controls.asset.$wrapper) {
      report._msr_controls.asset.$wrapper.remove();
      report._msr_controls.asset = null;
    }
    const assetCtrl = frappe.ui.form.make_control({
      parent: assetParent,
      df: {
        fieldtype: "Link",
        fieldname: "msr_asset",
        label: "Fleet Number",
        options: "Asset",
        reqd: 0,
        placeholder: "Select Asset…",
      },
      render_input: true,
    });
    assetCtrl.refresh();
    if (initial_asset) assetCtrl.set_value(initial_asset);

    // Type
    const typeParent = frame.querySelector("#msr_type_ctrl");
    if (report._msr_controls.type && report._msr_controls.type.$wrapper) {
      report._msr_controls.type.$wrapper.remove();
      report._msr_controls.type = null;
    }
    const typeCtrl = frappe.ui.form.make_control({
      parent: typeParent,
      df: {
        fieldtype: "Select",
        fieldname: "msr_type",
        label: "Type",
        options: ["", "Service", "Breakdown", "Planned Maintenance", "Inspection"].join("\n"),
        reqd: 0,
      },
      render_input: true,
    });
    typeCtrl.refresh();
    typeCtrl.set_value(initial_type || "");

    report._msr_controls.asset = assetCtrl;
    report._msr_controls.type = typeCtrl;
    return { assetCtrl, typeCtrl };
  }

  function read_asset_value(assetCtrl) {
    let v = "";
    try { v = (assetCtrl.get_value() || "").trim(); } catch (e) {}
    if (!v && assetCtrl.$input && typeof assetCtrl.$input.val === "function") {
      v = (assetCtrl.$input.val() || "").trim();
    }
    return v;
  }

  function read_type_value(typeCtrl) {
    let v = "";
    try { v = (typeCtrl.get_value() || "").trim(); } catch (e) {}
    return v;
  }

  // -----------------------------
  // Data fetching (bypass Query Report refresh issues)
  // -----------------------------
  function normalize_result(columns, result) {
    if (!Array.isArray(result)) return [];
    if (!result.length) return [];

    // If already dicts
    if (typeof result[0] === "object" && !Array.isArray(result[0])) return result;

    // If arrays, map to dict using columns fieldnames
    const fieldnames = (columns || [])
      .map((c) => (typeof c === "object" ? c.fieldname : null))
      .filter(Boolean);

    if (!fieldnames.length) return [];

    return result.map((row) => {
      const obj = {};
      for (let i = 0; i < fieldnames.length; i++) obj[fieldnames[i]] = row[i];
      return obj;
    });
  }

  function fetch_report_data(filters) {
    return new Promise((resolve, reject) => {
      frappe.call({
        method: "frappe.desk.query_report.run",
        args: {
          report_name: REPORT_NAME,
          filters: filters || {},
        },
        callback: (r) => {
          try {
            const msg = r.message || {};
            const cols = msg.columns || msg.columns || [];
            const res = msg.result || msg.result || msg.data || [];
            resolve({ columns: cols, result: res });
          } catch (e) {
            reject(e);
          }
        },
        error: (err) => reject(err),
      });
    });
  }

  // -----------------------------
  // Frame render
  // -----------------------------
  function render_table(frame, rows) {
    const tbody = frame.querySelector("#msr_tbody");
    if (!tbody) return;

    tbody.innerHTML = (rows && rows.length)
      ? rows.map((r) => {
          const color = status_color(r.service_breakdown);
          const msr = strip_html(r.name || "");
          const date = strip_html(r.service_date || "");
          const hrs = format_hours(r.current_hours);
          const desc = strip_html(r.description_of_breakdown || "");
          return `
            <tr style="box-shadow: inset 4px 0 0 ${color};">
              <td>
                <a href="/app/mechanical-service-report/${encodeURIComponent(msr)}"
                   target="_blank"
                   style="color:${color};font-weight:500;">
                  ${msr}
                </a>
              </td>
              <td class="center">${date}</td>
              <td class="num">${hrs}</td>
              <td>${desc}</td>
            </tr>
          `;
        }).join("")
      : `<tr><td colspan="4">&nbsp;</td></tr>`;
  }

  function set_loading(frame, on) {
    const el = frame.querySelector("#msr_loading");
    if (!el) return;
    el.style.display = on ? "block" : "none";
  }

  function build_frame(report) {
    inject_style_once();

    const root = get_root(report);
    remove_existing_frame(root);

    const frame = document.createElement("div");
    frame.id = FRAME_ID;

    const legend = `
      <span style="color:#2e7d32">● Service</span>
      <span style="color:#c62828">● Breakdown</span>
      <span style="color:#ef6c00">● Planned Maintenance</span>
      <span style="color:#1565c0">● Inspection</span>
    `;

    // Preserve last selected filters on re-render
    const initial_asset = (report && report._msr_state && report._msr_state.asset) || "";
    const initial_type = (report && report._msr_state && report._msr_state.type) || "";

    frame.innerHTML = `
      <div class="msr-frame-header">
        <strong>Equipment Logsheet</strong>
        <div class="msr-frame-legend">${legend}</div>
      </div>

      <div class="msr-frame-filters">
        <div style="min-width:320px" id="msr_asset_link"></div>
        <div style="min-width:320px" id="msr_type_ctrl"></div>

        <button class="msr-btn" id="msr_apply">Apply</button>
        <button class="msr-btn" id="msr_clear">Clear</button>
      </div>

      <div id="msr_loading" class="msr-loading" style="display:none">Loading…</div>

      <div style="overflow-x:auto">
        <table>
          <thead>
            <tr>
              <th style="width:38%">MSR</th>
              <th class="center" style="width:14%">MSR Date</th>
              <th class="num" style="width:16%">Hours</th>
              <th style="width:32%">Description of Equipment Interaction/Work performed</th>
            </tr>
          </thead>
          <tbody id="msr_tbody"></tbody>
        </table>
      </div>
    `;

    root.prepend(frame);

    attach_message_suppressor(report);
    suppress_standard_messages(report);

    const { assetCtrl, typeCtrl } = make_controls(report, frame, initial_asset, initial_type);
    const applyBtn = frame.querySelector("#msr_apply");
    const clearBtn = frame.querySelector("#msr_clear");

    function update_apply_enabled() {
      const fleet = read_asset_value(assetCtrl);
      applyBtn.disabled = !fleet;
    }
    update_apply_enabled();

    if (assetCtrl.$input) {
      assetCtrl.$input.on("awesomplete-selectcomplete", update_apply_enabled);
      assetCtrl.$input.on("change", update_apply_enabled);
      assetCtrl.$input.on("blur", update_apply_enabled);
      assetCtrl.$input.on("input", update_apply_enabled);
    }

    async function run_apply() {
      const fleet = read_asset_value(assetCtrl);
      const type = read_type_value(typeCtrl);

      // Remember selections
      report._msr_state = { asset: fleet || "", type: type || "" };

      // No asset => blank table
      if (!fleet) {
        render_table(frame, []);
        update_apply_enabled();
        return;
      }

      set_loading(frame, true);
      try {
        const resp = await fetch_report_data({
          asset: fleet,
          service_breakdown: type || undefined,
        });

        const rows = normalize_result(resp.columns, resp.result);
        render_table(frame, rows);
        suppress_standard_messages(report);
      } catch (e) {
        console.error("MSR framed fetch error", e);
        render_table(frame, []);
        suppress_standard_messages(report);
      } finally {
        set_loading(frame, false);
      }
    }

    applyBtn.addEventListener("click", () => {
      run_apply();
    });

    clearBtn.addEventListener("click", () => {
      try { assetCtrl.set_value(""); } catch (e) {}
      try { typeCtrl.set_value(""); } catch (e) {}
      report._msr_state = { asset: "", type: "" };
      render_table(frame, []);
      update_apply_enabled();
    });

    // Initial load: if we already have an asset selected (from route/previous), fetch immediately
    if (initial_asset) run_apply();
  }

  frappe.query_reports[REPORT_NAME] = {
    onload(report) {
      build_frame(report);
    },
    refresh(report) {
      // If Frappe triggers refresh, keep our frame (do not depend on report.data)
      build_frame(report);
    },
  };
})();