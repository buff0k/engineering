frappe.query_reports["Weekly Availability Dashboard"] = {
    filters: [],

    onload: function (report) {
        const hide_table = () => {
            report.page.main
                .find('.datatable, .dt-scrollable, .dt-footer')
                .hide();
        };

        hide_table();
        setTimeout(hide_table, 50);
        setTimeout(hide_table, 250);
    },

refresh: function (report) {
    report.page.main
        .find('.datatable, .dt-scrollable, .dt-footer')
        .hide();

    setTimeout(() => {
        console.log("WAD DEBUG (window):", window.__WAD_DEBUG || "No debug payload found");
    }, 300);
}

};
