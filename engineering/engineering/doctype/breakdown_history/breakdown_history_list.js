frappe.listview_settings["Breakdown History"] = {
    hide_name_filter: true,

    onload(listview) {
        const wrapper = listview.filter_area.standard_filters_wrapper;

        const refresh_list = function () {
            listview.start = 0;
            listview.refresh();

            if (typeof listview.on_filter_change === "function") {
                listview.on_filter_change();
            }
        };

        // =========================================================
        // SITE
        // Filters Breakdown History.location
        // =========================================================
        listview.page.add_field(
            {
                doctype: "Breakdown History",
                fieldname: "location",
                label: __("Site"),
                fieldtype: "Link",
                options: "Location",
                onchange: refresh_list,
            },
            wrapper
        );

        // =========================================================
        // ASSET NAME
        // Filters Breakdown History.asset_name
        // =========================================================
        listview.page.add_field(
            {
                doctype: "Breakdown History",
                fieldname: "asset_name",
                label: __("Asset Name"),
                fieldtype: "Link",
                options: "Asset",
                onchange: refresh_list,
            },
            wrapper
        );

        // =========================================================
        // FROM DATE
        // update_date_time >= selected date 00:00
        // =========================================================
        const from_date = listview.page.add_field(
            {
                doctype: "Breakdown History",
                fieldname: "breakdown_history_from_date",
                label: __("From Date"),
                fieldtype: "Date",
                condition: ">=",
                onchange: refresh_list,
            },
            wrapper
        );

        // Keep a unique toolbar field name but point the filter
        // to the actual Breakdown History database field.
        from_date.df.fieldname = "update_date_time";
        from_date.df.condition = ">=";

        // =========================================================
        // TO DATE
        // Use < next day so the entire selected To Date is included.
        //
        // Example:
        // To Date = 09-09-2026
        // query becomes update_date_time < 10-09-2026 00:00
        // =========================================================
        const to_date = listview.page.add_field(
            {
                doctype: "Breakdown History",
                fieldname: "breakdown_history_to_date",
                label: __("To Date"),
                fieldtype: "Date",
                condition: "<",
                onchange: refresh_list,
            },
            wrapper
        );

        to_date.df.fieldname = "update_date_time";
        to_date.df.condition = "<";

        // Convert To Date to the next day so records throughout
        // the selected date are included, not only midnight.
        const original_to_date_get_value = to_date.get_value.bind(to_date);

        to_date.get_value = function () {
            const value = original_to_date_get_value();

            if (!value) {
                return value;
            }

            return frappe.datetime.add_days(value, 1);
        };
    },
};
