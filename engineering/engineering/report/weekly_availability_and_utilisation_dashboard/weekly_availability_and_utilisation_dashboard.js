frappe.query_reports["Weekly Availability and Utilisation Dashboard"] = {
    filters: [
        {
            fieldname: "site_group",
            label: __("Complex"),
            fieldtype: "Select",
            options: ["", "All", "Seriti Sites", "Other"],
            default: "All",

        },

        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
        },
    ],

    onload(report) {
const today = frappe.datetime.get_today();
const yesterday = frappe.datetime.add_days(today, -1);

report.set_filter_value("to_date", yesterday);
report.set_filter_value(
    "from_date",
    frappe.datetime.add_days(yesterday, -6)
);

        hide_table(report);
    },

    refresh(report) {
        hide_table(report);
    },

    after_datatable_render(report) {
        hide_table(report);
    },
};


function hide_table(report) {
    const hide = () => {
        // hide datatable + report result containers (these include the footer/help text + scrollbar)
        report.page.wrapper.find(".result, .result-container, .report-wrapper, .report-footer").hide();
        report.page.main.find(".result, .result-container, .report-wrapper, .report-footer").hide();

        // extra safety: hide any lingering "help/execution time" text blocks
        report.page.wrapper.find(".dt-help, .dt-message, .dt-footer, .no-result").hide();
        report.page.main.find(".dt-help, .dt-message, .dt-footer, .no-result").hide();

        // remove the tiny scroll area if it remains
        report.page.wrapper.find(".result, .result-container, .report-wrapper").css({
            "max-height": "0",
            "overflow": "hidden",
            "padding": "0",
            "margin": "0"
        });
        report.page.main.find(".result, .result-container, .report-wrapper").css({
            "max-height": "0",
            "overflow": "hidden",
            "padding": "0",
            "margin": "0"
        });
    };

    setTimeout(hide, 0);
    setTimeout(hide, 200);
    setTimeout(hide, 800);
    setTimeout(hide, 1500);
}

