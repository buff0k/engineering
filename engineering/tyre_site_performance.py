frappe.query_reports["ADT Six Wheel Status"] = {
    filters: [
        {
            fieldname: "fleet_number",
            label: __("ADT"),
            fieldtype: "Link",
            options: "Asset",
            reqd: 1,
            get_query() {
                return { filters: { asset_category: "ADT" } };
            },
        },
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
