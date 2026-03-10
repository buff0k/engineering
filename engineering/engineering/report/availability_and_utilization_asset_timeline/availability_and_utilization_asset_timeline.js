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
            fieldtype: "Data",
            on_change: function (query_report) {
                schedule_report_refresh(query_report);
            }
        }
    ],

    onload: function () {
        inject_timeline_styles();
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

        // Breakdown button with popup
        if (typeof raw === "string" && raw.startsWith("B::")) {
            const docname = raw.split("B::")[1] || "";
            const safe_docname = frappe.utils.escape_html(docname);

            return `
                <div class="au-cell au-cell-breakdown">
                    <button
                        class="au-bd-btn"
                        onclick="show_bd_popup('${safe_docname}')"
                    >
                        B/D Detail
                    </button>
                </div>
            `;
        }

        // Startup = yellow only, no text
        if (raw === "S") {
            return `<div class="au-cell au-cell-startup"></div>`;
        }

        // Fatigue = blue only, no text
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
        const filters = query_report.get_values();
        if (!filters.site || !filters.start_date || !filters.end_date) {
            return;
        }
        query_report.refresh();
    }, 200);
}

function sync_end_date_if_blank(query_report) {
    const start_date = query_report.get_filter_value("start_date");
    const end_date = query_report.get_filter_value("end_date");

    if (start_date && !end_date) {
        query_report.set_filter_value("end_date", start_date);
    }
}

function show_bd_popup(docname) {
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
                    <div style="margin-bottom:10px;"><strong>${frappe.utils.escape_html(doc.name || "")}</strong></div>

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
                title: "B/D Detail",
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
            background: transparent;
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