// Copyright (c) 2026, Isambane Mining (Pty) Ltd
// For license information, please see license.txt

frappe.ui.form.on("Hourly Downtime Summary", {
    refresh(frm) {
        frm.set_df_property("summary_message", "read_only", 1);
        frm.set_df_property("channel_id", "read_only", 1);
        frm.set_df_property("sent_to_raven", "read_only", 1);
        frm.set_df_property("report_data_json", "read_only", 1);

        render_downtime_status(frm);

        if (!frm.is_new() && frm.doc.summary_message) {
            frm.add_custom_button(__("Copy Summary Message"), function () {
                frappe.utils.copy_to_clipboard(frm.doc.summary_message);

                frappe.show_alert({
                    message: __("Summary copied"),
                    indicator: "green"
                });
            });
        }
    }
});

function render_downtime_status(frm) {
    if (!frm.fields_dict.downtime_status_html) {
        return;
    }

    let data = [];

    try {
        data = JSON.parse(frm.doc.report_data_json || "[]");
    } catch (e) {
        data = [];
    }

    if (!data.length) {
        frm.fields_dict.downtime_status_html.$wrapper.html(`
            <div class="alert alert-warning">No report data found.</div>
        `);
        return;
    }

    const total = data.length;
    const open = data.filter(row => row.status_key === "open").length;
    const available = total - open;

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

    let html = `
        <style>
            .hds-wrapper {
                border: 1px solid #d9d9d9;
                border-radius: 12px;
                padding: 14px;
                margin-top: 10px;
                background: #fff;
            }

            .hds-title {
                font-size: 18px;
                font-weight: 900;
                text-transform: uppercase;
                margin-bottom: 4px;
            }

            .hds-subtitle {
                font-size: 13px;
                color: #666;
                margin-bottom: 14px;
            }

            .hds-summary {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: 8px;
                margin-bottom: 14px;
            }

            .hds-box {
                border-radius: 10px;
                border: 1px solid #e5e7eb;
                background: #f8fafc;
                padding: 10px;
                font-size: 12px;
                font-weight: 800;
            }

            .hds-box strong {
                display: block;
                font-size: 22px;
                margin-top: 4px;
            }

            .hds-open-box {
                background: #ffe5e5;
                color: #a8071a;
                border-color: #ff4d4f;
            }

            .hds-available-box {
                background: #e6f7e6;
                color: #237804;
                border-color: #52c41a;
            }

            .hds-category {
                margin-top: 12px;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                overflow: hidden;
            }

            .hds-category-heading {
                background: #f2f2f2;
                padding: 9px 11px;
                font-weight: 900;
                text-transform: uppercase;
            }

            .hds-row {
                display: grid;
                grid-template-columns: 34px 120px 1fr;
                gap: 8px;
                padding: 8px 11px;
                border-top: 1px solid #f0f0f0;
                font-size: 13px;
            }

            .hds-row-open {
                background: #fff1f0;
                color: #a8071a;
                font-weight: 700;
            }

            .hds-row-available {
                background: #f6ffed;
                color: #237804;
            }

            .hds-plant {
                font-weight: 900;
            }
        </style>

        <div class="hds-wrapper">
            <div class="hds-title">${frappe.utils.escape_html(frm.doc.site || "")} Fleet Downtime Status</div>
            <div class="hds-subtitle">
                Date: ${frappe.utils.escape_html(frm.doc.report_date || "")}
                | Hour: ${frappe.utils.escape_html(frm.doc.hour_slot || "")}
            </div>

            <div class="hds-summary">
                <div class="hds-box">Total Machines<strong>${total}</strong></div>
                <div class="hds-box hds-open-box">Open Downtime<strong>${open}</strong></div>
                <div class="hds-box hds-available-box">Available<strong>${available}</strong></div>
            </div>
    `;

    category_order.forEach(function (category) {
        const rows = grouped[category] || [];

        if (!rows.length) {
            return;
        }

        html += `
            <div class="hds-category">
                <div class="hds-category-heading">${frappe.utils.escape_html(category)}</div>
        `;

        rows.forEach(function (row) {
            const is_open = row.status_key === "open";
            const icon = is_open ? "❌" : "✅";
            const row_class = is_open ? "hds-row-open" : "hds-row-available";

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
                <div class="hds-row ${row_class}">
                    <div>${icon}</div>
                    <div class="hds-plant">${frappe.utils.escape_html(row.plant_no || "")}</div>
                    <div>${detail}</div>
                </div>
            `;
        });

        html += `</div>`;
    });

    html += `</div>`;

    frm.fields_dict.downtime_status_html.$wrapper.html(html);
}