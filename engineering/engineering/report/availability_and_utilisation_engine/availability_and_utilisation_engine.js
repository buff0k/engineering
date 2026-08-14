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


        const hour_fields = [
            "actual_hours",
            "planned_downtime",
            "required_hours",
            "work_hours",
            "pbm_elapsed_time",
            "pbm_startup_fatigue_time",
            "pbm_sunday_time",
            "pbm_total_downtime",
            "utilisation_available_hours",
            "availability_available_hours"
            // OLD UTILISATION SUPPORT FIELDS
            // "utilisation_work_hours",
            // "utilisation_available_hours"
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

            if (
                data
                && column.fieldname === "utilisation_percentage"
                && data.au_validation_level === "invalid"
            ) {
                value = `
                    <span style="
                        display:inline-block;
                        padding:3px 8px;
                        border-radius:999px;
                        background:#fee2e2;
                        color:#991b1b;
                        font-weight:700;
                    ">
                        N/A
                    </span>
                `;
            }
        }

        if (
            data
            && Number(data.indent || 0) === 0
            && column.fieldname === "asset_category"
            && Number(
                data.au_problem_day_count || 0
            ) > 0
        ) {
            const problem_day_count = Number(
                data.au_problem_day_count || 0
            );

            value = `
                ${value}
                <span
                    title="${problem_day_count} day(s) contain A&U warnings or invalid shifts"
                    style="
                        display:inline-flex;
                        align-items:center;
                        justify-content:center;
                        min-width:18px;
                        height:18px;
                        margin-left:6px;
                        padding:0 5px;
                        border-radius:9px;
                        background:#f97316;
                        color:#ffffff;
                        font-size:10px;
                        font-weight:700;
                        line-height:18px;
                    "
                >
                    ${problem_day_count}
                </span>
            `;
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

        if (
            data
            && [1, 2, 3].includes(
                Number(data.indent || 0)
            )
            && (
                data.au_validation_level === "invalid"
                || data.au_validation_level === "warning"
            )
        ) {
            const is_invalid = (
                data.au_validation_level === "invalid"
            );

            const background = (
                is_invalid
                ? "#fee2e2"
                : "#ffedd5"
            );

            const border = (
                is_invalid
                ? "#dc2626"
                : "#f97316"
            );

            const safe_status = (
                frappe.utils.escape_html(
                    data.au_validation_status || ""
                )
            );

            value = `
                <span
                    title="${safe_status}"
                    style="
                        display:block;
                        min-height:100%;
                        margin:-8px -10px;
                        padding:8px 10px;
                        background:${background} !important;
                        border-left:3px solid ${border} !important;
                    "
                >
                    ${value || ""}
                </span>
            `;
        }

        return value;
    },

    onload: function(report) {
        bind_engine_formula_header_clicks(report);
        add_engine_legend(report);

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
                mark_engine_formula_headers_clickable();
                bind_engine_expanded_date_highlight();
                update_invalid_au_button(
                    frappe.query_report
                );
            },
            200
        );
    }
};


