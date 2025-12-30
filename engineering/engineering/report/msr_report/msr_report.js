// Copyright (c) 2025, BuFf0k and contributors
// For license information, please see license.txt

frappe.query_reports["MSR Report"] = {
    report_name: "MSR Report",
    ref_doctype: "Mechanical Service Report",
    report_type: "Query Report",
    reference_report: "",
    is_standard: "No",
    module: "Engineering",
    letter_head: "Isambane Mining",
    add_total_row: 0,
    disabled: 0,
    prepared_report: 0,
    add_translate_data: 0,
    timeout: 1500,

    filters: [
        {
            fieldname: "asset",
            label: "Fleet Number",
            fieldtype: "Link",
            options: "Asset",
            reqd: 1
        }
    ],

    columns: [
        {
            label: "MSR",
            fieldname: "name",
            fieldtype: "Link",
            options: "Mechanical Service Report",
            width: 180
        },
        {
            label: "Service Date",
            fieldname: "service_date",
            fieldtype: "Date",
            width: 120
        },
        {
            label: "Hours at Service",
            fieldname: "smr",
            fieldtype: "Data",
            width: 130
        },
        {
            label: "Description of Breakdown",
            fieldname: "description_of_breakdown",
            fieldtype: "Data",
            width: 300
        }
    ],

    roles: [
        { role: "System Manager" },
        { role: "Engineering Manager" },
        { role: "Engineering User" }
    ],

    onload: function(report) {
        console.log("MSR Report loaded:", report.report_type);

        if (report.report_type === "Custom Report") {
            setTimeout(() => {
                const el = document.querySelector(".page-head .title-text");
                if (el) {
                    el.style.color = "blue";
                    console.log("Title turned blue");
                } else {
                    console.log("Title element not found");
                }
            }, 500);
        }
    }
};