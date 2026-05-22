frappe.query_reports["Oil Sample"] = {
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
        if (!data || column.fieldname !== "condition") return value;

        let bg = "#dcfce7", color = "#166534"; // Normal green

        if (data.condition === "Monitor") {
            bg = "#fef3c7"; color = "#92400e"; // yellow
        } else if (data.condition === "Requires Attention") {
            bg = "#ffedd5"; color = "#c2410c"; // orange
        } else if (["Urgent", "Critical", "Import Failed"].includes(data.condition)) {
            bg = "#fee2e2"; color = "#991b1b"; // red
        }

        return `<span style="background:${bg};color:${color};padding:4px 10px;border-radius:999px;font-weight:800;">${value}</span>`;
    }
};