function add_engine_legend(report) {
    const $wrapper = $(report.page.wrapper);

    if (
        $wrapper.find(
            ".availability-engine-legend"
        ).length
    ) {
        return;
    }

    const legend = `
        <div
            class="availability-engine-legend"
            style="
                display:flex;
                align-items:center;
                gap:14px;
                flex-wrap:wrap;
                margin:6px 0 8px;
                font-size:11px;
                font-weight:600;
            "
        >
            <span
                class="availability-engine-warning-legend"
                title="Click to view warning rules"
                style="
                    display:inline-flex;
                    align-items:center;
                    gap:5px;
                    cursor:pointer;
                "
            >
                <span style="
                    width:12px;
                    height:12px;
                    border-radius:3px;
                    background:#ffedd5;
                    border-left:3px solid #f97316;
                "></span>
                A&amp;U Warning
            </span>

            <span
                class="availability-engine-invalid-legend"
                title="Click to view invalid rules"
                style="
                    display:inline-flex;
                    align-items:center;
                    gap:5px;
                    cursor:pointer;
                "
            >
                <span style="
                    width:12px;
                    height:12px;
                    border-radius:3px;
                    background:#fee2e2;
                    border-left:3px solid #dc2626;
                "></span>
                Invalid A&amp;U
            </span>

            <button
                type="button"
                class="
                    btn
                    btn-xs
                    btn-default
                    availability-engine-invalid-view
                "
                style="
                    border:1px solid #dc2626;
                    color:#991b1b;
                    background:#fff;
                    font-size:11px;
                    font-weight:700;
                    padding:3px 9px;
                    border-radius:6px;
                "
            >
                View Invalid A&amp;U (0)
            </button>

            <span style="
                display:inline-flex;
                align-items:center;
                gap:5px;
            ">
                <span style="
                    width:12px;
                    height:12px;
                    border-radius:3px;
                    background:#e6d6ff;
                    border-left:3px solid #7b2cbf;
                "></span>
                Spare / Swing Machine
            </span>
        </div>
    `;

    const $filter_area = $wrapper.find(
        ".page-form"
    ).first();

    if ($filter_area.length) {
        $filter_area.append(legend);
    } else {
        $wrapper.prepend(legend);
    }

    $wrapper
        .find(".availability-engine-warning-legend")
        .off("click.auWarningLegend")
        .on(
            "click.auWarningLegend",
            show_au_warning_explanation
        );

    $wrapper
        .find(".availability-engine-invalid-legend")
        .off("click.auInvalidLegend")
        .on(
            "click.auInvalidLegend",
            show_au_invalid_explanation
        );

    $wrapper
        .find(".availability-engine-invalid-view")
        .off("click.auInvalidView")
        .on(
            "click.auInvalidView",
            function() {
                show_invalid_au_rows(
                    report
                );
            }
        );

    update_invalid_au_button(
        report
    );
}


function get_invalid_au_shift_rows(report) {
    let rows = [];

    if (
        report
        && Array.isArray(report.data)
    ) {
        rows = report.data;
    } else if (
        frappe.query_report
        && Array.isArray(
            frappe.query_report.data
        )
    ) {
        rows = frappe.query_report.data;
    }

    return rows
        .filter(
            function(row) {
                return (
                    row
                    && Number(
                        row.indent || 0
                    ) === 3
                    && (
                        row.shift === "Day"
                        || row.shift === "Night"
                    )
                    && (
                        row.au_validation_level
                        === "invalid"
                        || Number(
                            row.invalid_au || 0
                        ) === 1
                    )
                );
            }
        )
        .sort(
            function(a, b) {
                const date_compare = String(
                    a.shift_date || ""
                ).localeCompare(
                    String(
                        b.shift_date || ""
                    )
                );

                if (date_compare !== 0) {
                    return date_compare;
                }

                const machine_compare = String(
                    a.asset_name || ""
                ).localeCompare(
                    String(
                        b.asset_name || ""
                    )
                );

                if (machine_compare !== 0) {
                    return machine_compare;
                }

                return String(
                    a.shift || ""
                ).localeCompare(
                    String(
                        b.shift || ""
                    )
                );
            }
        );
}


function update_invalid_au_button(report) {
    if (
        !report
        || !report.page
        || !report.page.wrapper
    ) {
        return;
    }

    const rows = get_invalid_au_shift_rows(
        report
    );

    const $button = $(
        report.page.wrapper
    ).find(
        ".availability-engine-invalid-view"
    );

    if (!$button.length) {
        return;
    }

    $button.text(
        `View Invalid A&U (${rows.length})`
    );

    $button.prop(
        "disabled",
        rows.length === 0
    );

    $button.css(
        "opacity",
        rows.length === 0
            ? "0.55"
            : "1"
    );

    $button.attr(
        "title",
        rows.length
            ? (
                `${rows.length} invalid A&U `
                + "shift(s) in the current report"
            )
            : "No invalid A&U shifts in the current report"
    );
}


function format_invalid_au_date(value) {
    const text = String(
        value || ""
    ).slice(
        0,
        10
    );

    const match = text.match(
        /^(\d{4})-(\d{2})-(\d{2})$/
    );

    if (!match) {
        return text;
    }

    return (
        `${match[3]}/${match[2]}/${match[1]}`
    );
}


