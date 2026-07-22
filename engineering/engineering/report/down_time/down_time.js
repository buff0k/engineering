// Copyright (c) 2026, Isambane Mining (Pty) Ltd
// For license information, please see license.txt

let downtime_mobile_comment_cache = {};

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

    formatter: function (value, row, column, data, default_formatter) {
        if (column.fieldname === "downtime_comment") {
            const plant_no = data && data.plant_no ? data.plant_no : "";

            return `
                <input
                    type="text"
                    class="form-control downtime-comment-input"
                    data-plant-no="${frappe.utils.escape_html(plant_no)}"
                    placeholder="Add comment..."
                    style="height: 28px; min-width: 220px;"
                >
            `;
        }

        return default_formatter(value, row, column, data);
    },

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
        render_downtime_cards(report);
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

    $(".report-wrapper").after(html);

    $(".downtime-signoff-action-button").off("click").on("click", function () {
        const report_date = frappe.query_report.get_filter_value("report_date");

        if (!report_date) {
            frappe.msgprint(__("Please select a Date first."));
            return;
        }

        if (!all_downtime_records_verified()) {
            frappe.throw(__("Please verify all Downtime records before signing off."));
            return;
        }

        if (!$(".downtime-au-verify-checkbox").is(":checked")) {
            frappe.throw(__("Please verify the previous day Availability and Utilisation before signing off."));
            return;
        }

        const engineering_roles = [
            "Engineering Area Manager",
            "Engineering Foreman",
            "Engineering Manager",
            "Engineering Plant Manager",
            "Engineering Supervisor",
            "Engineering User"
        ];

        const production_roles = [
            "Production Manager",
            "Production Supervisor",
            "Production Foreman",
            "Production User"
        ];

        const can_sign_engineering = engineering_roles.some(function (role) {
            return frappe.user_roles.includes(role);
        });

        const can_sign_production = production_roles.some(function (role) {
            return frappe.user_roles.includes(role);
        });

        const signoff_options = [];

        if (can_sign_engineering) {
            signoff_options.push("Engineering");
        }

        if (can_sign_production) {
            signoff_options.push("Production");
        }

        if (!signoff_options.length) {
            frappe.throw(__(
                "You do not have permission to sign this downtime report."
            ));
            return;
        }

        const dialog = new frappe.ui.Dialog({
            title: __("Save Downtime Sign-off"),
            fields: [
                {
                    fieldname: "signoff_section",
                    label: __("Sign-off Section"),
                    fieldtype: "Select",
                    options: signoff_options.join("\n"),
                    default: signoff_options[0],
                    reqd: 1
                },
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
                        signoff_section: values.signoff_section,
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
    return window.matchMedia("(max-width: 1024px), (pointer: coarse)").matches;
}

function setup_mobile_downtime_view(report) {
    if (!report || !report.page) {
        return;
    }

    add_mobile_downtime_styles();

    frappe.after_ajax(function () {
        render_downtime_cards(report);
    });

    $(window).off("resize.mobile_downtime").on("resize.mobile_downtime", function () {
        const active = document.activeElement;

        if (
            active &&
            (
                active.classList.contains("mobile-downtime-comment-input") ||
                active.classList.contains("downtime-comment-input") ||
                active.tagName === "TEXTAREA" ||
                active.tagName === "INPUT"
            )
        ) {
            return;
        }

        render_downtime_cards(report);
    });
}


function add_mobile_downtime_styles() {
    if ($("#mobile-downtime-styles").length) {
        return;
    }

    $("head").append(`
        <style id="mobile-downtime-styles">
            .query-report .dt-scrollable,
            .query-report .datatable,
            .query-report .frappe-datatable {
                display: none !important;
            }

            .mobile-downtime-wrapper {
                display: block;
                width: 100%;
                margin: 0 auto;
                padding: 10px 0 80px 0;
                box-sizing: border-box;
            }

            .mobile-downtime-summary {
                display: grid;
                grid-template-columns: repeat(4, minmax(140px, 1fr));
                gap: 12px;
                margin-bottom: 14px;
            }

            .mobile-downtime-summary-box {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 14px;
                font-size: 12px;
                color: #6b7280;
                box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
            }

            .mobile-downtime-summary-box strong {
                display: block;
                font-size: 22px;
                color: #111827;
                margin-top: 5px;
            }

            .downtime-card-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(300px, 1fr));
                gap: 14px;
                align-items: stretch;
            }

            .mobile-downtime-card {
                background: #ffffff;
                border: 1px solid #dcdfe4;
                border-radius: 12px;
                padding: 14px;
                box-shadow: 0 2px 7px rgba(0, 0, 0, 0.06);
                display: flex;
                flex-direction: column;
                min-width: 0;
            }

            .mobile-downtime-card:hover {
                border-color: #c6cbd2;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.09);
            }

            .mobile-downtime-verify {
                display: flex;
                align-items: center;
                gap: 9px;
                padding: 10px 12px;
                margin-bottom: 12px;
                background: #fff7e6;
                border: 1px solid #ffd591;
                border-radius: 9px;
                font-size: 14px;
                font-weight: 700;
                cursor: pointer;
            }

            .mobile-downtime-verify input {
                width: 19px;
                height: 19px;
                margin: 0;
            }

            .mobile-downtime-title {
                font-size: 18px;
                font-weight: 800;
                color: #1f2937;
                margin-bottom: 9px;
            }

            .mobile-downtime-badges {
                display: flex;
                gap: 7px;
                flex-wrap: wrap;
                margin-bottom: 12px;
            }

            .mobile-downtime-badge {
                border-radius: 999px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: 700;
                background: #f1f3f5;
                color: #4b5563;
            }

            .mobile-downtime-badge.open {
                background: #ffe5e5;
                color: #b00020;
            }

            .mobile-downtime-badge.closed {
                background: #e8f5e9;
                color: #1b5e20;
            }

            .mobile-downtime-details {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 9px 14px;
                margin-bottom: 10px;
            }

            .mobile-downtime-row {
                font-size: 13px;
                line-height: 1.4;
                color: #4b5563;
                min-width: 0;
                overflow-wrap: anywhere;
            }

            .mobile-downtime-row.full-width {
                grid-column: 1 / -1;
            }

            .mobile-downtime-label {
                font-weight: 800;
                color: #374151;
            }

            .mobile-downtime-comment {
                margin-top: auto;
                padding-top: 10px;
            }

            .mobile-downtime-comment textarea {
                width: 100%;
                min-height: 76px;
                border: 1px solid #d1d5db;
                border-radius: 9px;
                padding: 9px;
                font-size: 13px;
                resize: vertical;
                background: #ffffff;
                box-sizing: border-box;
            }

            .mobile-downtime-comment textarea:focus {
                border-color: #f0ad00;
                outline: none;
                box-shadow: 0 0 0 2px rgba(240, 173, 0, 0.15);
            }

            .downtime-signoff-action-wrapper {
                position: sticky;
                bottom: 10px;
                z-index: 100;
                margin: 14px 0;
                display: flex;
                justify-content: flex-end;
                pointer-events: none;
            }

            .downtime-signoff-action-button {
                pointer-events: auto;
                border-radius: 999px;
                padding: 12px 22px;
                font-size: 14px;
                font-weight: 800;
                box-shadow: 0 3px 12px rgba(176, 0, 32, 0.25);
            }

            .downtime-avail-util-wrapper {
                background: #ffffff;
                border: 1px solid #d9d9d9;
                border-radius: 12px;
                padding: 14px;
                margin: 10px 0 14px 0;
            }

            .downtime-avail-util-title {
                font-size: 14px;
                font-weight: 800;
                margin: 10px 0 8px 0;
            }

            .tmm-equipment-downtime-heading {
                background: #f2f2f2;
                border: 2px solid #111;
                padding: 9px;
                margin: 10px 0 8px 0;
                font-size: 13px;
                font-weight: 800;
                color: #111;
                text-align: center;
                text-transform: uppercase;
            }

            .downtime-avail-util-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(120px, 1fr));
                gap: 8px;
                margin-bottom: 8px;
            }

            .downtime-prev-breakdown-section {
                margin-top: 12px;
                padding-top: 12px;
                border-top: 1px solid #e5e7eb;
            }

            .downtime-prev-breakdown-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                flex-wrap: wrap;
                margin-bottom: 8px;
            }

            .downtime-prev-breakdown-title {
                font-size: 13px;
                font-weight: 800;
                color: #374151;
            }

            .downtime-prev-breakdown-button {
                border: 1px solid #1d4ed8 !important;
                background: #dbeafe !important;
                color: #1e3a8a !important;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 700;
                white-space: nowrap;
            }

            .downtime-prev-breakdown-button:hover {
                border-color: #1e40af !important;
                background: #bfdbfe !important;
                color: #1e3a8a !important;
            }

            .downtime-au-verify-wrapper {
                display: flex;
                align-items: center;
                gap: 10px;
                flex-wrap: wrap;
            }

            .downtime-au-verify-label {
                display: flex;
                align-items: center;
                gap: 7px;
                margin: 0;
                padding: 7px 10px;
                background: #fff7e6;
                border: 1px solid #ffd591;
                border-radius: 8px;
                color: #7a4f01;
                font-size: 12px;
                font-weight: 700;
                cursor: pointer;
                white-space: nowrap;
            }

            .downtime-au-verify-label input {
                width: 17px;
                height: 17px;
                margin: 0;
            }

            .downtime-prev-breakdown-list {
                display: grid;
                grid-template-columns: repeat(6, minmax(160px, 1fr));
                gap: 8px;
            }

            .downtime-prev-breakdown-item {
                position: relative;
                background: #ffffff;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 9px 10px;
                font-size: 12px;
                color: #374151;
                line-height: 1.4;
                cursor: pointer;
                overflow: visible;
            }

            .downtime-prev-breakdown-item strong {
                color: #111827;
            }

            .downtime-prev-breakdown-item:hover {
                background: #dbeafe;
                border-color: #1d4ed8;
                color: #1e3a8a;
            }

            .downtime-prev-breakdown-item:hover strong {
                color: #1e3a8a;
            }

            .downtime-prev-breakdown-tooltip {
                display: none;
                position: absolute;
                left: 50%;
                top: calc(100% + 8px);
                transform: translateX(-50%);
                width: 300px;
                background: #ffffff;
                border: 1px solid #93c5fd;
                border-radius: 10px;
                padding: 12px;
                color: #1f2937;
                box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);
                z-index: 500;
                font-size: 12px;
                line-height: 1.5;
            }

            .downtime-prev-breakdown-item:hover .downtime-prev-breakdown-tooltip {
                display: block;
            }

            .downtime-prev-breakdown-tooltip-row {
                margin-bottom: 6px;
            }

            .downtime-prev-breakdown-tooltip-row:last-child {
                margin-bottom: 0;
            }

            @media (max-width: 1400px) {
                .downtime-prev-breakdown-list {
                    grid-template-columns: repeat(3, minmax(160px, 1fr));
                }
            }

            .downtime-prev-breakdown-empty {
                background: #fafafa;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 8px 10px;
                font-size: 12px;
                color: #6b7280;
            }

            .downtime-prev-breakdown-more {
                font-size: 12px;
                font-weight: 700;
                color: #6b7280;
                margin-top: 2px;
            }

            .downtime-avail-util-bubble {
                background: #f7f7f7;
                border: 1px solid #e5e5e5;
                border-radius: 12px;
                padding: 9px;
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
            }

            .downtime-avail-util-value {
                background: #fff;
                border: 1px solid #e5e5e5;
                border-radius: 8px;
                padding: 6px;
                font-size: 11px;
                font-weight: 800;
            }

            .downtime-au-red {
                background: #ffe5e5 !important;
                border-color: #ff4d4f !important;
                color: #a8071a !important;
            }

            .downtime-au-yellow {
                background: #fff7d6 !important;
                border-color: #faad14 !important;
                color: #ad6800 !important;
            }

            .downtime-au-green {
                background: #e6f7e6 !important;
                border-color: #52c41a !important;
                color: #237804 !important;
            }

            .downtime-au-na {
                background: #f5f5f5 !important;
                border-color: #d9d9d9 !important;
                color: #8c8c8c !important;
            }

            @media (max-width: 1350px) {
                .downtime-card-grid {
                    grid-template-columns: repeat(2, minmax(300px, 1fr));
                }
            }

            @media (max-width: 1024px), (pointer: coarse) {
                .mobile-downtime-wrapper {
                    max-width: 720px;
                    padding: 10px 8px 80px 8px;
                }

                .downtime-card-grid {
                    grid-template-columns: 1fr;
                    gap: 10px;
                }

                .mobile-downtime-summary {
                    grid-template-columns: repeat(2, 1fr);
                    gap: 8px;
                }

                .mobile-downtime-details {
                    grid-template-columns: 1fr;
                }

                .mobile-downtime-row.full-width {
                    grid-column: auto;
                }

                .downtime-avail-util-grid {
                    grid-template-columns: 1fr;
                }

                .downtime-prev-breakdown-list {
                    grid-template-columns: repeat(2, minmax(140px, 1fr));
                }

                .downtime-prev-breakdown-tooltip {
                    display: none !important;
                }

                .downtime-prev-breakdown-button {
                    width: 100%;
                    white-space: normal;
                }

                .downtime-au-verify-wrapper {
                    width: 100%;
                }

                .downtime-au-verify-label {
                    width: 100%;
                    justify-content: center;
                }

                .downtime-signoff-action-wrapper {
                    justify-content: stretch;
                }

                .downtime-signoff-action-button {
                    width: 100%;
                    padding: 13px 18px;
                    font-size: 15px;
                }
            }
        </style>
    `);
}

function format_downtime_duration(value) {
    const total_minutes = Math.round(flt(value || 0) * 60);
    const hours = Math.floor(total_minutes / 60);
    const minutes = total_minutes % 60;

    const parts = [];

    if (hours > 0) {
        parts.push(hours + (hours === 1 ? " hour" : " hours"));
    }

    if (minutes > 0 || hours === 0) {
        parts.push(minutes + (minutes === 1 ? " min" : " mins"));
    }

    return parts.join(" ");
}

function render_downtime_cards(report) {
    const data =
        frappe.query_report && frappe.query_report.data
            ? frappe.query_report.data
            : [];

    $(".mobile-downtime-wrapper").remove();
    $(".downtime-desktop-verify-wrapper").remove();

    $(".dt-scrollable, .datatable, .frappe-datatable").hide();

    const total_records = data.length;

    const open_records = data.filter(function (row) {
        return String(row.open_closed || "").toLowerCase() === "open";
    }).length;

    const closed_records = data.filter(function (row) {
        return String(row.open_closed || "").toLowerCase() === "closed";
    }).length;

    const total_hours = data.reduce(function (total, row) {
        return total + flt(row.breakdown_hours || 0);
    }, 0);

    let html = `
        <div class="mobile-downtime-wrapper">
            <div class="mobile-downtime-summary">
                <div class="mobile-downtime-summary-box">
                    Records
                    <strong>${total_records}</strong>
                </div>

                <div class="mobile-downtime-summary-box">
                    Total Downtime
                    <strong>${format_downtime_duration(total_hours)}</strong>
                </div>

                <div class="mobile-downtime-summary-box">
                    Open
                    <strong>${open_records}</strong>
                </div>

                <div class="mobile-downtime-summary-box">
                    Closed
                    <strong>${closed_records}</strong>
                </div>
            </div>

            <div class="downtime-card-grid">
    `;

    if (!data.length) {
        html += `
            <div class="mobile-downtime-card">
                No downtime records found.
            </div>
        `;
    }

    data.forEach(function (row) {
        const status = row.open_closed || "";

        const status_class =
            String(status).toLowerCase() === "open"
                ? "open"
                : "closed";

        const plant_no = row.plant_no || "";
        const record_key = row.breakdown_docname || plant_no;

        html += `
            <div class="mobile-downtime-card">
                <label class="mobile-downtime-verify">
                    <input
                        type="checkbox"
                        class="mobile-downtime-verify-checkbox downtime-verify-checkbox"
                        data-record-key="${frappe.utils.escape_html(record_key)}"
                    >
                    <span>Verify Downtime</span>
                </label>

                <div class="mobile-downtime-title">
                    ${frappe.utils.escape_html(plant_no)}
                </div>

                <div class="mobile-downtime-badges">
                    <span class="mobile-downtime-badge ${status_class}">
                        ${frappe.utils.escape_html(status)}
                    </span>

                    <span class="mobile-downtime-badge">
                        ${frappe.utils.escape_html(
                            format_downtime_duration(row.breakdown_hours)
                        )}
                    </span>

                    <span class="mobile-downtime-badge">
                        ${frappe.utils.escape_html(row.asset_category || "")}
                    </span>
                </div>

                <div class="mobile-downtime-details">
                    <div class="mobile-downtime-row">
                        <span class="mobile-downtime-label">Site:</span><br>
                        ${frappe.utils.escape_html(row.site || "")}
                    </div>

                    <div class="mobile-downtime-row">
                        <span class="mobile-downtime-label">Start:</span><br>
                        ${frappe.utils.escape_html(row.breakdown_start_datetime || "")}
                    </div>

                    <div class="mobile-downtime-row full-width">
                        <span class="mobile-downtime-label">Back in Production:</span><br>
                        ${frappe.utils.escape_html(row.resolved_datetime || "Still Open")}
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

                <div class="mobile-downtime-comment">
                    <span class="mobile-downtime-label">
                        Downtime Comment:
                    </span>

                    <textarea
                        class="mobile-downtime-comment-input"
                        data-plant-no="${frappe.utils.escape_html(plant_no)}"
                        placeholder="Add comment for this downtime record..."
                    >${frappe.utils.escape_html(
                        downtime_mobile_comment_cache[plant_no] || ""
                    )}</textarea>
                </div>
            </div>
        `;
    });

    html += `
            </div>
        </div>
    `;

    $(".report-wrapper").append(html);

    $(".mobile-downtime-comment-input")
        .off("input.mobile_comment")
        .on("input.mobile_comment", function () {
            const plant_no = $(this).data("plant-no");
            downtime_mobile_comment_cache[plant_no] = $(this).val() || "";
        });
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
    const previous_day_breakdowns = summary.previous_day_breakdowns || [];
    const site = frappe.query_report.get_filter_value("site") || "";

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

            <div class="downtime-prev-breakdown-section">
                <div class="downtime-prev-breakdown-header">
                    <div class="downtime-prev-breakdown-title">
                        Previous Day Downtime Summary ${previous_date ? "(" + frappe.utils.escape_html(previous_date) + ")" : ""}
                    </div>

                    <div class="downtime-au-verify-wrapper">
                        <label class="downtime-au-verify-label">
                            <input
                                type="checkbox"
                                class="downtime-au-verify-checkbox"
                            >
                            <span>Verify Previous Day A&amp;U</span>
                        </label>

                        <button
                            type="button"
                            class="btn btn-default downtime-prev-breakdown-button"
                            data-previous-date="${frappe.utils.escape_html(previous_date)}"
                            data-site="${frappe.utils.escape_html(site)}"
                        >
                            Click the Button to see more detail on previous day Downtimes
                        </button>
                    </div>
                </div>

                ${get_previous_day_breakdown_summary_html(previous_day_breakdowns)}
            </div>
        </div>
    `;

    $(".report-wrapper").prepend(html);

    $(".tmm-equipment-downtime-heading").remove();

    $(".downtime-avail-util-wrapper").after(`
        <div class="tmm-equipment-downtime-heading">
            TMM EQUIPMENT DOWNTIME
        </div>
    `);

    $(".downtime-prev-breakdown-button").off("click").on("click", function () {
        const previous_date = $(this).data("previous-date") || "";
        const site = $(this).data("site") || "";
        const url = get_previous_day_breakdown_report_url(previous_date, site);
        window.open(url, "_blank");
    });
}


function get_previous_day_breakdown_summary_html(rows) {
    rows = rows || [];

    if (!rows.length) {
        return `
            <div class="downtime-prev-breakdown-empty">
                No previous day downtimes found.
            </div>
        `;
    }

    const visible_rows = rows;

    let html = `<div class="downtime-prev-breakdown-list">`;

    visible_rows.forEach(function (row) {
        const plant_no = frappe.utils.escape_html(row.plant_no || "");
        const reason = truncate_previous_day_breakdown_reason(row.reason || "", 28);
        const full_reason = frappe.utils.escape_html(row.reason || "");
        const status = frappe.utils.escape_html(row.status || "");
        const start = frappe.utils.escape_html(row.start || "");
        const resolved = frappe.utils.escape_html(row.resolved || "Still Open");
        const hours = frappe.utils.escape_html(
            format_downtime_duration(row.hours)
        );

        html += `
            <div class="downtime-prev-breakdown-item">
                <strong>${plant_no}</strong> - ${reason}

                <div class="downtime-prev-breakdown-tooltip">
                    <div class="downtime-prev-breakdown-tooltip-row">
                        <strong>Fleet No:</strong> ${plant_no}
                    </div>

                    <div class="downtime-prev-breakdown-tooltip-row">
                        <strong>Reason:</strong> ${full_reason}
                    </div>

                    <div class="downtime-prev-breakdown-tooltip-row">
                        <strong>Status:</strong> ${status}
                    </div>

                    <div class="downtime-prev-breakdown-tooltip-row">
                        <strong>Downtime:</strong> ${hours}
                    </div>

                    <div class="downtime-prev-breakdown-tooltip-row">
                        <strong>Start:</strong> ${start}
                    </div>

                    <div class="downtime-prev-breakdown-tooltip-row">
                        <strong>Back in Production:</strong> ${resolved}
                    </div>
                </div>
            </div>
        `;
    });

    html += `</div>`;

    return html;
}

function truncate_previous_day_breakdown_reason(reason, max_length) {
    reason = String(reason || "");

    if (reason.length <= max_length) {
        return frappe.utils.escape_html(reason);
    }

    return frappe.utils.escape_html(reason.slice(0, max_length).trim()) + "......";
}

function get_previous_day_breakdown_report_url(previous_date, site) {
    const params = new URLSearchParams({
        from_date: previous_date || "",
        to_date: previous_date || "",
        location: site || "",
        machine_scope: "Include Swing/Spare"
    });

    return window.location.origin + "/desk/query-report/Availability%20and%20Utilisation%20Month%20End%20Report?" + params.toString();
}



function get_avail_util_bubble_html(row) {
    row = row || {};

    const raw_availability = row.availability;
    const raw_utilisation = row.utilisation;

    const label = frappe.utils.escape_html(row.label || "");
    const availability = format_avail_util_percent(raw_availability);
    const utilisation = format_avail_util_percent(raw_utilisation);

    const availability_class = get_avail_util_colour_class(raw_availability, "availability");
    const utilisation_class = get_avail_util_colour_class(raw_utilisation, "utilisation");

    return `
        <div class="downtime-avail-util-bubble">
            <strong>${label}</strong>
            <div class="downtime-avail-util-values">
                <div class="downtime-avail-util-value ${availability_class}">Avail<br>${availability}</div>
                <div class="downtime-avail-util-value ${utilisation_class}">Util<br>${utilisation}</div>
            </div>
        </div>
    `;
}

function get_avail_util_colour_class(value, type) {
    if (value === null || value === undefined || value === "") {
        return "downtime-au-na";
    }

    const percent = flt(value);

    if (type === "availability") {
        if (percent <= 75) {
            return "downtime-au-red";
        }

        if (percent <= 84) {
            return "downtime-au-yellow";
        }

        return "downtime-au-green";
    }

    if (percent <= 70) {
        return "downtime-au-red";
    }

    if (percent <= 79) {
        return "downtime-au-yellow";
    }

    return "downtime-au-green";
}


function format_avail_util_percent(value) {
    if (value === null || value === undefined || value === "") {
        return "N/A";
    }

    return flt(value).toFixed(1) + "%";
}

function get_mobile_downtime_comments() {
    const comments = {};

    $(".mobile-downtime-comment-input, .downtime-comment-input").each(function () {
        const plant_no = $(this).data("plant-no");
        const comment = ($(this).val() || "").trim();

        if (plant_no && comment) {
            comments[plant_no] = comment;
            downtime_mobile_comment_cache[plant_no] = comment;
        }
    });

    Object.keys(downtime_mobile_comment_cache || {}).forEach(function (plant_no) {
        const comment = (downtime_mobile_comment_cache[plant_no] || "").trim();

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