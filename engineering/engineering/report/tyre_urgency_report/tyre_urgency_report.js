frappe.query_reports["Tyre Urgency Report"] = {
    filters: [
        {
            fieldname: "as_on_date",
            label: __("As On Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "site",
            label: __("Site"),
            fieldtype: "Link",
            options: "Location",
        },
        {
            fieldname: "fleet_number",
            label: __("ADT"),
            fieldtype: "Link",
            options: "Asset",
        },
        {
            fieldname: "tyre_make",
            label: __("Tyre Make"),
            fieldtype: "Data",
        },
        {
            fieldname: "urgency_band",
            label: __("Urgency Band"),
            fieldtype: "Select",
            options: "\nCritical\nWarning\nCheck\nGood\nNormal",
        },
        {
            fieldname: "include_mock",
            label: __("Include Mock Data"),
            fieldtype: "Check",
            default: 1,
        },
    ],
    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "urgency_band" && data) {
            const colours = {
                Critical: "red",
                Warning: "orange",
                Check: "yellow",
                Good: "green",
                Normal: "blue",
            };
            return `<span class="indicator-pill ${colours[data.urgency_band] || "gray"}">${value}</span>`;
        }

        return value;
    },
};
