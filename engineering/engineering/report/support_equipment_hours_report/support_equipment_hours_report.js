frappe.query_reports["Support Equipment Hours Report"] = {
  filters: [
    {
      fieldname: "location",
      label: __("Site"),
      fieldtype: "Link",
      options: "Location",
      reqd: 1
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      reqd: 1
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      reqd: 1
    },
    {
      fieldname: "equipment_category",
      label: __("Equipment Category"),
      fieldtype: "Select",
      options: "\nWater Pump\nLightning Plant\nGenerator"
    }
  ],

  onload: function (report) {
    add_support_equipment_report_styles();
  },

  refresh: function (report) {
    add_support_equipment_report_styles();
  },

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (!column || !column.fieldname) {
      return value;
    }

    if (column.fieldname.includes("_day_total")) {
      value = `<span style="font-weight:700;">${value}</span>`;
    }

    if (column.fieldname.includes("_night_total")) {
      value = `<span style="font-weight:700;">${value}</span>`;
    }

    if (column.fieldname.endsWith("_daily_total")) {
      value = `
        <span style="
          font-weight:700;
          background:#c6e0b4;
          display:block;
          padding:4px;
          text-align:right;
        ">
          ${value}
        </span>
      `;
    }

    return value;
  }
};


function add_support_equipment_report_styles() {
  if ($("#support-equipment-hours-report-style").length) {
    return;
  }

  $("head").append(`
    <style id="support-equipment-hours-report-style">
      .query-report .dt-header .dt-cell {
        height: 72px !important;
      }

      .query-report .dt-header .dt-cell__content {
        height: 72px !important;
        line-height: 20px !important;
        white-space: normal !important;
        text-align: center !important;
        font-weight: 700 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
      }

      .query-report .dt-row-header {
        height: 72px !important;
      }

      .query-report .dt-cell__content {
        font-size: 13px;
      }

      .query-report .dt-scrollable {
        border: 1px solid #d1d8dd;
      }
    </style>
  `);
}