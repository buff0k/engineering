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


    get_datatable_options: function(options) {
        return Object.assign(
            options,
            {
                freezeColumns: 8
            }
        );
    },



    formatter: function(value, row, column, data, default_formatter) {
        if (
            data
            && Number(
                data.is_formula_row || 0
            ) === 1
        ) {
            const formulas = {
                "shift_available_hours": (
                    "MIN(MAX(Work Hrs - PBM Downtime, 0), Req Hrs)"
                ),
                "available_hours_above_100": (
                    "MAX(Work Hrs, Shift Available)"
                ),
                "availability_percentage": (
                    "(Above 100 / Req Hrs) × 100 × A&U"
                ),
                "utilisation_percentage": (
                    "(Work Hrs / Shift Available) × 100 × A&U"
                )
            };

            const formula = formulas[
                column.fieldname
            ];

            if (!formula) {
                return "";
            }

            return `
                <div style="
                    display:block;
                    width:100%;
                    padding:4px 5px;
                    border:1px solid #60a5fa;
                    border-radius:4px;
                    background:#eff6ff;
                    color:#1d4ed8;
                    font-size:9px;
                    font-weight:700;
                    line-height:1.2;
                    text-align:center;
                    white-space:normal;
                    box-sizing:border-box;
                ">
                    ${frappe.utils.escape_html(formula)}
                </div>
            `;
        }

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
            data
            && Number(data.indent || 0) === 1
            && column.fieldname === "shift_date"
        ) {
            value = `
                <span class="availability-engine-date-label">
                    ${value}
                </span>
            `;
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
            && Number(data.indent || 0) === 3
            && (
                data.shift === "Day"
                || data.shift === "Night"
            )
        ) {
            value = apply_engine_shift_highlight(
                value,
                data.shift
            );
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

    onload: function(report) {

        setTimeout(
            apply_engine_freeze_columns,
            500
        );

        setTimeout(
            apply_engine_freeze_columns,
            1500
        );
    },

    after_datatable_render: function() {
        setTimeout(
            function() {
                apply_engine_freeze_columns();
                bind_shift_available_formula_header();
                bind_available_hours_formula_header();
                bind_engine_expanded_date_highlight();
            },
            200
        );
    }
};



function bind_shift_available_formula_header() {
    const headers = document.querySelectorAll(
        ".dt-cell--header"
    );

    headers.forEach(function(header) {
        const text = (
            header.innerText || ""
        ).trim();

        if (
            text !== "Shift Available Hours"
        ) {
            return;
        }

        if (
            header.dataset.shiftFormulaBound === "1"
        ) {
            return;
        }

        header.dataset.shiftFormulaBound = "1";
        header.style.cursor = "pointer";
        header.title = "Click to view formula";

        header.addEventListener(
            "click",
            show_shift_available_formula
        );
    });
}


function show_shift_available_formula() {
    const dialog = new frappe.ui.Dialog({
        title: __("Shift Available Hours"),
        size: "large",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "formula_html"
            }
        ]
    });

    dialog.fields_dict.formula_html.$wrapper.html(`
        <div style="
            padding: 6px 4px 12px;
            line-height: 1.6;
        ">
            <div style="
                background: #eff6ff;
                border: 1px solid #93c5fd;
                border-radius: 10px;
                padding: 16px;
                margin-bottom: 16px;
            ">
                <div style="
                    color: #1d4ed8;
                    font-size: 15px;
                    font-weight: 700;
                    margin-bottom: 8px;
                ">
                    Shift Available Hours Formula
                </div>

                <div style="
                    color: #1d4ed8;
                    font-size: 16px;
                    font-weight: 700;
                ">
                    MIN(
                        MAX(
                            Work Hours - PBM Total Downtime,
                            0
                        ),
                        Required Hours
                    )
                </div>
            </div>

            <div style="
                background: #f8fafc;
                border: 1px solid #d1d8dd;
                border-radius: 10px;
                padding: 16px;
                margin-bottom: 12px;
            ">
                <strong>1. Start with Work Hours</strong>

                <div style="margin-top: 6px;">
                    Use the Working Hours recorded for the
                    individual shift.
                </div>
            </div>

            <div style="
                background: #f8fafc;
                border: 1px solid #d1d8dd;
                border-radius: 10px;
                padding: 16px;
                margin-bottom: 12px;
            ">
                <strong>2. Subtract PBM Total Downtime</strong>

                <div style="margin-top: 6px;">
                    Subtract PBM Total Downtime from Work Hours.
                </div>
            </div>

            <div style="
                background: #f8fafc;
                border: 1px solid #d1d8dd;
                border-radius: 10px;
                padding: 16px;
            ">
                <strong>3. Apply the limits</strong>

                <ul style="
                    margin-top: 8px;
                    margin-bottom: 0;
                    padding-left: 22px;
                ">
                    <li>
                        If the result is below 0, use 0.
                    </li>

                    <li>
                        If the result is above Required Hours,
                        use Required Hours.
                    </li>
                </ul>

                <div style="
                    margin-top: 12px;
                    font-weight: 700;
                ">
                    Shift Available Hours can therefore never
                    be negative and can never exceed the
                    shift's Required Hours.
                </div>
            </div>
        </div>
    `);

    dialog.show();
}

