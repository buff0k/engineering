frappe.query_reports["Availability and utilization Asset timeline"] = {
    filters: [
        {
            fieldname: "site",
            label: "Site",
            fieldtype: "Link",
            options: "Location",
            reqd: 1,
            on_change: function (query_report) {
                schedule_report_refresh(query_report);
            }
        },
        {
            fieldname: "start_date",
            label: "Start Date",
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today(),
            on_change: function (query_report) {
                sync_end_date_if_blank(query_report);
                schedule_report_refresh(query_report);
            }
        },
        {
            fieldname: "end_date",
            label: "End Date",
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today(),
            on_change: function (query_report) {
                schedule_report_refresh(query_report);
            }
        },
        {
            fieldname: "asset_category",
            label: "Asset Category",
            fieldtype: "Select",
            options: [
                "",
                "Excavator",
                "Dozer",
                "ADT",
                "Water Bowser",
                "Diesel Bowser",
                "Drills",
                "Grader",
                "FEL",
                "TLB"
            ].join("\n"),
            on_change: function (query_report) {
                schedule_report_refresh(query_report);
            }
        }
    ],

    onload: function (report) {
        inject_timeline_styles();
        render_timeline_legend(report);

        // expose popup globally so onclick from HTML works
        window.show_bd_popup = show_bd_popup;
    },

    refresh: function (report) {
        inject_timeline_styles();
        render_timeline_legend(report);

        // keep popup globally available after refresh
        window.show_bd_popup = show_bd_popup;
    },

    formatter: function (value, row, column, data, default_formatter) {
        const raw = value || "";
        const formatted = default_formatter(value, row, column, data);

        if (!column || !column.fieldname) {
            return formatted;
        }

        if (
            column.fieldname === "asset" ||
            column.fieldname === "no" ||
            column.fieldname === "end_marker"
        ) {
            return formatted;
        }

        if (typeof raw === "string" && raw.startsWith("B::")) {
            const docname = raw.split("B::")[1] || "";
            const safe_docname = String(docname).replace(/'/g, "\\'");
            const slot_label = String(column.label || "").replace(/'/g, "\\'");

            return `
                <div class="au-cell au-cell-breakdown">
                    <button
                        type="button"
                        class="au-bd-btn"
                        onclick="window.show_bd_popup('${safe_docname}', '${slot_label}')"
                    >
                        B/D Detail
                    </button>
                </div>
            `;
        }

        if (raw === "S") {
            return `<div class="au-cell au-cell-startup"></div>`;
        }

        if (raw === "F") {
            return `<div class="au-cell au-cell-fatigue"></div>`;
        }

        return `<div class="au-cell au-cell-empty"></div>`;
    }
};


let au_report_refresh_timer = null;

function schedule_report_refresh(query_report) {
    if (au_report_refresh_timer) {
        clearTimeout(au_report_refresh_timer);
    }

    au_report_refresh_timer = setTimeout(() => {
        const filters = query_report.get_values() || {};
        if (!filters.site || !filters.start_date || !filters.end_date) {
            return;
        }

        // immediate refresh without user hard refresh
        query_report.refresh();
    }, 100);
}

function sync_end_date_if_blank(query_report) {
    const start_date = query_report.get_filter_value("start_date");
    const end_date = query_report.get_filter_value("end_date");

    if (start_date && !end_date) {
        query_report.set_filter_value("end_date", start_date);
    }
}

function render_timeline_legend(report) {
    if (!report || !report.page) {
        return;
    }

    const page = report.page;
    const wrapper =
        page.main && page.main.parent ? page.main.parent() : null;

    if (!wrapper || !wrapper.length) {
        return;
    }

    wrapper.find(".au-legend-wrapper").remove();

    const legend_html = `
        <div class="au-legend-wrapper">
            <div class="au-legend-item">
                <span class="au-legend-box au-legend-startup"></span>
                <span class="au-legend-text">YELL = startup color only</span>
            </div>
            <div class="au-legend-item">
                <span class="au-legend-box au-legend-fatigue"></span>
                <span class="au-legend-text">BLUE = fatigue color only</span>
            </div>
            <div class="au-legend-item">
                <span class="au-legend-box au-legend-breakdown"></span>
                <span class="au-legend-text">RED = B/D Detail button</span>
            </div>
            <div class="au-legend-item">
                <span class="au-legend-box au-legend-empty"></span>
                <span class="au-legend-text">WHITE = nothing captured</span>
            </div>
        </div>
    `;

    // place legend directly under filters/header area
    wrapper.find(".report-wrapper, .layout-main-section").first().before(legend_html);
}

function show_bd_popup(docname, slot_label) {
    if (!docname) {
        frappe.msgprint("Breakdown document not found.");
        return;
    }

    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Plant Breakdown or Maintenance",
            name: docname
        },
        freeze: true,
        callback: function (r) {
            const doc = r.message;
            if (!doc) {
                frappe.msgprint("Unable to load breakdown details.");
                return;
            }

            const status_badge = (doc.open_closed || "").toLowerCase() === "open"
                ? `<span style="display:inline-block;padding:2px 8px;border-radius:10px;background:#ffe5e5;color:#b30000;font-size:12px;">Open</span>`
                : `<span style="display:inline-block;padding:2px 8px;border-radius:10px;background:#e8f5e9;color:#1b5e20;font-size:12px;">Closed</span>`;

            const html = `
                <div style="font-size:13px;line-height:1.6;">
                    <div style="margin-bottom:10px;">
                        <strong>${frappe.utils.escape_html(doc.name || "")}</strong>
                    </div>

                    <div style="margin-bottom:12px;">
                        <span style="display:inline-block;padding:4px 10px;border-radius:12px;background:#f5f5f5;color:#333;font-size:12px;">
                            Hour Slot: ${frappe.utils.escape_html(slot_label || "")}
                        </span>
                    </div>

                    <table style="width:100%;border-collapse:collapse;">
                        <tr>
                            <td style="padding:4px 8px 4px 0;"><strong>Site</strong></td>
                            <td style="padding:4px 0;">${frappe.utils.escape_html(doc.location || "")}</td>
                        </tr>
                        <tr>
                            <td style="padding:4px 8px 4px 0;"><strong>Shift</strong></td>
                            <td style="padding:4px 0;">${frappe.utils.escape_html(doc.shift || "")}</td>
                        </tr>
                        <tr>
                            <td style="padding:4px 8px 4px 0;"><strong>Downtime Type</strong></td>
                            <td style="padding:4px 0;">${frappe.utils.escape_html(doc.downtime_type || "")}</td>
                        </tr>
                        <tr>
                            <td style="padding:4px 8px 4px 0;"><strong>Plant No.</strong></td>
                            <td style="padding:4px 0;">${frappe.utils.escape_html(doc.asset_name || "")}</td>
                        </tr>
                        <tr>
                            <td style="padding:4px 8px 4px 0;"><strong>Plant Model</strong></td>
                            <td style="padding:4px 0;">${frappe.utils.escape_html(doc.item_name || "")}</td>
                        </tr>
                        <tr>
                            <td style="padding:4px 8px 4px 0;"><strong>Plant Category</strong></td>
                            <td style="padding:4px 0;">${frappe.utils.escape_html(doc.asset_category || "")}</td>
                        </tr>
                        <tr>
                            <td style="padding:4px 8px 4px 0;"><strong>Start Time</strong></td>
                            <td style="padding:4px 0;">${frappe.utils.escape_html(doc.breakdown_start_datetime || "")}</td>
                        </tr>
                        <tr>
                            <td style="padding:4px 8px 4px 0;"><strong>Back in Production</strong></td>
                            <td style="padding:4px 0;">${frappe.utils.escape_html(doc.resolved_datetime || "")}</td>
                        </tr>
                        <tr>
                            <td style="padding:4px 8px 4px 0;"><strong>Hours Start</strong></td>
                            <td style="padding:4px 0;">${frappe.utils.escape_html(String(doc.hours_breakdown_starts || ""))}</td>
                        </tr>
                        <tr>
                            <td style="padding:4px 8px 4px 0;"><strong>Status</strong></td>
                            <td style="padding:4px 0;">${status_badge}</td>
                        </tr>
                    </table>

                    <div style="margin-top:12px;">
                        <strong>Breakdown / Maintenance Reason</strong>
                        <div style="margin-top:4px;padding:8px;border:1px solid #e0e0e0;border-radius:6px;min-height:48px;background:#fafafa;">
                            ${frappe.utils.escape_html(doc.breakdown_reason || "")}
                        </div>
                    </div>

                    <div style="margin-top:12px;">
                        <strong>Resolution Summary</strong>
                        <div style="margin-top:4px;padding:8px;border:1px solid #e0e0e0;border-radius:6px;min-height:48px;background:#fafafa;">
                            ${frappe.utils.escape_html(doc.resolution_summary || "")}
                        </div>
                    </div>
                </div>
            `;

            const dialog = new frappe.ui.Dialog({
                title: `B/D Detail${slot_label ? " - " + slot_label : ""}`,
                size: "large",
                fields: [
                    {
                        fieldtype: "HTML",
                        fieldname: "bd_html"
                    }
                ],
                primary_action_label: "Open Full Document",
                primary_action: function () {
                    frappe.set_route("Form", "Plant Breakdown or Maintenance", docname);
                    dialog.hide();
                }
            });

            dialog.fields_dict.bd_html.$wrapper.html(html);
            dialog.show();
        },
        error: function () {
            frappe.msgprint("Unable to load breakdown details.");
        }
    });
}

