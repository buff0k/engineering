function open_oil_comment_popup(comment, condition) {
    const safe_comment = frappe.utils.escape_html(comment || "No comment available");

    let bg = "#f8fafc";
    let border = "#cbd5e1";
    let color = "#0f172a";

    if (condition === "Monitor") {
        bg = "#fef3c7";
        border = "#f59e0b";
        color = "#92400e";
    } else if (condition === "Requires Attention") {
        bg = "#fef3c7";
        border = "#f59e0b";
        color = "#92400e";
    } else if (condition === "Urgent") {
        bg = "#ffedd5";
        border = "#f97316";
        color = "#9a3412";
    } else if (condition === "Critical") {
        bg = "#fee2e2";
        border = "#dc2626";
        color = "#991b1b";
    } else if (condition === "Import Failed") {
        bg = "#f1f5f9";
        border = "#64748b";
        color = "#334155";
    } else if (condition === "Normal") {
        bg = "#dcfce7";
        border = "#22c55e";
        color = "#166534";
    }

    const dialog = new frappe.ui.Dialog({
        title: `Oil Sample Comment - ${condition || "Status"}`,
        size: "large",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "comment_html",
                options: `
                    <div style="
                        background:${bg};
                        border:2px solid ${border};
                        color:${color};
                        border-radius:14px;
                        padding:18px;
                        font-size:14px;
                        line-height:1.6;
                        font-weight:600;
                        white-space:pre-wrap;
                    ">${safe_comment}</div>
                `
            }
        ],
        primary_action_label: "Close",
        primary_action() {
            dialog.hide();
        }
    });

    dialog.show();
}




