// Copyright (c) 2026, BuFf0k and contributors
// For license information, please see license.txt


frappe.query_reports["Weekly Availability and Utilisation Dashboard"] = {
  filters: [
    {
      fieldname: "site_group",
      label: __("Complex"),
      fieldtype: "Select",
      options: ["", "All", "Seriti Sites", "Other"],
      default: "All"
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.add_days(frappe.datetime.get_today(), -7)
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.add_days(frappe.datetime.get_today(), -1)
    }
  ]
};