function get_invalid_au_reason(row) {
    return String(
        row.au_validation_status || ""
    )
        .replace(
            /^Invalid A&U:\s*/,
            ""
        )
        .trim();
}


function show_invalid_au_rows(report) {
    const rows = get_invalid_au_shift_rows(
        report
    );

    if (!rows.length) {
        frappe.msgprint({
            title: __("Invalid A&U"),
            message: __(
                "There are no invalid A&U shifts "
                + "in the current report."
            ),
            indicator: "green"
        });

        return;
    }

    const body_rows = rows
        .map(
            function(row) {
                const date = (
                    frappe.utils.escape_html(
                        format_invalid_au_date(
                            row.shift_date
                        )
                    )
                );

                const shift = (
                    frappe.utils.escape_html(
                        String(
                            row.shift || ""
                        )
                    )
                );

                const machine = (
                    frappe.utils.escape_html(
                        String(
                            row.asset_name || ""
                        )
                    )
                );

                const work_hours = (
                    frappe.utils.escape_html(
                        format_engine_hours(
                            row.work_hours
                        )
                    )
                );

                const pbm_hours = (
                    frappe.utils.escape_html(
                        format_engine_hours(
                            row.pbm_total_downtime
                        )
                    )
                );

                const required_hours = (
                    frappe.utils.escape_html(
                        format_engine_hours(
                            row.required_hours
                        )
                    )
                );

                const reason = (
                    frappe.utils.escape_html(
                        get_invalid_au_reason(
                            row
                        )
                    )
                );

                return `
                    <tr>
                        <td>${date}</td>
                        <td>${shift}</td>
                        <td>
                            <strong>
                                ${machine}
                            </strong>
                        </td>
                        <td>${work_hours}</td>
                        <td>${pbm_hours}</td>
                        <td>${required_hours}</td>
                        <td
                            style="
                                color:#991b1b;
                                min-width:280px;
                            "
                        >
                            ${reason}
                        </td>
                    </tr>
                `;
            }
        )
        .join("");

    const dialog = new frappe.ui.Dialog({
        title: __(
            `Invalid A&U Shifts (${rows.length})`
        ),
        size: "extra-large",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "invalid_rows_html"
            }
        ]
    });

    dialog
        .fields_dict
        .invalid_rows_html
        .$wrapper
        .html(`
            <div style="
                padding:4px 2px 12px;
            ">
                <div style="
                    display:flex;
                    align-items:center;
                    justify-content:space-between;
                    gap:12px;
                    flex-wrap:wrap;
                    margin-bottom:12px;
                    padding:12px 14px;
                    background:#fee2e2;
                    border:1px solid #dc2626;
                    border-radius:8px;
                ">
                    <div>
                        <strong style="
                            color:#991b1b;
                            font-size:14px;
                        ">
                            ${rows.length}
                            invalid A&amp;U shift(s)
                        </strong>

                        <div style="
                            margin-top:3px;
                            color:#7f1d1d;
                            font-size:12px;
                        ">
                            Current report filters only
                        </div>
                    </div>

                    <div style="
                        color:#7f1d1d;
                        font-size:12px;
                    ">
                        Invalid shifts are excluded from
                        A&amp;U KPI totals.
                    </div>
                </div>

                <div style="
                    max-height:60vh;
                    overflow:auto;
                    border:1px solid #d1d8dd;
                    border-radius:8px;
                ">
                    <table
                        class="table table-bordered"
                        style="
                            margin:0;
                            width:100%;
                            font-size:12px;
                            background:#fff;
                        "
                    >
                        <thead>
                            <tr style="
                                background:#f8fafc;
                            ">
                                <th
                                    style="
                                        position:sticky;
                                        top:0;
                                        background:#f8fafc;
                                        z-index:1;
                                    "
                                >
                                    Date
                                </th>
                                <th
                                    style="
                                        position:sticky;
                                        top:0;
                                        background:#f8fafc;
                                        z-index:1;
                                    "
                                >
                                    Shift
                                </th>
                                <th
                                    style="
                                        position:sticky;
                                        top:0;
                                        background:#f8fafc;
                                        z-index:1;
                                    "
                                >
                                    Machine
                                </th>
                                <th
                                    style="
                                        position:sticky;
                                        top:0;
                                        background:#f8fafc;
                                        z-index:1;
                                    "
                                >
                                    Work Hours
                                </th>
                                <th
                                    style="
                                        position:sticky;
                                        top:0;
                                        background:#f8fafc;
                                        z-index:1;
                                    "
                                >
                                    PBM Total Downtime
                                </th>
                                <th
                                    style="
                                        position:sticky;
                                        top:0;
                                        background:#f8fafc;
                                        z-index:1;
                                    "
                                >
                                    Required Hours
                                </th>
                                <th
                                    style="
                                        position:sticky;
                                        top:0;
                                        background:#f8fafc;
                                        z-index:1;
                                    "
                                >
                                    Invalid Reason
                                </th>
                            </tr>
                        </thead>

                        <tbody>
                            ${body_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        `);

    dialog.show();
}


