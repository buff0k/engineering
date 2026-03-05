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

    // Dropdown by asset category (ADT, EXCAVATOR, etc.)
    {
      fieldname: "asset_category",
      label: "ASSETS",
      fieldtype: "Link",
      options: "Asset Category",
      reqd: 0,
    },
  ],

  onload: function (report) {
    // CSS once
    if (!document.getElementById("asset-timeline-css")) {
      const style = document.createElement("style");
      style.id = "asset-timeline-css";
      style.innerHTML = `
        /* Make time headers show fully */
        .dt-header .dt-cell__content {
          white-space: nowrap !important;
          overflow: visible !important;
          text-overflow: clip !important;
        }

        .tl-legend { display:flex; gap:14px; align-items:center; margin:6px 0 10px; flex-wrap:wrap; }
        .tl-item { display:flex; gap:6px; align-items:center; }
        .tl-sq { width:18px; height:12px; border:1px solid #444; display:inline-block; }
        .tl-startup { background:#ffff00; }
        .tl-breakdown { background:#ff0000; }
        .tl-fatigue { background:#00b0f0; }

        .tl-slot { width:100%; height:18px; border-radius:2px; }
        .tl-S { background:#ffff00; }
        .tl-B { background:#ff0000; }
        .tl-F { background:#00b0f0; }
      `;
      document.head.appendChild(style);
    }

    // Legend above grid
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
  },

  formatter: function (value, row, column, data, default_formatter) {
    if (column.fieldname && column.fieldname.startsWith("h_")) {
      const v = (value || "").toString().trim(); // S / B / F / blank
      if (!v) return `<div class="tl-slot">&nbsp;</div>`;
      return `<div class="tl-slot tl-${v}">&nbsp;</div>`;
    }

    // right-side boundary cell (keep blank)
    if (column.fieldname === "end_0600") {
      return `<div class="tl-slot">&nbsp;</div>`;
    }

    return default_formatter(value, row, column, data);
  },
};