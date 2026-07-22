frappe.query_reports["Tyre Replacement Forecast"] = {
    filters: [
        {
            fieldname: "anchor_date",
            label: __("Planning Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        },
        {
            fieldname: "months",
            label: __("Months to Forecast"),
            fieldtype: "Int",
            default: 5,
            reqd: 1,
        },
        {
            fieldname: "site",
            label: __("Site"),
            fieldtype: "Link",
            options: "Location",
        },
        {
            fieldname: "include_mock",
            label: __("Include Mock Data"),
            fieldtype: "Check",
            default: 1,
        },
    ],
};
