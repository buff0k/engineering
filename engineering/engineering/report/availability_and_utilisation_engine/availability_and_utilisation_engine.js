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
                    "IF Work > 0: Work - PBM | IF Work = 0: Req - PBM"
                ),
                "available_hours_above_100": (
                    "MAX(Work Hrs, Shift Available)"
                ),
                "availability_percentage": (
                    "(Above 100 / Req Hrs) × 100 × A&U"
                ),
                "utilisation_work_hours": (
                    "Work Hrs used when Util Available > 0"
                ),
                "utilisation_available_hours": (
                    "IF Work >= Req: Req | ELSE: Req - PBM"
                ),
                "utilisation_percentage": (
                    "(Util Work Hrs / Util Available Hrs) × 100 × A&U"
                )
            };

            const formula = formulas[
                column.fieldname
            ];

            if (!formula) {
                return "";
            }

            return `
                <div
                    class="availability-engine-formula-cell"
                    style="
                    display:block;
                    width:100%;
                    min-height:44px;
                    padding:6px 5px;
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
            "available_hours_above_100",
            "utilisation_work_hours",
            "utilisation_available_hours"
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
                    <li>
                        Work Hours &gt; 0 while Utilisation Available Hours = 0.
                    </li>
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
                    <li>
                        Utilisation Available Hours exceed the physical shift length.
                    </li>
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
                $(this).text() || ""
            )
                .replace(/\s+/g, " ")
                .trim();

            if (text === "Shift Available Hours") {
                event.preventDefault();
                event.stopPropagation();
                show_shift_available_formula();
                return;
            }

            if (text === "Available Hours Above 100") {
                event.preventDefault();
                event.stopPropagation();
                show_available_hours_above_100_formula();
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
    const clickable_headers = [
        "Shift Available Hours",
        "Available Hours Above 100",
        "Utilisation %"
    ];

    document.querySelectorAll(
        ".dt-cell--header"
    ).forEach(function(header) {
        const text = (
            header.innerText || ""
        )
            .replace(/\s+/g, " ")
            .trim();

        if (!clickable_headers.includes(text)) {
            return;
        }

        header.style.cursor = "pointer";
        header.title = "Click to view formula";
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
                    If Work Hours &gt; 0:
                    <br>
                    MIN(
                        MAX(
                            Work Hours - PBM Total Downtime,
                            0
                        ),
                        Required Hours
                    )

                    <br><br>

                    If Work Hours = 0:
                    <br>
                    MAX(
                        Required Hours - PBM Total Downtime,
                        0
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
                <strong>1. If the machine worked</strong>

                <div style="margin-top: 6px;">
                    Shift Available Hours is calculated from
                    Work Hours minus PBM Total Downtime.
                    The result cannot be below 0 and cannot
                    exceed Required Hours.
                </div>
            </div>

            <div style="
                background: #f8fafc;
                border: 1px solid #d1d8dd;
                border-radius: 10px;
                padding: 16px;
                margin-bottom: 12px;
            ">
                <strong>2. If the machine did not work</strong>

                <div style="margin-top: 6px;">
                    Zero Work Hours does not mean that the
                    machine was unavailable.

                    Required Hours minus PBM Total Downtime is
                    used to determine how many hours the machine
                    was available during the shift.
                </div>
            </div>

            <div style="
                background: #f8fafc;
                border: 1px solid #d1d8dd;
                border-radius: 10px;
                padding: 16px;
            ">
                <strong>Example</strong>

                <div style="margin-top: 6px;">
                    Required Hours = 9<br>
                    Work Hours = 0<br>
                    PBM Total Downtime = 0<br><br>

                    Shift Available Hours = 9<br>
                    Utilisation = 0 / 9 = 0%
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
                    If Work Hours &gt; 0:
                    <br>
                    Work Hours - PBM Total Downtime

                    <br><br>

                    If Work Hours = 0:
                    <br>
                    Required Hours - PBM Total Downtime
                </div>

                <div>
                    The result cannot be below 0 or above the
                    shift's Required Hours. A machine can therefore
                    have Shift Available Hours even when it recorded
                    zero Work Hours.
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
                    Utilisation Work Hours
                    ÷
                    Utilisation Available Hours
                    × 100
                    × A&amp;U Percentage
                </div>

                <div style="margin-top:10px;">
                    Utilisation shows how much of the machine's
                    available production opportunity was actually used.
                </div>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>How Utilisation Available Hours is chosen</strong>

                <div style="margin-top:8px;">
                    <strong>If Work Hours are less than Required Hours:</strong>
                    <br>
                    Utilisation Available Hours =
                    Required Hours - PBM Total Downtime
                    <br><br>

                    <strong>If Work Hours reach or exceed Required Hours:</strong>
                    <br>
                    Utilisation Available Hours =
                    Required Hours
                </div>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>Example 1 — Machine was available but did not work</strong>

                <div style="margin-top:8px;">
                    Required Hours = 9<br>
                    Work Hours = 0<br>
                    PBM Total Downtime = 0<br><br>

                    Utilisation Available Hours =
                    9 - 0 = <strong>9</strong><br>

                    Utilisation =
                    0 ÷ 9 =
                    <strong>0%</strong>
                </div>

                <div style="margin-top:8px;">
                    The machine had 9 available hours but none
                    of them were used.
                </div>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>Example 2 — Breakdown reduced the available opportunity</strong>

                <div style="margin-top:8px;">
                    Required Hours = 9<br>
                    Work Hours = 4<br>
                    PBM Total Downtime = 6<br><br>

                    Because Work Hours are below Required Hours:
                    <br>

                    Utilisation Available Hours =
                    9 - 6 =
                    <strong>3</strong><br>

                    Utilisation =
                    4 ÷ 3 =
                    <strong>133.33%</strong>
                </div>

                <div style="margin-top:8px;">
                    Utilisation can be above 100% because the
                    machine worked more hours than the calculated
                    available production opportunity.
                </div>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>Example 3 — Machine worked beyond Required Hours</strong>

                <div style="margin-top:8px;">
                    Required Hours = 9<br>
                    Work Hours = 10<br>
                    PBM Total Downtime = 1<br><br>

                    Because Work Hours reached or exceeded Required Hours:
                    <br>

                    Utilisation Available Hours =
                    <strong>9</strong><br>

                    Utilisation =
                    10 ÷ 9 =
                    <strong>111.11%</strong>
                </div>

                <div style="margin-top:8px;">
                    The mine required 9 hours, but the machine
                    worked 10 hours, so Utilisation is above 100%.
                </div>
            </div>

            <div style="
                background:#f8fafc;
                border:1px solid #d1d8dd;
                border-radius:10px;
                padding:16px;
                margin-bottom:12px;
            ">
                <strong>Example 4 — Machine was unavailable for the whole required period</strong>

                <div style="margin-top:8px;">
                    Required Hours = 9<br>
                    Work Hours = 0<br>
                    PBM Total Downtime = 9<br><br>

                    Utilisation Available Hours =
                    9 - 9 =
                    <strong>0</strong><br>

                    Utilisation =
                    <strong>N/A</strong>
                </div>

                <div style="margin-top:8px;">
                    There were no available hours to utilise,
                    so the shift does not contribute to the
                    combined Utilisation denominator.
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
                    Total Utilisation is not an average of the
                    individual shift percentages.
                    <br><br>

                    It uses:
                    <br>

                    <strong>
                        SUM(Utilisation Work Hours)
                        ÷
                        SUM(Utilisation Available Hours)
                        × 100
                        × A&amp;U Percentage
                    </strong>
                    <br><br>

                    This correctly weights every valid shift by
                    the number of Utilisation Available Hours
                    that shift contributed.
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
        .dt-row:has(.availability-engine-formula-cell),
        .query-report[data-report-name="Availability and Utilisation Engine"]
        .dt-row:has(.availability-engine-formula-cell) .dt-cell,
        .query-report[data-report-name="Availability and Utilisation Engine"]
        .dt-row:has(.availability-engine-formula-cell) .dt-cell__content {
            min-height: 58px !important;
            height: auto !important;
            overflow: visible !important;
            white-space: normal !important;
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