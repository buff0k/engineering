frappe.query_reports["Pre-Use Report"] = {
    filters: [
        {
            fieldname: "start_date",
            label: __("Start Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.add_days(frappe.datetime.get_today(), -7)
        },
        {
            fieldname: "end_date",
            label: __("End Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "site",
            label: __("Site"),
            fieldtype: "Link",
            options: "Location",
            reqd: 1
        },
        {
            fieldname: "shift",
            label: __("Shift"),
            fieldtype: "Select",
            options: ["", "Day", "Night", "Morning", "Afternoon"]
        }
    ],
    tree: true,
    name_field: "asset_name",
    parent_field: "asset_category",
    initial_depth: 1,

    onload: function(report) {
        // Add textbox top-right (shifted lower)
        if (!report.page.wrapper.find(".working-hours-rules-topright").length) {
            const rules_topright = `
                <div class="working-hours-rules-topright"
                     style="position:absolute; top:60px; right:20px; 
                            padding:8px; border:1px solid #ccc; border-radius:5px;
                            background:#f9f9f9; z-index:10; max-width:240px;">
                    <b>⚠️ Working Hours Rules:</b><br>
                    - Hours = 0 → <span style="color:orange;font-weight:bold;">Orange</span><br>
                    - Hours &lt; 0 → <span style="color:red;font-weight:bold;">Red</span><br>
                    - Hours &gt; 24 → <span style="color:red;font-weight:bold;">Red</span>
                </div>`;
            report.page.wrapper.prepend(rules_topright);
        }
    },

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "working_hours") {
            if (data.working_hours === 0) {
                value = `<span style="color:orange;font-weight:bold">${value}</span>`;
            } else if (data.working_hours < 0 || data.working_hours > 24) {
                value = `<span style="color:red;font-weight:bold">${value}</span>`;
            }
        }

        return value;
    }
};