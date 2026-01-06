(function () {
    function inject_css_once() {
        if (document.getElementById("msr-report-css")) return;

        const style = document.createElement("style");
        style.id = "msr-report-css";
        style.type = "text/css";

        // These selectors cover most Frappe versions (old + new)
        style.textContent = `
            /* Allow borders to show fully (fix clipping at bottom) */
            .query-report .dt-row,
            .query-report .dt-row > .dt-cell,
            .query-report .dt-cell,
            .query-report .dt-cell__content,
            .query-report .dt-scrollable .dt-row,
            .query-report .dt-scrollable .dt-cell,
            .query-report .dt-scrollable .dt-cell__content {
                overflow: visible !important;
            }

            /* Give every cell a little breathing room so borders aren't cut */
            .query-report .dt-cell__content {
                padding-bottom: 4px !important;
            }

            /* Avoid too-tight row height when content is wrapped */
            .query-report .dt-row {
                height: auto !important;
            }
        `;

        document.head.appendChild(style);
    }

    function ensure_legend(report) {
        if (document.getElementById("msr-report-legend")) return;

        const legend = document.createElement("div");
        legend.id = "msr-report-legend";

        legend.style.margin = "12px 0 14px 0";
        legend.style.padding = "12px 14px";
        legend.style.border = "1px solid #ddd";
        legend.style.borderRadius = "10px";
        legend.style.background = "#fafafa";
        legend.style.display = "flex";
        legend.style.gap = "12px";
        legend.style.flexWrap = "wrap";
        legend.style.alignItems = "center";
        legend.style.fontSize = "14px";
        legend.style.lineHeight = "1.2";
        legend.style.width = "100%";
        legend.style.boxSizing = "border-box";

        legend.innerHTML = `
            <strong style="margin-right:6px;">Status Legend:</strong>

            <span style="background:#e8f5e9;border:1px solid #2e7d32;padding:8px 14px;border-radius:999px;white-space:nowrap;display:inline-flex;align-items:center;line-height:1.1;font-size:13px;">
                Service
            </span>

            <span style="background:#ffebee;border:1px solid #c62828;padding:8px 14px;border-radius:999px;white-space:nowrap;display:inline-flex;align-items:center;line-height:1.1;font-size:13px;">
                Breakdown
            </span>

            <span style="background:#fff3e0;border:1px solid #ef6c00;padding:8px 14px;border-radius:999px;white-space:nowrap;display:inline-flex;align-items:center;line-height:1.1;font-size:13px;min-width:170px;justify-content:center;">
                Planned Maintenance
            </span>

            <span style="background:#e3f2fd;border:1px solid #1565c0;padding:8px 14px;border-radius:999px;white-space:nowrap;display:inline-flex;align-items:center;line-height:1.1;font-size:13px;">
                Inspection
            </span>
        `;

        const main = report && report.page && report.page.main ? report.page.main : null;
        if (main && main.prepend) {
            main.prepend(legend);
            return;
        }

        const fallback =
            document.querySelector(".layout-main-section") ||
            document.querySelector(".page-content") ||
            document.querySelector(".page-body");

        if (fallback) fallback.prepend(legend);
    }

    function status_style(data) {
        const t = (data.service_breakdown || "").trim();

        if (t === "Service") return { bg: "#e8f5e9", border: "#2e7d32" };
        if (t === "Breakdown") return { bg: "#ffebee", border: "#c62828" };
        if (t === "Planned Maintenance") return { bg: "#fff3e0", border: "#ef6c00" };
        if (t === "Inspection") return { bg: "#e3f2fd", border: "#1565c0" };

        return null;
    }

    frappe.query_reports["MSR Report"] = {
        onload: function (report) {
            // Make sure CSS + legend are present
            inject_css_once();
            setTimeout(() => ensure_legend(report), 200);
        },

        refresh: function (report) {
            inject_css_once();
            setTimeout(() => ensure_legend(report), 200);
        },

        formatter: function (value, row, column, data, default_formatter) {
            value = default_formatter(value, row, column, data);
            if (!data) return value;

            const style = status_style(data);
            if (!style) return value;

            // Colour only MSR + Description columns
            const allowed = ["name", "description_of_breakdown"];
            if (column && !allowed.includes(column.fieldname)) return value;

            const is_description = column && column.fieldname === "description_of_breakdown";

            return `
                <div style="
                    background:${style.bg};
                    border:1px solid ${style.border};
                    border-radius:8px;

                    display:block;
                    width:100%;
                    box-sizing:border-box;

                    padding:7px 10px 9px 10px;
                    line-height:1.35;

                    ${is_description ? `
                        white-space:normal;
                        overflow-wrap:anywhere;
                        word-break:break-word;
                        min-height:56px;
                    ` : `
                        white-space:nowrap;
                    `}
                ">${value}</div>
            `;
        }
    };
})();
