frappe.query_reports["Availability and Utilisation Engine"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end()
        },
        {
            fieldname: "locations",
            label: __("Location"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Location", txt);
            }
        },
        {
            fieldname: "assets",
            label: __("Asset"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Asset", txt);
            }
        },
        {
            fieldname: "companies",
            label: __("Company"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Company", txt);
            }
        },
        {
            fieldname: "free_hours",
            label: __("Free Hours"),
            fieldtype: "Float",
            default: 0
        },
        {
            fieldname: "production_machines_only",
            label: __("Production Machines Only"),
            fieldtype: "Check",
            default: 0
        }
    ],

    formatter: function(value, row, column, data, default_formatter) {
        const hour_fields = [
            "actual_hours",
            "planned_downtime",
            "required_hours",
            "work_hours",
            "pbm_elapsed_time",
            "pbm_startup_fatigue_time",
            "pbm_sunday_time",
            "pbm_total_downtime"
        ];

        const raw_value = data
            ? data[column.fieldname]
            : 0;

        value = default_formatter(
            value,
            row,
            column,
            data
        );

        if (hour_fields.includes(column.fieldname)) {
            value = format_engine_hours(raw_value);
        }

        return value;
    },

    onload: function() {
        setTimeout(
            apply_engine_styles,
            500
        );
    },

    after_datatable_render: function() {
        setTimeout(
            apply_engine_styles,
            200
        );
    }
};


function format_engine_hours(hours_value) {
    const total_minutes = Math.round(
        flt(hours_value || 0) * 60
    );

    const hours = Math.floor(
        total_minutes / 60
    );

    const minutes = total_minutes % 60;

    if (hours && minutes) {
        return `${hours}h ${minutes}m`;
    }

    if (hours) {
        return `${hours}h`;
    }

    return `${minutes}m`;
}


function apply_engine_styles() {
    const style_id = "availability-utilisation-engine-style";
    const old_style = document.getElementById(style_id);

    if (old_style) {
        old_style.remove();
    }

    const style = document.createElement("style");

    style.id = style_id;

    style.innerHTML = `
        .query-report[data-report-name="Availability and Utilisation Engine"]
        .dt-cell--header {
            background: #dcfce7 !important;
            color: #166534 !important;
            font-weight: 800 !important;
            border-bottom: 2px solid #16a34a !important;
        }
    `;

    document.head.appendChild(style);
}