function bind_available_hours_formula_header() {
    const headers = document.querySelectorAll(
        ".dt-cell--header"
    );


    headers.forEach(function(header) {
        const text = (
            header.innerText || ""
        ).trim();

        if (
            text !== "Available Hours Above 100"
        ) {
            return;
        }

        if (
            header.dataset.formulaBound === "1"
        ) {
            return;
        }

        header.dataset.formulaBound = "1";
        header.style.cursor = "pointer";
        header.title = "Click to view formula";

        header.addEventListener(
            "click",
            show_available_hours_above_100_formula
        );
    });
}


function show_available_hours_above_100_formula() {
    const dialog = new frappe.ui.Dialog({
        title: __("Available Hours Above 100"),
        size: "large",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "formula_html"
            }
        ]
    });

    dialog.fields_dict.formula_html.$wrapper.html(`
        <div style="
            padding: 6px 4px 12px;
            line-height: 1.6;
        ">
            <div style="
                background: #f8fafc;
                border: 1px solid #d1d8dd;
                border-radius: 10px;
                padding: 16px;
                margin-bottom: 16px;
            ">
                <div style="
                    font-size: 15px;
                    font-weight: 700;
                    margin-bottom: 8px;
                ">
                    1. Shift Available Hours
                </div>

                <div style="
                    font-size: 16px;
                    font-weight: 700;
                    margin-bottom: 8px;
                ">
                    MIN(
                        MAX(
                            Work Hours - PBM Total Downtime,
                            0
                        ),
                        Required Hours
                    )
                </div>

                <div>
                    Work Hours minus PBM Total Downtime is used,
                    with a minimum of 0 and a maximum of the
                    shift's Required Hours.
                </div>
            </div>

            <div style="
                background: #f8fafc;
                border: 1px solid #d1d8dd;
                border-radius: 10px;
                padding: 16px;
                margin-bottom: 16px;
            ">
                <div style="
                    font-size: 15px;
                    font-weight: 700;
                    margin-bottom: 8px;
                ">
                    2. Available Hours Above 100
                </div>

                <div style="
                    font-size: 16px;
                    font-weight: 700;
                    margin-bottom: 10px;
                ">
                    MAX(
                        Work Hours,
                        Shift Available Hours
                    )
                </div>

                <div style="margin-bottom: 8px;">
                    The higher of the two values is used.
                </div>

                <ul style="
                    margin-bottom: 0;
                    padding-left: 22px;
                ">
                    <li>
                        If Shift Available Hours is higher,
                        Shift Available Hours is used.
                    </li>
                    <li>
                        If Work Hours is higher,
                        Work Hours is used.
                    </li>
                </ul>
            </div>

            <div style="
                background: #f8fafc;
                border: 1px solid #d1d8dd;
                border-radius: 10px;
                padding: 16px;
            ">
                <div style="
                    font-size: 15px;
                    font-weight: 700;
                    margin-bottom: 8px;
                ">
                    3. Totals
                </div>

                <div>
                    Each shift is calculated separately first.
                    Machine, day, category and main totals are
                    then calculated by summing the individual
                    shift results.
                </div>
            </div>
        </div>
    `);

    dialog.show();
}

