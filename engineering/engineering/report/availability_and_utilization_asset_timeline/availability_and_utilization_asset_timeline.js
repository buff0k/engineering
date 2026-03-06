frappe.query_reports["Availability and utilization Asset timeline"] = {
  filters: [
    {
      fieldname: "site",
      label: "Site",
      fieldtype: "Link",
      options: "Location",
      reqd: 1,
      default: frappe.defaults.get_user_default("location") || ""
    },

    {
      fieldname: "start_date",
      label: "Start Date",
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.get_today(),
    },

    {
      fieldname: "end_date",
      label: "End Date",
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.get_today(),
    },

    {
      fieldname: "asset_category",
      label: "ASSETS",
      fieldtype: "Link",
      options: "Asset Category",
      reqd: 0,
    },
  ],

  onload: function (report) {
    if (!document.getElementById("asset-timeline-css")) {
      const style = document.createElement("style");
      style.id = "asset-timeline-css";
      style.innerHTML = `
        .dt-header .dt-cell__content {
          white-space: nowrap !important;
          overflow: visible !important;
          text-overflow: clip !important;
        }

        .tl-legend {
          display: flex;
          gap: 14px;
          align-items: center;
          margin: 6px 0 10px;
          flex-wrap: wrap;
        }

        .tl-item {
          display: flex;
          gap: 6px;
          align-items: center;
        }

        .tl-sq {
          width: 18px;
          height: 12px;
          border: 1px solid #444;
          display: inline-block;
        }

        .tl-startup { background: #ffff00; }
        .tl-breakdown { background: #ff0000; }
        .tl-fatigue { background: #00b0f0; }

        .tl-slot {
          width: 100%;
          min-height: 24px;
          border-radius: 2px;
        }

        .tl-S {
          background: #ffff00;
          height: 18px;
        }

        .tl-F {
          background: #00b0f0;
          height: 18px;
        }

        .tl-B {
          background: #ff0000;
          min-height: 40px;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2px;
        }

        .tl-bd-btn {
          background: #ffffff;
          color: #000000;
          border: 1px solid #a0a0a0;
          border-radius: 4px;
          font-size: 11px;
          line-height: 1.2;
          padding: 3px 6px;
          cursor: pointer;
          white-space: nowrap;
        }

        .tl-empty {
          min-height: 18px;
        }

        .tl-popup-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.25);
          z-index: 1040;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }

        .tl-popup-card {
          width: min(720px, 95vw);
          max-height: 85vh;
          overflow: auto;
          background: #ffffff;
          border-radius: 10px;
          box-shadow: 0 10px 35px rgba(0, 0, 0, 0.25);
          border: 1px solid #d1d8dd;
        }

        .tl-popup-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 16px 18px 12px 18px;
          border-bottom: 1px solid #e5e7eb;
        }

        .tl-popup-title {
          font-size: 18px;
          font-weight: 600;
          color: #1f2937;
        }

        .tl-popup-close {
          border: 1px solid #c7cdd4;
          background: #f8f9fa;
          color: #111827;
          border-radius: 6px;
          padding: 6px 10px;
          cursor: pointer;
          font-size: 12px;
        }

        .tl-popup-body {
          padding: 14px 18px 18px 18px;
        }

        .tl-popup-grid {
          display: grid;
          grid-template-columns: 180px 1fr;
          gap: 10px 14px;
          align-items: start;
        }

        .tl-popup-label {
          font-weight: 600;
          color: #4b5563;
        }

        .tl-popup-value {
          color: #111827;
          word-break: break-word;
        }

        .tl-popup-footer {
          padding: 0 18px 18px 18px;
          display: flex;
          justify-content: flex-end;
          gap: 10px;
        }

        .tl-popup-open {
          background: #ff0000;
          color: #ffffff;
          border: 1px solid #cc0000;
          border-radius: 6px;
          padding: 8px 12px;
          cursor: pointer;
          font-size: 13px;
        }

        .tl-popup-muted {
          color: #6b7280;
          font-size: 12px;
          margin-bottom: 12px;
        }
      `;
      document.head.appendChild(style);
    }

    const $wrap = $(report.page.wrapper);

    if (!$wrap.find(".tl-legend").length) {
      $wrap.find(".page-content").prepend(`
        <div class="tl-legend">
          <div class="tl-item"><span class="tl-sq tl-startup"></span><span>Start up</span></div>
          <div class="tl-item"><span class="tl-sq tl-breakdown"></span><span>Breakdown</span></div>
          <div class="tl-item"><span class="tl-sq tl-fatigue"></span><span>Fatigue</span></div>
          <div class="tl-item"><span class="tl-sq"></span><span>Non Reported</span></div>
        </div>
      `);
    }

    if (!$wrap.data("tl-bd-click-bound")) {
      $wrap.on("click", ".tl-bd-btn", function (e) {
        e.preventDefault();
        e.stopPropagation();

        const docname = $(this).attr("data-docname");
        if (!docname) {
          frappe.msgprint(__("Breakdown document was not found for this block."));
          return;
        }

        show_breakdown_popup(docname);
      });

      $wrap.data("tl-bd-click-bound", true);
    }
  },

  formatter: function (value, row, column, data, default_formatter) {
    if (column.fieldname && column.fieldname.startsWith("h_")) {
      const v = (value || "").toString().trim();

      if (!v) {
        return `<div class="tl-slot tl-empty">&nbsp;</div>`;
      }

      if (v === "S") {
        return `<div class="tl-slot tl-S">&nbsp;</div>`;
      }

      if (v === "F") {
        return `<div class="tl-slot tl-F">&nbsp;</div>`;
      }

      if (v.startsWith("B::")) {
        const docname = v.substring(3).trim();
        const safeDocname = frappe.utils.escape_html(docname);

        return `
          <div class="tl-slot tl-B">
            <button class="tl-bd-btn" data-docname="${safeDocname}" type="button">
              B/D Detail
            </button>
          </div>
        `;
      }

      return `<div class="tl-slot tl-empty">&nbsp;</div>`;
    }

    if (column.fieldname === "end_0600") {
      return `<div class="tl-slot tl-empty">&nbsp;</div>`;
    }

    return default_formatter(value, row, column, data);
  },
};


