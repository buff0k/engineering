frappe.query_reports["Availability and Utilisation Engine"] = {
    initial_depth: 0,

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
        },
        {
            fieldname: "au_percentage_basis",
            label: __("A & U Percentage"),
            fieldtype: "Select",
            options: [
                "85% A & U",
                "100% A & U"
            ].join("\n"),
            default: "85% A & U",
            reqd: 1
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
            "pbm_total_downtime",
            "shift_available_hours",
            "available_hours_above_100"
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

        if (
            [
                "availability_percentage",
                "utilisation_percentage"
            ].includes(column.fieldname)
            && (
                raw_value === null
                || raw_value === undefined
                || raw_value === ""
            )
        ) {
            value = "N/A";
        }

        if (
            data
            && Number(
                data.is_spare_swing_unit || 0
            ) === 1
        ) {
            value = apply_engine_spare_highlight(
                value,
                data.spare_swing_reason
            );
        }

        if (
            data
            && column.fieldname === "invalid_pre_use_status"
            && data.invalid_pre_use_status
        ) {
            const invalid = String(
                data.invalid_pre_use_status
            ).startsWith("Invalid");

            const contains_invalid = (
                data.invalid_pre_use_status
                === "Contains Invalid Shift"
            );

            if (invalid || contains_invalid) {
                value = `
                    <span style="
                        display:inline-block;
                        padding:3px 8px;
                        border-radius:999px;
                        background:#fee2e2;
                        color:#991b1b;
                        font-weight:700;
                    ">
                        ${frappe.utils.escape_html(
                            data.invalid_pre_use_status
                        )}
                    </span>
                `;
            }
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

function apply_engine_spare_highlight(value, reason) {
    const safe_reason = frappe.utils.escape_html(
        reason
        || "Spare/Swing unit in Monthly Production Planning"
    );

    return `
        <span
            class="availability-engine-spare-cell"
            title="${safe_reason}"
            style="
                display:block;
                min-height:100%;
                margin:-8px -10px;
                padding:8px 10px;
                background:#e6d6ff !important;
                color:#4b0082 !important;
                font-weight:600 !important;
                border-left:3px solid #7b2cbf !important;
            "
        >
            ${value || ""}
        </span>
    `;
}

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

        .query-report[data-report-name="Availability and Utilisation Engine"]
        .availability-engine-spare-cell {
            display: block;
            min-height: 100%;
            margin: -8px -10px;
            padding: 8px 10px;
            background: #e6d6ff !important;
            color: #4b0082 !important;
            font-weight: 600 !important;
            border-left: 3px solid #7b2cbf !important;
        }

        .query-report[data-report-name="Availability and Utilisation Engine"]
        .dt-cell__tree-node,
        .query-report[data-report-name="Availability and Utilisation Engine"]
        .dt-tree-node,
        .query-report[data-report-name="Availability and Utilisation Engine"]
        .dt-cell__toggle {
            position: relative !important;
            z-index: 20 !important;
            color: #111111 !important;
            opacity: 1 !important;
            visibility: visible !important;
        }
    `;

    document.head.appendChild(style);
}