// Copyright (c) 2026, Isambane Mining (Pty) Ltd
// For license information, please see license.txt

frappe.query_reports["Hourly Downtime Report"] = {
    filters: [
        {
            fieldname: "report_date",
            label: __("Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today(),
            onchange: function () {
                frappe.query_report.refresh();
            }
        },
        {
            fieldname: "hour_slot",
            label: __("Hour"),
            fieldtype: "Select",
            reqd: 1,
            options: [
                "00:00-01:00",
                "01:00-02:00",
                "02:00-03:00",
                "03:00-04:00",
                "04:00-05:00",
                "05:00-06:00",
                "06:00-07:00",
                "07:00-08:00",
                "08:00-09:00",
                "09:00-10:00",
                "10:00-11:00",
                "11:00-12:00",
                "12:00-13:00",
                "13:00-14:00",
                "14:00-15:00",
                "15:00-16:00",
                "16:00-17:00",
                "17:00-18:00",
                "18:00-19:00",
                "19:00-20:00",
                "20:00-21:00",
                "21:00-22:00",
                "22:00-23:00",
                "23:00-24:00"
            ].join("\n"),
            default: get_current_hour_slot(),
            onchange: function () {
                frappe.query_report.refresh();
            }
        },
        {
            fieldname: "site",
            label: __("Site"),
            fieldtype: "Link",
            options: "Location",
            reqd: 1,
            onchange: function () {
                frappe.query_report.refresh();
            }
        }
    ],

    onload: function () {
        add_hourly_downtime_styles();
    },

    refresh: function () {
        add_hourly_downtime_styles();

        frappe.after_ajax(function () {
            render_hourly_downtime_html();
        });
    },

    after_datatable_render: function () {
        render_hourly_downtime_html();
    },

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (!data) {
            return value;
        }

        if (column.fieldname === "status") {
            if (data.status_key === "open") {
                return `<span class="hourly-status-open">${value}</span>`;
            }

            return `<span class="hourly-status-available">${value}</span>`;
        }

        return value;
    }
};


function get_current_hour_slot() {
    const now = moment();
    const hour = now.hour();
    const next_hour = hour + 1;

    if (next_hour >= 24) {
        return "23:00-24:00";
    }

    return `${String(hour).padStart(2, "0")}:00-${String(next_hour).padStart(2, "0")}:00`;
}


function add_hourly_downtime_styles() {
    if ($("#hourly-downtime-styles").length) {
        return;
    }

    $("head").append(`
        <style id="hourly-downtime-styles">
            .hourly-downtime-wrapper {
                background: #ffffff;
                border: 1px solid #d9d9d9;
                border-radius: 12px;
                padding: 14px;
                margin: 10px 0 16px 0;
            }

            .hourly-downtime-title {
                font-size: 18px;
                font-weight: 900;
                margin-bottom: 4px;
                text-transform: uppercase;
            }

            .hourly-downtime-subtitle {
                font-size: 13px;
                color: #666;
                margin-bottom: 14px;
            }

            .hourly-downtime-summary {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: 8px;
                margin-bottom: 14px;
            }

            .hourly-summary-box {
                border-radius: 10px;
                border: 1px solid #e5e7eb;
                background: #f8fafc;
                padding: 10px;
                font-size: 12px;
                font-weight: 800;
            }

            .hourly-summary-box strong {
                display: block;
                font-size: 22px;
                margin-top: 4px;
            }

            .hourly-summary-open {
                background: #ffe5e5;
                color: #a8071a;
                border-color: #ff4d4f;
            }

            .hourly-summary-available {
                background: #e6f7e6;
                color: #237804;
                border-color: #52c41a;
            }

            .hourly-available-by-category {
                background: #e6f7e6;
                color: #237804;
                border: 1px solid #52c41a;
                border-radius: 10px;
                padding: 10px;
                margin-bottom: 14px;
            }

            .hourly-available-title {
                font-size: 13px;
                font-weight: 900;
                margin-bottom: 8px;
            }

            .hourly-available-line {
                display: flex;
                justify-content: space-between;
                gap: 12px;
                padding: 4px 0;
                border-bottom: 1px solid rgba(82, 196, 26, 0.25);
                font-size: 13px;
                font-weight: 800;
            }

            .hourly-available-line:last-child {
                border-bottom: none;
            }

            .hourly-category-section {
                margin-top: 12px;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                overflow: hidden;
            }

            .hourly-category-heading {
                background: #f2f2f2;
                padding: 9px 11px;
                font-weight: 900;
                text-transform: uppercase;
                border-bottom: 1px solid #e5e7eb;
            }

            .hourly-plant-row {
                display: grid;
                grid-template-columns: 34px 120px 1fr;
                gap: 8px;
                align-items: start;
                padding: 8px 11px;
                border-bottom: 1px solid #f0f0f0;
                font-size: 13px;
            }

            .hourly-plant-row:last-child {
                border-bottom: none;
            }

            .hourly-plant-open {
                background: #fff1f0;
                color: #a8071a;
                font-weight: 700;
            }

            .hourly-plant-available {
                background: #f6ffed;
                color: #237804;
            }

            .hourly-plant-status {
                font-size: 16px;
            }

            .hourly-plant-no {
                font-weight: 900;
            }

            .hourly-plant-detail {
                line-height: 1.35;
            }

            .hourly-plant-clickable {
                cursor: pointer;
            }

            .hourly-plant-clickable:hover {
                outline: 2px solid rgba(168, 7, 26, 0.35);
                outline-offset: -2px;
            }

            .hourly-status-open {
                color: #a8071a;
                font-weight: 900;
            }

            .hourly-status-available {
                color: #237804;
                font-weight: 900;
            }
        </style>
    `);
}


