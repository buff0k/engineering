// Copyright (c) 2025, BuFf0k and contributors
// For license information, please see license.txt

frappe.query_reports["MSR Report"] = {
    "filters": [
        {
            fieldname: "asset",
            label: "Fleet Number",
            fieldtype: "Link",
            options: "Asset",
            reqd: 1
        }
    ]
};