function show_breakdown_popup(docname) {
  remove_breakdown_popup();

  frappe.call({
    method: "frappe.client.get",
    args: {
      doctype: "Plant Breakdown or Maintenance",
      name: docname
    },
    callback: function (r) {
      if (!r || !r.message) {
        frappe.msgprint(__("Could not load breakdown details."));
        return;
      }

      const d = r.message;

      const popupHtml = `
        <div class="tl-popup-overlay" id="tl-popup-overlay">
          <div class="tl-popup-card" id="tl-popup-card">
            <div class="tl-popup-header">
              <div class="tl-popup-title">Breakdown Detail</div>
              <button type="button" class="tl-popup-close" id="tl-popup-close">Close</button>
            </div>

            <div class="tl-popup-body">
              <div class="tl-popup-muted">Click anywhere outside this popup to close it.</div>

              <div class="tl-popup-grid">
                <div class="tl-popup-label">Document</div>
                <div class="tl-popup-value">${escape_html(d.name || "")}</div>

                <div class="tl-popup-label">Site</div>
                <div class="tl-popup-value">${escape_html(d.location || "")}</div>

                <div class="tl-popup-label">Shift</div>
                <div class="tl-popup-value">${escape_html(d.shift || "")}</div>

                <div class="tl-popup-label">Plant No.</div>
                <div class="tl-popup-value">${escape_html(d.asset_name || "")}</div>

                <div class="tl-popup-label">Plant Model</div>
                <div class="tl-popup-value">${escape_html(d.item_name || "")}</div>

                <div class="tl-popup-label">Plant Category</div>
                <div class="tl-popup-value">${escape_html(d.asset_category || "")}</div>

                <div class="tl-popup-label">Downtime Type</div>
                <div class="tl-popup-value">${escape_html(d.downtime_type || "")}</div>

                <div class="tl-popup-label">Status</div>
                <div class="tl-popup-value">${escape_html(d.breakdown_status || "")}</div>

                <div class="tl-popup-label">Open/Closed</div>
                <div class="tl-popup-value">${escape_html(d.open_closed || "")}</div>

                <div class="tl-popup-label">Start Time</div>
                <div class="tl-popup-value">${escape_html(d.breakdown_start_datetime || "")}</div>

                <div class="tl-popup-label">Resolved Time</div>
                <div class="tl-popup-value">${escape_html(d.resolved_datetime || "")}</div>

                <div class="tl-popup-label">Breakdown Hours</div>
                <div class="tl-popup-value">${escape_html(as_text(d.breakdown_hours))}</div>

                <div class="tl-popup-label">Reason</div>
                <div class="tl-popup-value">${escape_html(d.breakdown_reason || "")}</div>

                <div class="tl-popup-label">Resolution Summary</div>
                <div class="tl-popup-value">${escape_html(d.resolution_summary || "")}</div>
              </div>
            </div>

            <div class="tl-popup-footer">
              <button type="button" class="tl-popup-open" id="tl-popup-open-full">Open Full Record</button>
            </div>
          </div>
        </div>
      `;

      $("body").append(popupHtml);

      $("#tl-popup-overlay").on("click", function () {
        remove_breakdown_popup();
      });

      $("#tl-popup-card").on("click", function (e) {
        e.stopPropagation();
      });

      $("#tl-popup-close").on("click", function () {
        remove_breakdown_popup();
      });

      $("#tl-popup-open-full").on("click", function () {
        remove_breakdown_popup();
        frappe.set_route("Form", "Plant Breakdown or Maintenance", d.name);
      });
    }
  });
}


function remove_breakdown_popup() {
  $("#tl-popup-overlay").remove();
}


function escape_html(value) {
  return frappe.utils.escape_html(as_text(value));
}


function as_text(value) {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}