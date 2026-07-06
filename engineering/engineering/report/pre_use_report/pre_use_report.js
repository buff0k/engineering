frappe.query_reports["Pre-Use Report"] = {
    filters: [
        {
            fieldname: "start_date",
            label: __("Start Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.add_days(frappe.datetime.get_today(), -7)
        },
        {
            fieldname: "end_date",
            label: __("End Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "site",
            label: __("Site"),
            fieldtype: "Link",
            options: "Location",
            reqd: 1
        },
        {
            fieldname: "shift",
            label: __("Shift"),
            fieldtype: "Select",
            options: ["", "Day", "Night", "Morning", "Afternoon"]
        },
        {
            fieldname: "asset_category",
            label: __("Asset Category"),
            fieldtype: "Link",
            options: "Asset Category"
        },
        {
            fieldname: "asset",
            label: __("Machine"),
            fieldtype: "Link",
            options: "Asset"
        }
    ],

    tree: true,
    name_field: "asset_name",
    parent_field: "asset_category",
    initial_depth: 1,

    onload: function(report) {
        if (!$("#pre-use-report-style").length) {
            $("head").append(`
                <style id="pre-use-report-style">
                    .query-report .dt-scrollable {
                        border-radius: 14px;
                        border: 1px solid #dbe3ea;
                        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
                    }

                    .query-report .dt-header {
                        background: #102a43 !important;
                        color: white !important;
                        font-weight: 700 !important;
                    }

                    .query-report .dt-row:nth-child(even) {
                        background: #f8fafc;
                    }

                    .query-report .dt-row:hover {
                        background: #eef6ff !important;
                    }

                    .pre-use-legend {
                        position: absolute;
                        top: 58px;
                        right: 20px;
                        background: #ffffff;
                        border-radius: 14px;
                        padding: 14px 16px;
                        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.18);
                        font-size: 13px;
                        z-index: 20;
                        min-width: 275px;
                        border: 1px solid #e5e7eb;
                    }

                    .pre-use-legend-title {
                        font-size: 14px;
                        font-weight: 800;
                        color: #102a43;
                        margin-bottom: 8px;
                    }

                    .pre-use-pill {
                        padding: 4px 10px;
                        border-radius: 999px;
                        font-weight: 800;
                        display: inline-block;
                        min-width: 62px;
                        text-align: center;
                    }

                    .pre-use-pill-orange {
                        background: #fff3cd;
                        color: #b45309;
                        border: 1px solid #facc15;
                    }

                    .pre-use-pill-red {
                        background: #fee2e2;
                        color: #b91c1c;
                        border: 1px solid #fca5a5;
                    }

                    .pre-use-pill-green {
                        background: #dcfce7;
                        color: #166534;
                        border: 1px solid #86efac;
                    }

                    .pre-use-machine {
                        font-weight: 900;
                        color: #102a43;
                    }

                    .pre-use-muted {
                        color: #64748b;
                        font-weight: 500;
                    }

                    .pre-use-number {
                        font-weight: 700;
                        color: #334155;
                    }
                </style>
            `);
        }

        if (!report.page.wrapper.find(".pre-use-legend").length) {
            report.page.wrapper.prepend(`
                <div class="pre-use-legend">
                    <div class="pre-use-legend-title">Pre-Use Report Legend</div>
                    <div>🟠 End Hours = 0</div>
                    <div>🔴 Working Hours = 0</div>
                    <div>🔴 Working Hours > 24</div>
                    <div>🟢 Normal Working Hours</div>
                </div>
            `);
        }
    },

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (!data) return value;

        if (column.fieldname === "asset_category") {
            return `<span style="font-weight:800;color:#102a43;">${value}</span>`;
        }

        if (column.fieldname === "asset_name") {
            return `<span class="pre-use-machine">🚜 ${value}</span>`;
        }

        if (column.fieldname === "item_name") {
            return `<span class="pre-use-muted">${value || ""}</span>`;
        }

        if (column.fieldname === "start_hours") {
            return `<span class="pre-use-number">${value}</span>`;
        }

        if (column.fieldname === "end_hours") {
            if (Number(data.end_hours) === 0) {
                return `<span class="pre-use-pill pre-use-pill-orange">${value}</span>`;
            }
            return `<span class="pre-use-number">${value}</span>`;
        }

        if (column.fieldname === "working_hours") {
            if (Number(data.working_hours) === 0) {
                return `<span class="pre-use-pill pre-use-pill-red">${value}</span>`;
            }

            if (Number(data.working_hours) > 24) {
                return `<span class="pre-use-pill pre-use-pill-red">${value}</span>`;
            }

            if (data.working_hours !== null && data.working_hours !== undefined) {
                return `<span class="pre-use-pill pre-use-pill-green">${value}</span>`;
            }
        }

        return value;
    }
};