function inject_timeline_styles() {
    if (document.getElementById("au-timeline-styles")) {
        return;
    }

    const style = document.createElement("style");
    style.id = "au-timeline-styles";
    style.innerHTML = `
        .au-legend-wrapper {
            display: flex;
            flex-wrap: wrap;
            gap: 14px;
            align-items: center;
            margin: 8px 0 12px 0;
            padding: 8px 0 2px 0;
        }

        .au-legend-item {
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .au-legend-box {
            width: 18px;
            height: 18px;
            display: inline-block;
            border-radius: 2px;
            border: 1px solid #d1d8dd;
            box-sizing: border-box;
        }

        .au-legend-startup {
            background: #fff200;
            border-color: #d6cc00;
        }

        .au-legend-fatigue {
            background: #29a3e1;
            border-color: #1b82b7;
        }

        .au-legend-breakdown {
            background: #ff1a1a;
            border-color: #d00000;
        }

        .au-legend-empty {
            background: #ffffff;
            border-color: #d1d8dd;
        }

        .au-legend-text {
            font-size: 12px;
            color: #36414c;
        }

        .au-cell {
            width: 100%;
            min-height: 22px;
            height: 22px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
            border-radius: 2px;
        }

        .au-cell-empty {
            background: #ffffff;
        }

        .au-cell-startup {
            background: #fff200;
        }

        .au-cell-fatigue {
            background: #29a3e1;
        }

        .au-cell-breakdown {
            background: #ff1a1a;
            padding: 0;
        }

        .au-bd-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            height: 18px;
            min-width: 72px;
            padding: 0 8px;
            border: 0;
            border-radius: 2px;
            background: #ffffff;
            color: #111;
            font-size: 10px;
            line-height: 1;
            cursor: pointer;
            margin: auto;
        }

        .au-bd-btn:hover {
            background: #f4f4f4;
        }

        .dt-cell__content {
            overflow: visible !important;
        }
    `;
    document.head.appendChild(style);
}