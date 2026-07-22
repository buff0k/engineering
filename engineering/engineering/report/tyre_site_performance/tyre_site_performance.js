frappe.query_reports["Tyre Site Performance"] = {
    filters: [
        {
            fieldname: "as_on_date",
            label: __("As On Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "include_mock",
            label: __("Include Mock Data"),
            fieldtype: "Check",
            default: 1,
        },
    ],
};
