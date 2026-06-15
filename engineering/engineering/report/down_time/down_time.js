// Copyright (c) 2026, Isambane Mining (Pty) Ltd
// For license information, please see license.txt

frappe.query_reports["Down Time"] = {
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
            fieldname: "site",
            label: __("Site"),
            fieldtype: "Link",
            options: "Location",
            onchange: function () {
                frappe.query_report.refresh();
            }
        },
        {
            fieldname: "asset_category",
            label: __("Asset Category"),
            fieldtype: "Link",
            options: "Asset Category",
            onchange: function () {
                frappe.query_report.refresh();
            }
        },
        {
            fieldname: "shift",
            label: __("Shift"),
            fieldtype: "Select",
            options: "\nDay Shift\nNight Shift",
            onchange: function () {
                frappe.query_report.refresh();
            }
        }
    ],

    onload: function (report) {
        hide_generate_button(report);
        add_signoff_button(report);
        setup_mobile_downtime_view(report);
    },

    refresh: function (report) {
        hide_generate_button(report);
        add_signoff_button(report);
        setup_mobile_downtime_view(report);
    },

    after_datatable_render: function (report) {
        render_mobile_downtime_cards(report);
    }
};

function add_signoff_button(report) {
    if (!report || !report.page) {
        return;
    }

    const button = report.page.add_inner_button(__("Save Sign-off"), function () {
        const report_date = frappe.query_report.get_filter_value("report_date");

        if (!report_date) {
            frappe.msgprint(__("Please select a Date first."));
            return;
        }

        const dialog = new frappe.ui.Dialog({
            title: __("Save Downtime Sign-off"),
            fields: [
                {
                    fieldname: "signature",
                    label: __("Signature"),
                    fieldtype: "Signature",
                    reqd: 1
                }
            ],
            primary_action_label: __("Save"),
            primary_action(values) {
                frappe.call({
                    method: "engineering.engineering.report.down_time.down_time.save_downtime_signoff",
                    args: {
                        report_date: report_date,
                        site: frappe.query_report.get_filter_value("site") || "",
                        asset_category: frappe.query_report.get_filter_value("asset_category") || "",
                        shift: frappe.query_report.get_filter_value("shift") || "",
                        signature: values.signature
                    },
                    freeze: true,
                    freeze_message: __("Saving sign-off..."),
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint(r.message);
                        }

                        dialog.hide();
                    }
                });
            }
        });

        dialog.show();
    });

    button.removeClass("btn-default btn-secondary").addClass("btn-danger");
}

function hide_generate_button(report) {
    if (!report || !report.page) {
        return;
    }

    report.page.clear_primary_action();

    setTimeout(function () {
        report.page.clear_primary_action();

        $(".btn-primary").each(function () {
            if ($(this).text().trim() === "Generate New Report") {
                $(this).hide();
            }
        });
    }, 500);

    setTimeout(function () {
        report.page.clear_primary_action();

        $(".btn-primary").each(function () {
            if ($(this).text().trim() === "Generate New Report") {
                $(this).hide();
            }
        });
    }, 1500);
}



function is_mobile_downtime_view() {
    return window.innerWidth <= 768;
}

function setup_mobile_downtime_view(report) {
    if (!report || !report.page) {
        return;
    }

    add_mobile_downtime_styles();

    frappe.after_ajax(function () {
        render_mobile_downtime_cards(report);
    });

    $(window).off("resize.mobile_downtime").on("resize.mobile_downtime", function () {
        render_mobile_downtime_cards(report);
    });
}