function show_au_warning_explanation() {
    const dialog = new frappe.ui.Dialog({
        title: __("A&U Warning"),
        size: "large",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "warning_html"
            }
        ]
    });

    dialog.fields_dict.warning_html.$wrapper.html(`
        <div style="
            padding:6px 4px 12px;
            line-height:1.6;
        ">
            <div style="
                background:#ffedd5;
                border:1px solid #f97316;
                border-radius:10px;
                padding:16px;
                margin-bottom:14px;
            ">
                <strong style="
                    color:#9a3412;
                    font-size:15px;
                ">
                    What does an A&amp;U Warning mean?
                </strong>

                <div style="margin-top:8px;">
                    The record is mathematically possible, but the
                    underlying hours are unusual and should be reviewed.
                </div>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>Warning rules</strong>

                <ul style="
                    margin-top:8px;
                    margin-bottom:0;
                    padding-left:22px;
                ">
                    <!-- OLD UTILISATION AVAILABLE HOURS WARNING
                    <li>
                        Work Hours &gt; 0 while Utilisation Available Hours = 0.
                    </li>
                    -->
                    <li>
                        Required Hours = 0 while the machine still recorded Work Hours.
                    </li>
                    <li>
                        Utilisation is greater than 150%.
                    </li>
                </ul>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
            ">
                <strong>Important</strong>

                <div style="margin-top:8px;">
                    Warning rows are still included in the A&amp;U totals.
                    Orange does not automatically mean the data is wrong.
                </div>
            </div>
        </div>
    `);

    dialog.show();
}


function show_au_invalid_explanation() {
    const dialog = new frappe.ui.Dialog({
        title: __("Invalid A&U"),
        size: "large",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "invalid_html"
            }
        ]
    });

    dialog.fields_dict.invalid_html.$wrapper.html(`
        <div style="
            padding:6px 4px 12px;
            line-height:1.6;
        ">
            <div style="
                background:#fee2e2;
                border:1px solid #dc2626;
                border-radius:10px;
                padding:16px;
                margin-bottom:14px;
            ">
                <strong style="
                    color:#991b1b;
                    font-size:15px;
                ">
                    What does Invalid A&amp;U mean?
                </strong>

                <div style="margin-top:8px;">
                    The individual shift contains a physically impossible
                    or invalid combination of hours.
                </div>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>Invalid rules</strong>

                <ul style="
                    margin-top:8px;
                    margin-bottom:0;
                    padding-left:22px;
                ">
                    <li>
                        Work Hours exceed the physical shift length.
                    </li>
                    <li>
                        PBM Total Downtime exceeds the physical shift length.
                    </li>
                    <li>
                        Work Hours + PBM Total Downtime exceed the physical shift length.
                    </li>
                    <li>
                        Required Hours exceed the physical shift length.
                    </li>
                    <!-- OLD UTILISATION AVAILABLE HOURS VALIDATION
                    <li>
                        Utilisation Available Hours exceed the physical shift length.
                    </li>
                    -->
                </ul>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>Example</strong>

                <div style="margin-top:8px;">
                    12-hour shift<br>
                    Work Hours = 8<br>
                    PBM Total Downtime = 5<br><br>

                    Work + PBM = 13 hours.<br>
                    This cannot physically fit inside a 12-hour shift,
                    so the shift is flagged red.
                </div>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
            ">
                <strong>Important</strong>

                <div style="margin-top:8px;">
                    The 12-hour or 8-hour validation limit applies to
                    individual shifts only.

                    Date, machine and category rows may naturally total
                    more than one shift.

                    Invalid shift rows are excluded from A&amp;U totals.
                </div>
            </div>
        </div>
    `);

    dialog.show();
}


