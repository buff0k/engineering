frappe.query_reports["Breakdown Status History"] = {
    "filters": [
        {
            "fieldname": "asset_name",
            "label": __("Asset Name"),
            "fieldtype": "Link",
            "options": "Asset"
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date"
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date"
        }
    ]
};