function add_mobile_downtime_styles() {
    if ($("#mobile-downtime-styles").length) {
        return;
    }

    $("head").append(`
        <style id="mobile-downtime-styles">
            .mobile-downtime-wrapper {
                display: none;
            }

            @media (max-width: 768px) {
                .dt-scrollable,
                .datatable,
                .frappe-datatable {
                    display: none !important;
                }

                .mobile-downtime-wrapper {
                    display: block;
                    padding: 10px 4px 80px 4px;
                }

                .mobile-downtime-summary {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 8px;
                    margin-bottom: 12px;
                }

                .mobile-downtime-summary-box {
                    background: #f7f7f7;
                    border: 1px solid #e5e5e5;
                    border-radius: 10px;
                    padding: 10px;
                    font-size: 12px;
                }

                .mobile-downtime-summary-box strong {
                    display: block;
                    font-size: 18px;
                    margin-top: 3px;
                }

                .mobile-downtime-card {
                    background: #fff;
                    border: 1px solid #ddd;
                    border-radius: 12px;
                    padding: 12px;
                    margin-bottom: 10px;
                    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
                }

                .mobile-downtime-title {
                    font-size: 16px;
                    font-weight: 700;
                    margin-bottom: 8px;
                }

                .mobile-downtime-badges {
                    display: flex;
                    gap: 6px;
                    flex-wrap: wrap;
                    margin-bottom: 10px;
                }

                .mobile-downtime-badge {
                    border-radius: 999px;
                    padding: 4px 8px;
                    font-size: 12px;
                    font-weight: 700;
                    background: #eee;
                }

                .mobile-downtime-badge.open {
                    background: #ffe5e5;
                    color: #b00020;
                }

                .mobile-downtime-badge.closed {
                    background: #e8f5e9;
                    color: #1b5e20;
                }

                .mobile-downtime-row {
                    margin-bottom: 7px;
                    font-size: 13px;
                    line-height: 1.35;
                }

                .mobile-downtime-label {
                    font-weight: 700;
                    color: #555;
                }
            }
        </style>
    `);
}

function render_mobile_downtime_cards(report) {
    const is_mobile = is_mobile_downtime_view();
    const data = frappe.query_report && frappe.query_report.data ? frappe.query_report.data : [];

    $(".mobile-downtime-wrapper").remove();

    if (!is_mobile) {
        $(".dt-scrollable, .datatable, .frappe-datatable").show();
        return;
    }

    const total_records = data.length;
    const open_records = data.filter(row => String(row.open_closed || "").toLowerCase() === "open").length;
    const closed_records = data.filter(row => String(row.open_closed || "").toLowerCase() === "closed").length;
    const total_hours = data.reduce((total, row) => total + flt(row.breakdown_hours || 0), 0);

    let html = `
        <div class="mobile-downtime-wrapper">
            <div class="mobile-downtime-summary">
                <div class="mobile-downtime-summary-box">Records<strong>${total_records}</strong></div>
                <div class="mobile-downtime-summary-box">Total Hours<strong>${total_hours.toFixed(2)}</strong></div>
                <div class="mobile-downtime-summary-box">Open<strong>${open_records}</strong></div>
                <div class="mobile-downtime-summary-box">Closed<strong>${closed_records}</strong></div>
            </div>
    `;

    if (!data.length) {
        html += `<div class="mobile-downtime-card">No downtime records found.</div>`;
    }

    data.forEach(function (row) {
        const status = row.open_closed || "";
        const status_class = String(status).toLowerCase() === "open" ? "open" : "closed";

        html += `
            <div class="mobile-downtime-card">
                <div class="mobile-downtime-title">${frappe.utils.escape_html(row.plant_no || "")}</div>

                <div class="mobile-downtime-badges">
                    <span class="mobile-downtime-badge ${status_class}">${frappe.utils.escape_html(status)}</span>
                    <span class="mobile-downtime-badge">${frappe.utils.escape_html(row.breakdown_hours || 0)} hrs</span>
                    <span class="mobile-downtime-badge">${frappe.utils.escape_html(row.asset_category || "")}</span>
                </div>

                <div class="mobile-downtime-row">
                    <span class="mobile-downtime-label">Site:</span>
                    ${frappe.utils.escape_html(row.site || "")}
                </div>

                <div class="mobile-downtime-row">
                    <span class="mobile-downtime-label">Start:</span>
                    ${frappe.utils.escape_html(row.breakdown_start_datetime || "")}
                </div>

                <div class="mobile-downtime-row">
                    <span class="mobile-downtime-label">Back in Production:</span>
                    ${frappe.utils.escape_html(row.resolved_datetime || "")}
                </div>

                <div class="mobile-downtime-row">
                    <span class="mobile-downtime-label">Reason:</span><br>
                    ${frappe.utils.escape_html(row.breakdown_reason || "")}
                </div>

                <div class="mobile-downtime-row">
                    <span class="mobile-downtime-label">Resolution:</span><br>
                    ${frappe.utils.escape_html(row.resolution_summary || "")}
                </div>
            </div>
        `;
    });

    html += `</div>`;

    $(".report-wrapper").append(html);
}