function bind_engine_formula_header_clicks(report) {
    const $wrapper = $(report.page.wrapper);

    $wrapper.off(
        "click.availabilityFormulaHeaders",
        ".dt-cell--header"
    );

    $wrapper.on(
        "click.availabilityFormulaHeaders",
        ".dt-cell--header",
        function(event) {
            const text = (
                $(this)
                    .find(".dt-cell__content")
                    .clone()
                    .children()
                    .remove()
                    .end()
                    .text()
                    || ""
            )
                .replace(/\s+/g, " ")
                .trim();

            if (text === "Utilisation Available Hours") {
                event.preventDefault();
                event.stopPropagation();
                show_shift_available_formula();
                return;
            }

            if (text === "Availability Available Hours") {
                event.preventDefault();
                event.stopPropagation();
                show_availability_available_hours_formula();
                return;
            }

            if (text === "Utilisation %") {
                event.preventDefault();
                event.stopPropagation();
                show_utilisation_formula();
            }
        }
    );
}


function mark_engine_formula_headers_clickable() {
    const formulas = {
        "Utilisation Available Hours": (
            "MAX(Req - PBM, MIN(Work, Req))"
        ),
        "Availability Available Hours": (
            "MAX(Work, MAX(Req - PBM, 0))"
        ),
        "Availability %": (
            "(Availability Available Hours / Req Hrs) × 100 × A&U"
        ),
        "Utilisation %": (
            "(Work Hrs / Utilisation Available Hours) × 100 × A&U"
        )
    };

    const clickable_headers = [
        "Utilisation Available Hours",
        "Availability Available Hours",
        "Utilisation %"
    ];

    const filter_row = document.querySelector(
        ".dt-row-filter"
    );

    if (!filter_row) {
        return;
    }

    document.querySelectorAll(
        ".dt-cell--header"
    ).forEach(function(header) {
        const content = header.querySelector(
            ".dt-cell__content"
        );

        if (!content) {
            return;
        }

        const text = (
            content.innerText || ""
        )
            .replace(/\s+/g, " ")
            .trim();

        const formula = formulas[text];

        if (!formula) {
            return;
        }

        const column_class = Array.from(
            header.classList
        ).find(function(class_name) {
            return class_name.startsWith(
                "dt-cell--col-"
            );
        });

        if (!column_class) {
            return;
        }

        const filter_cell = filter_row.querySelector(
            `.${column_class}`
        );

        if (
            !filter_cell
            || filter_cell.querySelector(
                ".availability-engine-header-formula"
            )
        ) {
            return;
        }

        const filter_content = filter_cell.querySelector(
            ".dt-cell__content"
        );

        if (!filter_content) {
            return;
        }

        filter_content.innerHTML = "";

        const formula_element = document.createElement(
            "div"
        );

        formula_element.className = (
            "availability-engine-header-formula"
        );

        formula_element.textContent = formula;

        filter_content.prepend(formula_element);

        if (clickable_headers.includes(text)) {
            header.style.cursor = "pointer";
            header.title = "Click to view formula";
        }
    });
}




