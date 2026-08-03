frappe.pages["engineering-legals-monthly-summary-link"].on_page_load =
    function () {
        frappe.set_route(
            "query-report",
            "Engineering Legals Monthly Summary"
        );
    };

frappe.pages["engineering-legals-monthly-summary-link"].on_page_show =
    function () {
        frappe.set_route(
            "query-report",
            "Engineering Legals Monthly Summary"
        );
    };
