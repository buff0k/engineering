frappe.query_reports["Daily Availability and Utilisation Dashboard"] = {
    filters: [
        {
            fieldname: "start_date",
            label: __("Start Date"),
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "end_date",
            label: __("End Date"),
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "location",
            label: __("Site"),
            fieldtype: "Link",
            options: "Location",
            reqd: 1
        }
    ],

    onload(report) {
        const today = frappe.datetime.get_today();
        const yesterday = frappe.datetime.add_days(today, -1);

        if (!report.get_filter_value("start_date")) {
            report.set_filter_value("start_date", yesterday);
        }

        if (!report.get_filter_value("end_date")) {
            report.set_filter_value("end_date", yesterday);
        }

        inject_dashboard_table_hider();
    },

    refresh(report) {
        inject_dashboard_table_hider();
        hide_report_table(report);
    },

    after_datatable_render(report) {
        inject_dashboard_table_hider();
        hide_report_table(report);
    }
};

function inject_dashboard_table_hider() {
    if (document.getElementById("daily-availability-dashboard-table-hider")) {
        return;
    }

    const style = document.createElement("style");
    style.id = "daily-availability-dashboard-table-hider";
    style.innerHTML = `
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .datatable,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .dt-scrollable,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .dt-header,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .dt-cell,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .dt-row,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .dt-footer,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .dt-message,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .no-result {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            min-height: 0 !important;
            max-height: 0 !important;
            overflow: hidden !important;
            padding: 0 !important;
            margin: 0 !important;
            border: 0 !important;
        }

        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .result,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .result-container,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .report-wrapper {
            display: block !important;
            visibility: visible !important;
            height: auto !important;
            min-height: 0 !important;
            max-height: none !important;
            overflow: visible !important;
        }
    `;

    document.head.appendChild(style);
}

function hide_report_table(report) {
    const hide = () => {
        inject_dashboard_table_hider();

        const wrapper = report.page.wrapper;

        wrapper.attr("data-report-name", "Daily Availability and Utilisation Dashboard");
        wrapper.find(".query-report").attr("data-report-name", "Daily Availability and Utilisation Dashboard");

        wrapper.find(".datatable, .dt-scrollable, .dt-header, .dt-cell, .dt-row, .dt-footer, .dt-message, .no-result").attr("style", function(i, current) {
            return (current || "") + ";display:none!important;visibility:hidden!important;height:0!important;max-height:0!important;overflow:hidden!important;padding:0!important;margin:0!important;border:0!important;";
        });

        wrapper.find(".result, .result-container, .report-wrapper").attr("style", function(i, current) {
            return (current || "") + ";display:block!important;visibility:visible!important;height:auto!important;max-height:none!important;overflow:visible!important;";
        });
    };

    setTimeout(hide, 0);
    setTimeout(hide, 100);
    setTimeout(hide, 300);
    setTimeout(hide, 800);
    setTimeout(hide, 1500);
}