function bind_shift_available_formula_header() {
    const headers = document.querySelectorAll(
        ".dt-cell--header"
    );

    headers.forEach(function(header) {
        const text = (
            header.innerText || ""
        ).trim();

        if (
            text !== "Utilisation Available Hours"
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
        title: __("Utilisation Available Hours"),
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
            padding:6px 4px 12px;
            line-height:1.6;
        ">
            <div style="
                background:#eff6ff;
                border:1px solid #93c5fd;
                border-radius:10px;
                padding:16px;
                margin-bottom:14px;
            ">
                <strong>Utilisation Available Hours Formula</strong>

                <div style="
                    margin-top:10px;
                    font-size:16px;
                    font-weight:700;
                ">
                    MAX(
                        Required Hours - PBM Total Downtime,
                        MIN(Work Hours, Required Hours)
                    )
                </div>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>Why is this formula used?</strong>

                <div style="margin-top:8px;">
                    PBM downtime reduces the Required Hours available to work.
                    However, if the machine physically records more Work Hours
                    than that reduced amount, those Work Hours prove that the
                    machine was available for at least that amount of time.
                    <br><br>

                    The denominator therefore cannot be lower than Work Hours
                    while Work Hours remain below the Required Hours.
                    <br><br>

                    The denominator is capped at Required Hours so that work
                    performed above the required target is recognised as
                    recovery above 100%.
                </div>
            </div>

            <div style="
                background:#ecfdf5;
                border:1px solid #86efac;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>Example — Machine recovers during the shift</strong>

                <div style="margin-top:8px;">
                    Required Hours = 9<br>
                    Work Hours = 8<br>
                    PBM Total Downtime = 1.933<br><br>

                    Required - PBM = 9 - 1.933 =
                    <strong>7.067h</strong><br><br>

                    But the machine physically worked
                    <strong>8 hours</strong>, so it must have been available
                    for at least 8 hours.<br><br>

                    MIN(Work, Required) =
                    MIN(8, 9) =
                    <strong>8h</strong><br><br>

                    Utilisation Available Hours =
                    MAX(7.067, 8) =
                    <strong>8h</strong><br><br>

                    Utilisation =
                    8 ÷ 8 × 100 =
                    <strong>100%</strong>
                </div>
            </div>

            <div style="
                background:#ecfdf5;
                border:1px solid #86efac;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>Example — Recovery above Required Hours</strong>

                <div style="margin-top:8px;">
                    Required Hours = 9<br>
                    Work Hours = 10<br>
                    PBM Total Downtime = 1.933<br><br>

                    MIN(Work, Required) =
                    MIN(10, 9) =
                    <strong>9h</strong><br><br>

                    Utilisation Available Hours =
                    <strong>9h</strong><br><br>

                    Utilisation =
                    10 ÷ 9 × 100 =
                    <strong>111.11%</strong><br><br>

                    The additional work is therefore recognised as recovery
                    above the required target.
                </div>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
            ">
                <strong>Important</strong>

                <div style="margin-top:8px;">
                    If Required Hours are zero, Utilisation is 0%.
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
            text !== "Availability Available Hours"
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
            show_availability_available_hours_formula
        );
    });
}