frappe.query_reports["Oil Sample"] = {
    onload(report) {

        $(report.page.wrapper)
            .off("click.oil_comment")
            .on("click.oil_comment", ".oil-comment-btn", function () {
                const comment = decodeURIComponent($(this).attr("data-comment") || "");
                const condition = decodeURIComponent($(this).attr("data-condition") || "");
                open_oil_comment_popup(comment, condition);
            });
    },

    after_refresh(report) {
        setTimeout(() => {
            const wrapper = $(report.page.wrapper);
            const summary = wrapper.find(".report-summary, .summary-section").first();

            if (!summary.length || wrapper.find("#oil-detailed-analysis-btn").length) return;

            summary.append(`
                <div style="width:100%;text-align:center;margin-top:18px;">
                    <button
                        id="oil-detailed-analysis-btn"
                        class="btn btn-primary"
                        style="
                            border-radius:999px;
                            font-weight:900;
                            padding:8px 22px;
                            box-shadow:0 4px 12px rgba(0,0,0,.12);
                        "
                    >
                        Detailed Analyses
                    </button>
                </div>
            `);

            wrapper.find("#oil-detailed-analysis-btn").on("click", () => {
                window.open("https://oilandwear.com/tribology/web/login.php", "_blank");
            });

            if (!wrapper.find("#oil-chart-legend-style").length) {
                wrapper.append(`
                    <style id="oil-chart-legend-style">
                        .chart-container .chart-legend,
                        .frappe-chart .chart-legend {
                            display: none !important;
                        }

                        #oil-custom-chart-legend {
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            gap: 14px;
                            flex-wrap: wrap;
                            margin: 6px auto 6px;
                            width: 100%;
                        }

                        .oil-legend-card {
                            min-width: 118px;
                            text-align: center;
                            padding: 6px 10px;
                            border-radius: 12px;
                            border: 1px solid rgba(15, 23, 42, 0.08);
                            background: #ffffff;
                            box-shadow: 0 1px 5px rgba(15, 23, 42, 0.05);
                        }

                        .oil-legend-label {
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            gap: 7px;
                            font-size: 13px;
                            font-weight: 800;
                            color: #1f2937;
                            white-space: nowrap;
                        }

                        .oil-legend-dot {
                            width: 11px;
                            height: 11px;
                            border-radius: 999px;
                            display: inline-block;
                        }

                        .oil-legend-value {
                            margin-top: 2px;
                            font-size: 13px;
                            font-weight: 900;
                            color: #111827;
                        }

                        .report-summary {
                            margin-bottom: 8px !important;
                        }

                        .chart-container,
                        .frappe-chart {
                            margin-top: 10px !important;
                            margin-bottom: 24px !important;
                            padding-bottom: 18px !important;
                        }

                        .chart-container svg,
                        .frappe-chart svg {
                            max-height: 165px !important;
                            overflow: visible !important;
                        }
                    </style>
                `);
            }

            wrapper.find("#oil-custom-chart-legend").remove();

            const chart_wrapper = wrapper.find(".chart-container, .frappe-chart").first();

            if (chart_wrapper.length) {
                chart_wrapper.before(`
                    <div id="oil-custom-chart-legend">
                        <div class="oil-legend-card">
                            <div class="oil-legend-label">
                                <span class="oil-legend-dot" style="background:#f59e0b;"></span>
                                Requires Attention
                            </div>
                            <div class="oil-legend-value">176</div>
                        </div>

                        <div class="oil-legend-card">
                            <div class="oil-legend-label">
                                <span class="oil-legend-dot" style="background:#64748b;"></span>
                                Import Failed
                            </div>
                            <div class="oil-legend-value">1</div>
                        </div>

                        <div class="oil-legend-card">
                            <div class="oil-legend-label">
                                <span class="oil-legend-dot" style="background:#f97316;"></span>
                                Urgent
                            </div>
                            <div class="oil-legend-value">61</div>
                        </div>

                        <div class="oil-legend-card">
                            <div class="oil-legend-label">
                                <span class="oil-legend-dot" style="background:#dc2626;"></span>
                                Critical
                            </div>
                            <div class="oil-legend-value">10</div>
                        </div>
                    </div>
                `);
            }
        }, 300);
    },

    filters: [
        {"fieldname": "from_date", "label": "From Date", "fieldtype": "Date"},
        {"fieldname": "to_date", "label": "To Date", "fieldtype": "Date"},
        {"fieldname": "location", "label": "Location", "fieldtype": "Link", "options": "Location"},
        {"fieldname": "plant_number", "label": "Plant Number", "fieldtype": "Link", "options": "Asset"},
        {"fieldname": "component", "label": "Component", "fieldtype": "Data"},
        {"fieldname": "condition", "label": "Condition", "fieldtype": "Select", "options": "\nNormal\nMonitor\nRequires Attention\nUrgent\nCritical\nImport Failed"},
        {"fieldname": "only_attention", "label": "Only Requires Attention / Urgent / Critical", "fieldtype": "Check"}
    ],

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        const fieldname = column.fieldname || column.id;

        if (fieldname === "comments") {
            const comment = data.comments || "";
            const short_text = comment.length > 35 ? comment.substring(0, 35) + "..." : comment;

            return `
                <div style="text-align:center;width:100%;">
                    <button
                        type="button"
                        class="btn btn-xs btn-primary oil-comment-btn"
                        data-comment="${encodeURIComponent(comment)}"
                        data-condition="${encodeURIComponent(data.condition || "")}"
                        style="border-radius:999px;font-weight:800;padding:3px 12px;"
                    >
                        Open
                    </button>
                </div>
            `;
        }

        if (fieldname !== "condition") return value;

        let bg = "#dcfce7", color = "#166534"; // Normal green

        if (data.condition === "Monitor") {
            bg = "#fef3c7"; color = "#92400e";
        } else if (data.condition === "Requires Attention") {
            bg = "#ffedd5"; color = "#c2410c";
        } else if (["Urgent", "Critical", "Import Failed"].includes(data.condition)) {
            bg = "#fee2e2"; color = "#991b1b";
        }

        return `<span style="background:${bg};color:${color};padding:4px 10px;border-radius:999px;font-weight:800;">${value}</span>`;
    }
};
