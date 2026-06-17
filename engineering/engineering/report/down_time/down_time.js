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
        load_previous_day_avail_util_summary(report);
    },

    refresh: function (report) {
        hide_generate_button(report);
        add_signoff_button(report);
        setup_mobile_downtime_view(report);
        load_previous_day_avail_util_summary(report);
    },

    after_datatable_render: function (report) {
        render_mobile_downtime_cards(report);
        render_desktop_downtime_verification();
        load_previous_day_avail_util_summary(report);
    }
};

function add_signoff_button(report) {
    if (!report || !report.page) {
        return;
    }

    $(".downtime-signoff-action-wrapper").remove();

    const html = `
        <div class="downtime-signoff-action-wrapper">
            <button type="button" class="btn btn-danger downtime-signoff-action-button">
                Save Downtime Sign-off
            </button>
        </div>
    `;

    $(".report-wrapper").before(html);

    $(".downtime-signoff-action-button").off("click").on("click", function () {
        const report_date = frappe.query_report.get_filter_value("report_date");

        if (!report_date) {
            frappe.msgprint(__("Please select a Date first."));
            return;
        }

        if (!all_downtime_records_verified()) {
            frappe.throw(__("Please verify Downtime first before signing off."));
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
                        signature: values.signature,
                        downtime_comments: get_mobile_downtime_comments()
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

            .downtime-signoff-action-wrapper {
                margin: 10px 0 14px 0;
                display: flex;
                justify-content: flex-end;
            }

            .downtime-signoff-action-button {
                border-radius: 999px;
                padding: 10px 18px;
                font-size: 14px;
                font-weight: 800;
                box-shadow: 0 2px 8px rgba(176, 0, 32, 0.25);
            }

            @media (max-width: 768px) {
                .downtime-signoff-action-wrapper {
                    justify-content: stretch;
                }

                .downtime-signoff-action-button {
                    width: 100%;
                    padding: 13px 18px;
                    font-size: 15px;
                }
            }

            .downtime-desktop-verify-wrapper {
                background: #fff7e6;
                border: 1px solid #ffd591;
                border-radius: 12px;
                padding: 12px;
                margin: 10px 0 14px 0;
            }

            .downtime-desktop-verify-title {
                font-size: 14px;
                font-weight: 800;
                margin-bottom: 8px;
            }

            .downtime-desktop-verify-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 8px;
            }

            .downtime-desktop-verify-item {
                display: flex;
                align-items: center;
                gap: 8px;
                background: #fff;
                border: 1px solid #f0d9a0;
                border-radius: 8px;
                padding: 8px 10px;
                font-size: 13px;
                font-weight: 700;
            }

            .downtime-desktop-verify-item input {
                width: 18px;
                height: 18px;
            }

            @media (max-width: 768px) {
                .downtime-desktop-verify-wrapper {
                    display: none;
                }
            }


            .downtime-avail-util-wrapper {
                background: #fff;
                border: 1px solid #d9d9d9;
                border-radius: 12px;
                padding: 12px;
                margin: 10px 0 14px 0;
            }

            .downtime-avail-util-title {
                font-size: 14px;
                font-weight: 800;
                margin: 10px 0 8px 0;
            }

            .downtime-avail-util-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(120px, 1fr));
                gap: 8px;
                margin-bottom: 8px;
            }

            .downtime-avail-util-bubble {
                background: #f7f7f7;
                border: 1px solid #e5e5e5;
                border-radius: 999px;
                padding: 8px 10px;
                font-size: 12px;
                font-weight: 700;
                text-align: center;
            }

            .downtime-avail-util-bubble strong {
                display: block;
                font-size: 13px;
                margin-bottom: 5px;
            }

            .downtime-avail-util-values {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 5px;
                margin-top: 4px;
            }

            .downtime-avail-util-value {
                background: #fff;
                border: 1px solid #e5e5e5;
                border-radius: 8px;
                padding: 5px;
                font-size: 11px;
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
                .downtime-avail-util-grid {
                    grid-template-columns: 1fr;
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

                .mobile-downtime-verify {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 10px;
                    margin-bottom: 10px;
                    background: #fff7e6;
                    border: 1px solid #ffd591;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 700;
                }

                .mobile-downtime-verify input {
                    width: 20px;
                    height: 20px;
                }

                .mobile-downtime-comment {
                    margin-top: 10px;
                }

                .mobile-downtime-comment textarea {
                    width: 100%;
                    min-height: 72px;
                    border: 1px solid #d9d9d9;
                    border-radius: 8px;
                    padding: 8px;
                    font-size: 13px;
                    resize: vertical;
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
                <label class="mobile-downtime-verify">
                    <input type="checkbox" class="mobile-downtime-verify-checkbox downtime-verify-checkbox">
                    <span>Verify Downtime</span>
                </label>

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

                <div class="mobile-downtime-comment">
                    <span class="mobile-downtime-label">Downtime Comment:</span>
                    <textarea
                        class="mobile-downtime-comment-input"
                        data-plant-no="${frappe.utils.escape_html(row.plant_no || "")}"
                        placeholder="Add comment for this downtime record..."
                    ></textarea>
                </div>
            </div>
        `;
    });

    html += `</div>`;

    $(".report-wrapper").append(html);
}


function render_desktop_downtime_verification() {
    const is_mobile = is_mobile_downtime_view();
    const data = frappe.query_report && frappe.query_report.data ? frappe.query_report.data : [];

    $(".downtime-desktop-verify-wrapper").remove();

    if (is_mobile || !data.length) {
        return;
    }

    let html = `
        <div class="downtime-desktop-verify-wrapper">
            <div class="downtime-desktop-verify-title">Verify Downtime</div>
            <div class="downtime-desktop-verify-grid">
    `;

    data.forEach(function (row) {
        html += `
            <label class="downtime-desktop-verify-item">
                <input type="checkbox" class="downtime-verify-checkbox">
                <span>${frappe.utils.escape_html(row.plant_no || "")}</span>
            </label>
        `;
    });

    html += `
            </div>
        </div>
    `;

    $(".report-wrapper").before(html);
}


function load_previous_day_avail_util_summary(report) {
    const report_date = frappe.query_report.get_filter_value("report_date");
    const site = frappe.query_report.get_filter_value("site") || "";

    if (!report_date) {
        return;
    }

    frappe.call({
        method: "engineering.engineering.report.down_time.down_time.get_previous_day_avail_util_summary",
        args: {
            report_date: report_date,
            site: site
        },
        callback: function (r) {
            render_previous_day_avail_util_summary(r.message || {});
        }
    });
}

function render_previous_day_avail_util_summary(summary) {
    $(".downtime-avail-util-wrapper").remove();

    const production = summary.production || {};
    const spare = summary.spare || {};
    const previous_date = summary.previous_date || "";

    let html = `
        <div class="downtime-avail-util-wrapper">
            <div class="downtime-avail-util-title">
                Previous Day Production Machine Availability and Utilisation ${previous_date ? "(" + frappe.utils.escape_html(previous_date) + ")" : ""}
            </div>
            <div class="downtime-avail-util-grid">
                ${get_avail_util_bubble_html(production.adts)}
                ${get_avail_util_bubble_html(production.excavators)}
                ${get_avail_util_bubble_html(production.dozers)}
            </div>

            <div class="downtime-avail-util-title">
                Previous Day Spare Machine Availability and Utilisation ${previous_date ? "(" + frappe.utils.escape_html(previous_date) + ")" : ""}
            </div>
            <div class="downtime-avail-util-grid">
                ${get_avail_util_bubble_html(spare.adts)}
                ${get_avail_util_bubble_html(spare.excavators)}
                ${get_avail_util_bubble_html(spare.dozers)}
            </div>
        </div>
    `;

    $(".report-wrapper").prepend(html);
}

function get_avail_util_bubble_html(row) {
    row = row || {};

    const label = frappe.utils.escape_html(row.label || "");
    const availability = format_avail_util_percent(row.availability);
    const utilisation = format_avail_util_percent(row.utilisation);

    return `
        <div class="downtime-avail-util-bubble">
            <strong>${label}</strong>
            <div class="downtime-avail-util-values">
                <div class="downtime-avail-util-value">Avail<br>${availability}</div>
                <div class="downtime-avail-util-value">Util<br>${utilisation}</div>
            </div>
        </div>
    `;
}

function format_avail_util_percent(value) {
    if (value === null || value === undefined || value === "") {
        return "N/A";
    }

    return flt(value).toFixed(1) + "%";
}

function get_mobile_downtime_comments() {
    const comments = {};

    $(".mobile-downtime-comment-input").each(function () {
        const plant_no = $(this).data("plant-no");
        const comment = ($(this).val() || "").trim();

        if (plant_no && comment) {
            comments[plant_no] = comment;
        }
    });

    return comments;
}


function all_downtime_records_verified() {
    const checkboxes = $(".downtime-verify-checkbox:visible");

    if (!checkboxes.length) {
        return true;
    }

    let all_verified = true;

    checkboxes.each(function () {
        if (!$(this).is(":checked")) {
            all_verified = false;
        }
    });

    return all_verified;
}