function show_availability_available_hours_formula() {
    const dialog = new frappe.ui.Dialog({
        title: __("Availability Available Hours"),
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
            padding:6px 4px 12px;
            line-height:1.6;
        ">
            <div style="
                background:#eff6ff;
                border:1px solid #93c5fd;
                border-radius:10px;
                padding:16px;
                margin-bottom:14px;
            ">
                <strong>Availability Available Hours Formula</strong>

                <div style="
                    margin-top:8px;
                    font-size:16px;
                    font-weight:700;
                ">
                    MAX(
                        Work Hours,
                        MAX(
                            Required Hours - PBM Total Downtime,
                            0
                        )
                    )
                </div>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>Utilisation Available Hours</strong>

                <div style="margin-top:8px;">
                    Utilisation uses a separate denominator:
                </div>

                <div style="
                    margin-top:10px;
                    font-weight:700;
                ">
                    MAX(
                        Required Hours - PBM Total Downtime,
                        MIN(Work Hours, Required Hours)
                    )
                </div>

                <div style="margin-top:10px;">
                    This prevents the utilisation denominator from being lower
                    than hours the machine actually worked, while still
                    capping the denominator at Required Hours so recovery
                    above 100% can be recognised.
                </div>
            </div>


            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>Purpose</strong>

                <div style="margin-top:8px;">
                    Availability can exceed 100% when the machine records
                    more Work Hours than its Required Hours.
                </div>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
            ">
                <strong>Totals</strong>

                <div style="margin-top:8px;">
                    Each valid shift is calculated first.
                    Invalid shifts are excluded from the machine,
                    date and category totals.
                </div>
            </div>
        </div>
    `);

    dialog.show();
}

function show_utilisation_formula() {
    const dialog = new frappe.ui.Dialog({
        title: __("Utilisation %"),
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
            padding:6px 4px 12px;
            line-height:1.6;
        ">
            <div style="
                background:#eff6ff;
                border:1px solid #93c5fd;
                border-radius:10px;
                padding:16px;
                margin-bottom:14px;
            ">
                <div style="
                    color:#1d4ed8;
                    font-size:15px;
                    font-weight:700;
                    margin-bottom:8px;
                ">
                    Utilisation Formula
                </div>

                <div style="
                    color:#1d4ed8;
                    font-size:16px;
                    font-weight:700;
                ">
                    Work Hours
                    ÷
                    Utilisation Available Hours
                    × 100
                    × A&amp;U Percentage
                </div>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>Utilisation Available Hours</strong>

                <div style="
                    margin-top:8px;
                    font-weight:700;
                ">
                    MAX(
                        Required Hours - PBM Total Downtime,
                        MIN(Work Hours, Required Hours)
                    )
                </div>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>Example — Why the denominator adjusts</strong>

                <div style="margin-top:8px;">
                    Required Hours = 9<br>
                    PBM Total Downtime = 1.933<br>
                    Work Hours = 8<br><br>

                    Required - PBM =
                    9 - 1.933 =
                    <strong>7.067h</strong><br><br>

                    The machine physically worked 8 hours, so its utilisation
                    denominator cannot reasonably be only 7.067 hours.<br><br>

                    MIN(8, 9) =
                    <strong>8h</strong><br>

                    MAX(7.067, 8) =
                    <strong>8h</strong><br><br>

                    Utilisation =
                    8 ÷ 8 × 100 =
                    <strong>100%</strong><br><br>

                    If the machine works 10 hours against a 9-hour requirement,
                    the denominator remains 9 hours and Utilisation becomes
                    <strong>111.11%</strong>, recognising recovery.
                </div>
            </div>

            <div style="
                background:#ecfdf5;
                border:1px solid #86efac;
                border-radius:10px;
                padding:16px;
            ">
                <strong>Combined / Total Utilisation</strong>

                <div style="margin-top:8px;">
                    Total Work Hours
                    ÷
                    Total Utilisation Available Hours
                    × 100
                    × A&amp;U Percentage
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

        row.classList.toggle(
            "availability-engine-row-expanded"
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
        .dt-row-filter {
            min-height: 68px !important;
            height: 68px !important;
        }

        .query-report[data-report-name="Availability and Utilisation Engine"]
        .dt-row-filter .dt-cell {
            min-height: 68px !important;
            height: 68px !important;
        }

        .query-report[data-report-name="Availability and Utilisation Engine"]
        .dt-row-filter .dt-cell__content {
            height: 100% !important;
            overflow: visible !important;
            white-space: normal !important;
        }

        .availability-engine-header-formula {
            margin-bottom: 5px;
            padding: 4px 3px;
            border: 1px solid #60a5fa;
            border-radius: 4px;
            background: #eff6ff;
            color: #1d4ed8;
            font-size: 9px;
            font-weight: 700;
            line-height: 1.15;
            text-align: center;
            white-space: normal;
        }


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
        .availability-engine-row-expanded
        .dt-cell {
            border-top: 2px solid #22c55e !important;
            border-bottom: 2px solid #22c55e !important;
        }

        .query-report[data-report-name="Availability and Utilisation Engine"]
        .availability-engine-row-expanded
        .dt-cell:first-child {
            border-left: 3px solid #16a34a !important;
        }

        .query-report[data-report-name="Availability and Utilisation Engine"]
        .availability-engine-row-expanded
        .dt-cell:last-child {
            border-right: 2px solid #22c55e !important;
        }
    `;

    document.head.appendChild(style);
}