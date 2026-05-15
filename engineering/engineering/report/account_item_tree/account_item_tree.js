frappe.query_reports["Account Item Tree"] = {
    tree: true,
    name_field: "account_item",
    initial_depth: 1,
    filters: [],

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        if (data.row_type === "account" && column.fieldname === "account_item") {
            return `<span style="font-weight: 800; background: #e5e7eb; padding: 4px 8px; border-radius: 6px;">${value}</span>`;
        }

        if (data.row_type === "account_code" && column.fieldname === "account_item") {
            return `<span style="font-weight: 700; color: #1f2937;">${value}</span>`;
        }

        if (data.row_type === "item_group" && column.fieldname === "account_item") {
            return `<span style="background: #eef2ff; color: #3730a3; padding: 3px 8px; border-radius: 999px; font-weight: 700;">${value}</span>`;
        }

        if (data.row_type === "item" && column.fieldname === "item_group" && data.item_group) {
            return `<span style="background: #f0fdf4; color: #166534; padding: 3px 8px; border-radius: 999px; font-weight: 600;">${data.item_group}</span>`;
        }

        return value;
    }
};