window.account_item_tree_toggle_row = function (el) {
    const row = el.closest(".dt-row");
    if (!row) return;

    const toggle = row.querySelector(".dt-tree-node__toggle, .tree-node-button, .fa-caret-right, .fa-caret-down");
    if (toggle) {
        toggle.click();
    }
};



frappe.query_reports["Account Item Tree"] = {
    tree: true,
    name_field: "account_item",
    initial_depth: 0,
    filters: [],

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!data) return value;



        if (data.row_type === "company" && column.fieldname === "account_item") {
            return `<span onclick="window.account_item_tree_toggle_row(this)" style="
                display: inline-block;
                cursor: pointer;
                font-weight: 800;
                color: #1e3a8a;
                background: #dbeafe;
                border: 1px solid #93c5fd;
                border-left: 6px solid #2563eb;
                padding: 5px 13px;
                border-radius: 8px;
                min-width: 240px;
            ">${value}</span>`;
        }



        if (data.row_type === "account" && column.fieldname === "account_item") {
            return `<span onclick="window.account_item_tree_toggle_row(this)" style="
                display: inline-block;
                cursor: pointer;
                font-weight: 750;
                color: #14532d;
                background: #dcfce7;
                border: 1px solid #86efac;
                border-left: 5px solid #16a34a;
                padding: 4px 11px;
                border-radius: 7px;
                min-width: 260px;
            ">${value}</span>`;
        }

        if (data.row_type === "account_code" && column.fieldname === "account_item") {
            return `<span style="font-weight: 700; color: #1f2937;">${value}</span>`;
        }

        if (data.row_type === "item_group" && column.fieldname === "account_item") {
            return `<span onclick="window.account_item_tree_toggle_row(this)" style="
                display: inline-block;
                cursor: pointer;
                font-weight: 700;
                color: #111827;
                background: #f3f4f6;
                border: 1px solid #d1d5db;
                padding: 3px 10px;
                border-radius: 999px;
                min-width: 180px;
            ">${value}</span>`;
        }

        if (data.row_type === "item" && column.fieldname === "item_group" && data.item_group) {
            return `<span style="
                display: inline-block;
                font-weight: 600;
                color: #0369a1;
                background: #f0f9ff;
                border: 1px solid #bae6fd;
                padding: 3px 9px;
                border-radius: 999px;
            ">${data.item_group}</span>`;
        }


        if (data.row_type === "item" && column.fieldname === "account_item") {
            return `<span style="font-weight: 650; color: #111827;">${value}</span>`;
        }

        return value;
    }
};