function apply_engine_shift_highlight(value, shift) {
    const background = (
        shift === "Day"
        ? "#eaf4ff"
        : "#f3f4f6"
    );

    return `
        <span
            class="availability-engine-shift-cell"
            style="
                display:block;
                min-height:100%;
                margin:-8px -10px;
                padding:8px 10px;
                background:${background} !important;
            "
        >
            ${value || ""}
        </span>
    `;
}


function bind_engine_expanded_date_highlight() {
    const report = document.querySelector(
        '.query-report[data-report-name="Availability and Utilisation Engine"]'
    );

    if (
        !report
        || report.dataset.expandedDateBound === "1"
    ) {
        return;
    }

    report.dataset.expandedDateBound = "1";

    report.addEventListener("click", function(event) {
        const toggle = event.target.closest(
            ".dt-cell__toggle, .dt-cell__tree-node, .dt-tree-node"
        );

        if (!toggle) {
            return;
        }

        const row = toggle.closest(".dt-row");

        if (!row) {
            return;
        }

        const date_label = row.querySelector(
            ".availability-engine-date-label"
        );

        if (!date_label) {
            return;
        }

        setTimeout(
            function() {
                date_label.classList.toggle(
                    "availability-engine-date-expanded"
                );
            },
            50
        );
    });
}




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





function apply_engine_freeze_columns() {
    if (
        !frappe.query_report
        || !frappe.query_report.datatable
    ) {
        return;
    }

    if (
        frappe.query_report.report_name
        !== "Availability and Utilisation Engine"
    ) {
        return;
    }

    frappe.query_report.datatable.options.freezeColumns = 8;

    apply_engine_styles();
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


        .dt-cell--col-0,
        .dt-cell--col-1,
        .dt-cell--col-2,
        .dt-cell--col-3,
        .dt-cell--col-4,
        .dt-cell--col-5,
        .dt-cell--col-6,
        .dt-cell--col-7 {
            position: sticky !important;
            background: #ffffff !important;
            z-index: 30 !important;
            box-shadow: 1px 0 0 #d1d8dd !important;
        }

        .dt-header .dt-cell--col-0,
        .dt-header .dt-cell--col-1,
        .dt-header .dt-cell--col-2,
        .dt-header .dt-cell--col-3,
        .dt-header .dt-cell--col-4,
        .dt-header .dt-cell--col-5,
        .dt-header .dt-cell--col-6,
        .dt-header .dt-cell--col-7,
        .dt-cell--header.dt-cell--col-0,
        .dt-cell--header.dt-cell--col-1,
        .dt-cell--header.dt-cell--col-2,
        .dt-cell--header.dt-cell--col-3,
        .dt-cell--header.dt-cell--col-4,
        .dt-cell--header.dt-cell--col-5,
        .dt-cell--header.dt-cell--col-6,
        .dt-cell--header.dt-cell--col-7 {
            position: sticky !important;
            background: #dcfce7 !important;
            z-index: 60 !important;
        }

        .dt-cell--col-0 {
            left: 0 !important;
        }

        .dt-cell--col-1 {
            left: 38px !important;
        }

        .dt-cell--col-2 {
            left: 168px !important;
        }

        .dt-cell--col-3 {
            left: 268px !important;
        }

        .dt-cell--col-4 {
            left: 383px !important;
        }

        .dt-cell--col-5 {
            left: 468px !important;
        }

        .dt-cell--col-6 {
            left: 603px !important;
        }

        .dt-cell--col-7 {
            left: 723px !important;
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

        .query-report[data-report-name="Availability and Utilisation Engine"]
        .availability-engine-date-label {
            font-weight: 600;
        }

        .query-report[data-report-name="Availability and Utilisation Engine"]
        .availability-engine-date-expanded {
            color: #15803d !important;
            font-weight: 800 !important;
        }
    `;

    document.head.appendChild(style);
}