function render_hourly_downtime_html() {
    const data = frappe.query_report && frappe.query_report.data ? frappe.query_report.data : [];
    const site = frappe.query_report.get_filter_value("site") || "All Sites";
    const report_date = frappe.query_report.get_filter_value("report_date") || "";
    const hour_slot = frappe.query_report.get_filter_value("hour_slot") || "";

    $(".hourly-downtime-wrapper").remove();

    if (!data.length) {
        $(".report-wrapper").prepend(`
            <div class="hourly-downtime-wrapper">
                <div class="hourly-downtime-title">Hourly Downtime Report</div>
                <div class="hourly-downtime-subtitle">${frappe.utils.escape_html(site)} | ${frappe.utils.escape_html(report_date)} | ${frappe.utils.escape_html(hour_slot)}</div>
                <div>No assets found for this filter.</div>
            </div>
        `);
        return;
    }

    const total = data.length;
    const open = data.filter(row => row.status_key === "open").length;

    const category_order = [
        "ADT",
        "Excavator",
        "Dozer",
        "Water Bowser",
        "Diesel Bowser",
        "Service Truck",
        "FEL",
        "Grader"
    ];

    const grouped = {};

    data.forEach(function (row) {
        const category = row.category_group || row.asset_category || "Uncategorised";

        if (!grouped[category]) {
            grouped[category] = [];
        }

        grouped[category].push(row);
    });

    const available_by_category = {};

    category_order.forEach(function (category) {
        const rows = grouped[category] || [];
        const category_total = rows.length;
        const category_open = rows.filter(function (row) {
            return row.status_key === "open";
        }).length;
        const category_available = category_total - category_open;

        if (category_total > 0) {
            available_by_category[category] = {
                total: category_total,
                available: category_available
            };
        }
    });

    let html = `
        <div class="hourly-downtime-wrapper">
            <div class="hourly-downtime-title">${frappe.utils.escape_html(site)} Fleet Downtime Status</div>
            <div class="hourly-downtime-subtitle">
                Date: ${frappe.utils.escape_html(report_date)} | Hour: ${frappe.utils.escape_html(hour_slot)}
            </div>

            <div class="hourly-downtime-summary">
                <div class="hourly-summary-box">Total Machines<strong>${total}</strong></div>
                <div class="hourly-summary-box hourly-summary-open">Open Downtime<strong>${open}</strong></div>
            </div>

            <div class="hourly-available-by-category">
                <div class="hourly-available-title">Available by Type</div>
                ${category_order.map(function (category) {
                    const item = available_by_category[category];

                    if (!item) {
                        return "";
                    }

                    return `
                        <div class="hourly-available-line">
                            <span>${frappe.utils.escape_html(category)}</span>
                            <strong>${item.available} / ${item.total}</strong>
                        </div>
                    `;
                }).join("")}
            </div>
    `;

    category_order.forEach(function (category) {
        const rows = grouped[category] || [];

        if (!rows.length) {
            return;
        }

        html += `
            <div class="hourly-category-section">
                <div class="hourly-category-heading">${frappe.utils.escape_html(category)}</div>
        `;

        rows.forEach(function (row) {
            const is_open = row.status_key === "open";
            const icon = is_open ? "❌" : "✅";
            const row_class = is_open ? "hourly-plant-open" : "hourly-plant-available";
            const is_clickable = is_open && row.breakdown_docname;
            const clickable_class = is_clickable ? "hourly-plant-clickable" : "";
            const clickable_attr = is_clickable ? `data-breakdown-docname="${frappe.utils.escape_html(row.breakdown_docname)}"` : "";

            let detail = "";

            if (is_open) {
                detail = `
                    ${frappe.utils.escape_html(row.reason || "-")}
                    <br>
                    <small>
                        Open for ${frappe.utils.escape_html(row.open_hours || 0)} hrs at end of hour
                        ${row.start_time ? " | Start: " + frappe.utils.escape_html(row.start_time) : ""}
                    </small>
                `;
            } else {
                detail = frappe.utils.escape_html(row.item_name || "Available");
            }

            html += `
                <div class="hourly-plant-row ${row_class} ${clickable_class}" ${clickable_attr}>
                    <div class="hourly-plant-status">${icon}</div>
                    <div class="hourly-plant-no">${frappe.utils.escape_html(row.plant_no || "")}</div>
                    <div class="hourly-plant-detail">${detail}</div>
                </div>
            `;
        });

        html += `</div>`;
    });

    html += `</div>`;

    $(".report-wrapper").prepend(html);

    $(".hourly-plant-clickable").off("click").on("click", function () {
        const breakdown_docname = $(this).attr("data-breakdown-docname");

        if (breakdown_docname) {
            frappe.set_route("Form", "Plant Breakdown or Maintenance", breakdown_docname);
        }
    });
}