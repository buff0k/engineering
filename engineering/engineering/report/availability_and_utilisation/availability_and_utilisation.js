// availability_and_utilisation.js

frappe.query_reports["Availability and Utilisation"] = {
    "filters": [
        {
            "fieldname": "start_date",
            "label": __("Start Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_start(),
            "reqd": 1
        },
        {
            "fieldname": "end_date",
            "label": __("End Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_end(),
            "reqd": 1
        },
        {
            "fieldname": "site",
            "label": __("Site"),
            "fieldtype": "Link",
            "options": "Location"
        },
        {
            "fieldname": "shift",
            "label": __("Shift"),
            "fieldtype": "Select",
            "options": "\nDay\nNight"
        }
    ]
};
