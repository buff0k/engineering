frappe.require(
    "/assets/engineering/css/engineering_legals_monthly_summary.css"
);

frappe.query_reports["Engineering Legals Monthly Summary"] = {
    filters: [
        {
            fieldname: "year",
            label: __("Year"),
            fieldtype: "Int",
            default: frappe.datetime.get_today().substring(0, 4),
            reqd: 1,
        },
        {
            fieldname: "month",
            label: __("Month"),
            fieldtype: "Select",
            options: [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ],
            default: moment().format("MMM"),
            reqd: 1,
        },
        {
            fieldname: "site",
            label: __("Site"),
            fieldtype: "Link",
            options: "Location",
        },
    ],

    onload(report) {
        report.page.add_inner_button(
            __("Refresh Summary"),
            () => report.refresh()
        );
    },

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(
            value,
            row,
            column,
            data
        );

        if (!data) {
            return value;
        }

        if (data.is_total) {
            return `<strong>${value}</strong>`;
        }

        if (column.fieldname === "category") {
            let missingItems = [];

            try {
                missingItems = JSON.parse(
                    data.missing_items_json || "[]"
                );
            } catch (error) {
                console.error(
                    "Unable to read missing legal items:",
                    error
                );
            }

            const missingHtml = missingItems.length
                ? `
                    <div
                        style="
                            margin-top: 6px;
                            font-size: 11px;
                            line-height: 1.5;
                            color: var(--red-600);
                            white-space: normal;
                        "
                    >
                        <strong>${__("Not done")}:</strong>
                        ${missingItems.map((item) => `
                            <div>
                                • ${frappe.utils.escape_html(item)}
                            </div>
                        `).join("")}
                    </div>
                `
                : "";

            return `
                <div style="white-space: normal;">
                    <span style="font-weight: 600;">
                        ${value}
                    </span>
                    ${missingHtml}
                </div>
            `;
        }

        if (column.fieldname === "frequency_rule") {
            const badgeClass =
                data.mode === "active_until_expiry"
                    ? "indicator-pill green"
                    : "indicator-pill blue";

            return `
                <span class="${badgeClass}">
                    ${value}
                </span>
            `;
        }

        if (column.fieldname === "completed") {
            return `
                <strong>
                    ${frappe.utils.escape_html(
                        String(data.completed || 0)
                    )}
                </strong>
            `;
        }

        if (
            column.fieldname === "tmm" ||
            column.fieldname === "ldv" ||
            column.fieldname === "drills"
        ) {
            const count = Number(
                data[column.fieldname] || 0
            );

            return `<strong>${count}</strong>`;
        }

        if (column.fieldname === "view_rows") {
            if (!data.view_enabled) {
                return "";
            }

            return `
                <button
                    type="button"
                    class="btn btn-xs btn-primary
                           engineering-legals-view-rows"
                    data-records="${frappe.utils.escape_html(
                        data.record_names_json || "[]"
                    )}"
                    style="
                        min-width: 88px;
                        border-radius: 12px;
                        font-weight: 600;
                    "
                >
                    ${__("View Rows")}
                </button>
            `;
        }

        return value;
    },

    after_datatable_render() {
        setTimeout(() => {
            bind_view_rows_buttons();
        }, 100);
    },
};


function bind_view_rows_buttons() {
    $(".engineering-legals-view-rows")
        .off("click.engineering_legals_view_rows")
        .on(
            "click.engineering_legals_view_rows",
            function () {
                let recordNames = [];

                try {
                    recordNames = JSON.parse(
                        $(this).attr("data-records") || "[]"
                    );
                } catch (error) {
                    console.error(
                        "Unable to read Engineering Legals rows:",
                        error
                    );
                }

                open_engineering_legal_rows(recordNames);
            }
        );
}


function open_engineering_legal_rows(recordNames) {
    const names =
        recordNames && recordNames.length
            ? recordNames
            : ["__NO_ENGINEERING_LEGALS_RECORDS__"];

    frappe.route_options = {
        name: ["in", names],
    };

    frappe.set_route(
        "List",
        "Engineering Legals",
        "List"
    );
}

// MACHINE PLANT LIST CLICK ACTION - START
$(document)
    .off(
        "click.engineering_machine_plant",
        ".engineering-machine-count-link"
    )
    .on(
        "click.engineering_machine_plant",
        ".engineering-machine-count-link",
        function () {
            const machineType =
                ($(this).attr("data-machine-type") || "").trim();

            const site =
                ($(this).attr("data-site") || "").trim();

            show_submitted_machine_dialog(
                machineType,
                site
            );
        }
    );


function show_submitted_machine_dialog(machineType, site) {
    frappe.call({
        method:
            "engineering.engineering.report.engineering_legals_monthly_summary.engineering_legals_monthly_summary.get_submitted_machine_rows",
        args: {
            machine_type: machineType,
            site: site,
        },
        freeze: true,
        freeze_message: __(
            "Loading submitted machines..."
        ),
        callback(response) {
            const result = response.message || {};
            const rows = result.rows || [];

            const dialog = new frappe.ui.Dialog({
                title: __(
                    "Machine Plant List - {0}",
                    [machineType]
                ),
                size: "extra-large",
                fields: [
                    {
                        fieldtype: "HTML",
                        fieldname: "machine_rows_html",
                    },
                ],
            });

            const machineHtml =
                machineType === "Total Fleet"
                    ? build_grouped_total_fleet_html(
                        rows,
                        result.site || site || "All Sites"
                    )
                    : build_machine_rows_html(
                        machineType,
                        result.site || site,
                        rows
                    );

            dialog.fields_dict.machine_rows_html.$wrapper.html(
                machineHtml
            );

            dialog.set_primary_action(
                __("Print"),
                () => {
                    print_machine_plant_dialog(
                        machineType,
                        result.site || site || "All Sites",
                        machineHtml
                    );
                }
            );

            dialog.show();
        },
    });
}


function build_machine_rows_html(
    machineType,
    site,
    rows
) {
    const escape = frappe.utils.escape_html;

    let bodyRows = "";

    if (rows.length) {
        bodyRows = rows.map((row) => `
            <tr>
                <td>
                    <a
                        href="/app/asset/${encodeURIComponent(
                            row.name
                        )}"
                        target="_blank"
                        style="font-weight: 700;"
                    >
                        ${escape(row.name || "")}
                    </a>
                </td>
                <td>${escape(row.item_name || "")}</td>
                <td>${escape(row.asset_category || "")}</td>
                <td>${escape(row.location || "")}</td>
            </tr>
        `).join("");
    } else {
        bodyRows = `
            <tr>
                <td
                    colspan="4"
                    style="
                        text-align: center;
                        padding: 25px;
                        color: var(--text-muted);
                    "
                >
                    ${__("No submitted machines found.")}
                </td>
            </tr>
        `;
    }

    return `
        <div class="engineering-machine-dialog">
            <div class="engineering-machine-dialog__title">
                ${__("Submitted {0} for {1}", [
                    escape(machineType),
                    escape(site || "All Sites"),
                ])}
            </div>

            <div class="table-responsive">
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>${__("Plant Number")}</th>
                            <th>${__("Item Name")}</th>
                            <th>${__("Category")}</th>
                            <th>${__("Location")}</th>
                        </tr>
                    </thead>

                    <tbody>
                        ${bodyRows}
                    </tbody>

                    <tfoot>
                        <tr>
                            <th colspan="4" class="text-right">
                                ${__("Total")}
                            </th>
                            <th>
                                ${rows.length}
                            </th>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>
    `;
}
// MACHINE PLANT LIST CLICK ACTION - END


function simpleLegalStatus(done, completedLabel) {
    if (!done) {
        return `
            <div
                style="
                    color: var(--red-600);
                    font-size: 11px;
                    font-weight: 600;
                    white-space: normal;
                "
            >
                ${__("Not done")}
            </div>
        `;
    }

    return `
        <div
            style="
                color: var(--green-600);
                font-size: 11px;
                white-space: normal;
                line-height: 1.35;
            "
        >
            • ${frappe.utils.escape_html(completedLabel)}
        </div>
    `;
}


function applicableLegalStatus(
    applicable,
    done,
    completedLabel
) {
    if (!applicable) {
        return `
            <div
                style="
                    color: var(--text-muted);
                    font-size: 11px;
                    font-weight: 600;
                    white-space: normal;
                "
            >
                ${__("N/A")}
            </div>
        `;
    }

    return simpleLegalStatus(done, completedLabel);
}


function completedLegalItems(items) {
    const completedItems = items || [];

    if (!completedItems.length) {
        return `
            <div
                style="
                    color: var(--red-600);
                    font-size: 11px;
                    font-weight: 600;
                    white-space: normal;
                "
            >
                ${__("Not done")}
            </div>
        `;
    }

    return completedItems
        .map((item) => `
            <div
                style="
                    color: var(--green-600);
                    font-size: 11px;
                    white-space: normal;
                    line-height: 1.35;
                    margin-top: 3px;
                "
            >
                • ${frappe.utils.escape_html(item)}
            </div>
        `)
        .join("");
}


function conditionMonitoringStatus(row) {
    const doneItems =
        row.condition_monitoring_done || [];

    if (!doneItems.length) {
        return `
            <div
                style="
                    color: var(--red-600);
                    font-size: 11px;
                    font-weight: 600;
                    white-space: normal;
                "
            >
                ${__("Not done")}
            </div>
        `;
    }

    const doneHtml = doneItems
        .map((item) => `
            <div
                style="
                    margin-top: 3px;
                    color: var(--green-600);
                    font-size: 11px;
                    white-space: normal;
                    line-height: 1.35;
                "
            >
                • ${frappe.utils.escape_html(item)}
            </div>
        `)
        .join("");

    return `
        <div style="min-width: 190px;">
            ${doneHtml}
        </div>
    `;
}


// MACHINE PLANT POPUP DIRECT ACTION - START
window.openEngineeringMachineRows = function (
    machineType,
    site
) {
    if (machineType === "Total Fleet") {
        open_grouped_total_fleet_popup(site);
        return;
    }

    const year =
        frappe.query_report.get_filter_value("year");

    const month =
        frappe.query_report.get_filter_value("month");

    frappe.call({
        method:
            "engineering.engineering.report.engineering_legals_monthly_summary.engineering_legals_monthly_summary.get_machine_legal_status_rows",
        args: {
            machine_type: machineType,
            site: site,
            year: year,
            month: month,
        },
        freeze: true,
        freeze_message: __(
            "Loading machine legal status..."
        ),
        callback(response) {
            const result = response.message || {};
            const rows = result.rows || [];

            const statusBadge = (done) => {
                return done
                    ? `
                        <span class="indicator-pill green">
                            ${__("Done")}
                        </span>
                    `
                    : `
                        <span class="indicator-pill red">
                            ${__("Missing")}
                        </span>
                    `;
            };

            const bodyRows = rows.length
                ? rows.map((row) => `
                    <tr>
                        <td>
                            <a
                                href="/app/asset/${encodeURIComponent(
                                    row.name
                                )}"
                                target="_blank"
                                style="font-weight:700;"
                            >
                                ${frappe.utils.escape_html(
                                    row.name || ""
                                )}
                            </a>
                        </td>

                        <td>
                            ${simpleLegalStatus(
                                row.fire_suppression,
                                __("Fire Suppression")
                            )}
                        </td>

                        <td>
                            ${conditionMonitoringStatus(row)}
                        </td>

                        <td>
                            ${simpleLegalStatus(
                                row.brake_tested,
                                __("Brake Tested")
                            )}
                        </td>

                        <td>
                            ${simpleLegalStatus(
                                row.frcs,
                                __("FRCS")
                            )}
                        </td>

                        <td>
                            ${applicableLegalStatus(
                                row.load_testing_applicable,
                                row.load_testing,
                                __("Load Testing")
                            )}
                        </td>

                        <td>
                            ${completedLegalItems(
                                row.maintenance_done
                            )}
                        </td>

                        <td>
                            ${simpleLegalStatus(
                                row.pds_mpi,
                                __("PDS-MPI Maintenance")
                            )}
                        </td>

                        <td>
                            ${applicableLegalStatus(
                                row.pressure_vessels_applicable,
                                row.pressure_vessels,
                                __("Pressure Vessels")
                            )}
                        </td>
                    </tr>
                `).join("")
                : `
                    <tr>
                        <td
                            colspan="9"
                            style="
                                text-align:center;
                                padding:28px;
                            "
                        >
                            ${__("No submitted machines found.")}
                        </td>
                    </tr>
                `;

            const html = `
                <div class="engineering-machine-dialog">
                    <div class="engineering-machine-dialog__title">
                        ${frappe.utils.escape_html(machineType)}
                        —
                        ${frappe.utils.escape_html(
                            result.site || site || "All Sites"
                        )}
                    </div>

                    <div class="table-responsive">
                        <table
                            class="table table-bordered table-hover"
                        >
                            <thead>
                                <tr>
                                    <th>${__("Plant Number")}</th>
                                    <th>${__("Fire Suppression")}</th>
                                    <th>${__("Condition Monitoring")}</th>
                                    <th>${__("Brake Tested")}</th>
                                    <th>${__("FRCS")}</th>
                                    <th>${__("Load Testing")}</th>
                                    <th>${__("Maintenance Schedules")}</th>
                                    <th>${__("PDS-MPI Maintenance")}</th>
                                    <th>${__("Pressure Vessels")}</th>
                                </tr>
                            </thead>

                            <tbody>
                                ${bodyRows}
                            </tbody>

                            <tfoot>
                                <tr>
                                    <th
                                        colspan="8"
                                        class="text-right"
                                    >
                                        ${__("Total Machines")}
                                    </th>
                                    <th>${rows.length}</th>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>
            `;

            show_machine_dialog(
                `${machineType} Legal Status`,
                machineType,
                result.site || site || "All Sites",
                html
            );
        },
    });
};


function open_grouped_total_fleet_popup(site) {
    frappe.call({
        method:
            "engineering.engineering.report.engineering_legals_monthly_summary.engineering_legals_monthly_summary.get_submitted_machine_rows",
        args: {
            machine_type: "Total Fleet",
            site: site,
        },
        freeze: true,
        freeze_message: __("Loading total fleet..."),
        callback(response) {
            const result = response.message || {};
            const rows = result.rows || [];

            const html = build_grouped_total_fleet_html(
                rows,
                result.site || site || "All Sites"
            );

            show_machine_dialog(
                __("Machine Plant List - Total Fleet"),
                "Total Fleet",
                result.site || site || "All Sites",
                html
            );
        },
    });
}


function show_machine_dialog(
    title,
    machineType,
    site,
    html
) {
    const dialog = new frappe.ui.Dialog({
        title: title,
        size: "extra-large",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "machine_rows_html",
            },
        ],
    });

    dialog.fields_dict
        .machine_rows_html
        .$wrapper
        .html(html);

    if (
        typeof print_machine_plant_dialog
        === "function"
    ) {
        dialog.set_primary_action(
            __("Print"),
            () => {
                print_machine_plant_dialog(
                    machineType,
                    site,
                    html
                );
            }
        );
    }

    dialog.show();
}
// MACHINE PLANT POPUP DIRECT ACTION - END


// MACHINE PLANT TABLE DELEGATED CLICK - START
$(document)
    .off(
        "click.machine_plant_popup",
        ".engineering-machine-count-link"
    )
    .on(
        "click.machine_plant_popup",
        ".engineering-machine-count-link",
        function (event) {
            event.preventDefault();
            event.stopPropagation();

            const machineType =
                ($(this).attr("data-machine-type") || "").trim();

            const site =
                ($(this).attr("data-site") || "").trim();

            if (
                typeof window.openEngineeringMachineRows
                !== "function"
            ) {
                frappe.msgprint(
                    __("Machine popup function is not loaded.")
                );
                return;
            }

            window.openEngineeringMachineRows(
                machineType,
                site
            );
        }
    );
// MACHINE PLANT TABLE DELEGATED CLICK - END



function print_machine_plant_dialog(
    machineType,
    site,
    tableHtml
) {
    const printWindow = window.open(
        "",
        "_blank",
        "width=1000,height=750"
    );

    if (!printWindow) {
        frappe.msgprint(
            __("Please allow pop-ups to print this list.")
        );
        return;
    }

    const title = `${machineType} Machine Plant List - ${site}`;

    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>${frappe.utils.escape_html(title)}</title>

            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 24px;
                    color: #222;
                }

                h2 {
                    margin: 0 0 6px;
                    font-size: 20px;
                }

                .print-subtitle {
                    margin-bottom: 18px;
                    font-size: 13px;
                    color: #555;
                }

                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 12px;
                }

                th,
                td {
                    border: 1px solid #bbb;
                    padding: 8px 10px;
                    text-align: left;
                    font-size: 12px;
                }

                th {
                    background: #eaf3ff;
                    font-weight: 700;
                }

                tfoot th {
                    background: #eef5ff;
                }

                a {
                    color: #000;
                    text-decoration: none;
                }

                .engineering-machine-dialog__title {
                    display: none;
                }

                @page {
                    size: landscape;
                    margin: 12mm;
                }
            </style>
        </head>

        <body>
            <h2>${frappe.utils.escape_html(machineType)} Machine Plant List</h2>

            <div class="print-subtitle">
                Site:
                <strong>${frappe.utils.escape_html(site)}</strong>
            </div>

            ${tableHtml}

            <script>
                window.onload = function () {
                    window.print();
                };
            <\/script>
        </body>
        </html>
    `);

    printWindow.document.close();
}


// GROUPED TOTAL FLEET POPUP - START
function build_grouped_total_fleet_html(rows, site) {
    const escape = frappe.utils.escape_html;

    const categoryOrder = [
        "Excavator",
        "Dozer",
        "ADT",
        "Water Bowser",
        "Grader",
        "TLB",
        "Lighting Plant",
        "Service Truck",
        "Diesel Bowser",
        "Loader",
        "Drills",
        "LDV",
    ];

    const categoryAliases = {
        "EXCAVATOR": "Excavator",
        "EXCAVATORS": "Excavator",
        "DOZER": "Dozer",
        "DOZERS": "Dozer",
        "ADT": "ADT",
        "ADTS": "ADT",
        "ARTICULATED DUMP TRUCK": "ADT",
        "ARTICULATED DUMP TRUCKS": "ADT",
        "WATER BOWSER": "Water Bowser",
        "WATER BOWSERS": "Water Bowser",
        "WATERBOWSER": "Water Bowser",
        "WATERBOWSERS": "Water Bowser",
        "GRADER": "Grader",
        "GRADERS": "Grader",
        "TLB": "TLB",
        "TLBS": "TLB",
        "LIGHTING PLANT": "Lighting Plant",
        "LIGHTING PLANTS": "Lighting Plant",
        "LIGHT TOWER": "Lighting Plant",
        "LIGHT TOWERS": "Lighting Plant",

        "SERVICE TRUCK": "Service Truck",
        "SERVICE TRUCKS": "Service Truck",

        "DIESEL BOWSER": "Diesel Bowser",
        "DIESEL BOWSERS": "Diesel Bowser",
        "DIESELBOWSER": "Diesel Bowser",
        "DIESELBOWSERS": "Diesel Bowser",

        "LOADER": "Loader",
        "LOADERS": "Loader",
        "FRONT END LOADER": "Loader",
        "FRONT END LOADERS": "Loader",
        "FRONT-END LOADER": "Loader",
        "FRONT-END LOADERS": "Loader",

        "DRILL": "Drills",
        "DRILLS": "Drills",
        "LDV": "LDV",
        "LDVS": "LDV",
    };

    const grouped = {};

    categoryOrder.forEach((category) => {
        grouped[category] = [];
    });

    rows.forEach((row) => {
        const rawCategory = String(
            row.asset_category || ""
        )
            .trim()
            .toUpperCase();

        const category =
            categoryAliases[rawCategory] || rawCategory;

        if (!grouped[category]) {
            grouped[category] = [];
        }

        grouped[category].push(row);
    });

    const sections = categoryOrder.map((category) => {
        const categoryRows = grouped[category] || [];

        const tableRows = categoryRows.length
            ? categoryRows.map((row) => `
                <tr>
                    <td>
                        <a
                            href="/app/asset/${encodeURIComponent(
                                row.name
                            )}"
                            target="_blank"
                            style="font-weight: 700;"
                        >
                            ${escape(row.name || "")}
                        </a>
                    </td>

                    <td>
                        ${escape(row.item_name || "")}
                    </td>

                    <td>
                        ${escape(row.location || "")}
                    </td>
                </tr>
            `).join("")
            : `
                <tr>
                    <td
                        colspan="3"
                        style="
                            padding: 14px;
                            text-align: center;
                            color: var(--text-muted);
                        "
                    >
                        ${__("No submitted machines")}
                    </td>
                </tr>
            `;

        return `
            <div class="engineering-total-fleet-section">
                <div class="engineering-total-fleet-section__heading">
                    <span>${escape(category)}</span>

                    <span class="indicator-pill blue">
                        ${categoryRows.length}
                    </span>
                </div>

                <div class="table-responsive">
                    <table
                        class="table table-bordered table-hover"
                    >
                        <thead>
                            <tr>
                                <th>${__("Plant Number")}</th>
                                <th>${__("Item Name")}</th>
                                <th>${__("Location")}</th>
                            </tr>
                        </thead>

                        <tbody>
                            ${tableRows}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }).join("");

    return `
        <div class="engineering-machine-dialog">
            <div class="engineering-machine-dialog__title"
                 style="
                    display:flex;
                    align-items:center;
                    justify-content:space-between;
                    gap:12px;
                 ">
                <span>
                    ${__("Total Fleet for {0}", [
                        escape(site || "All Sites"),
                    ])}
                </span>

                <button
                    type="button"
                    class="btn btn-xs btn-primary
                           engineering-view-all-legals"
                    data-site="${escape(site || "All Sites")}"
                    style="
                        padding:4px 12px;
                        font-size:11px;
                        border-radius:10px;
                        font-weight:700;
                    "
                >
                    ${__("View All Legals")}
                </button>
            </div>

            <div class="engineering-total-fleet-sections">
                ${sections}
            </div>

            <div class="engineering-total-fleet-grand-total">
                <span>${__("Total Fleet")}</span>
                <strong>${rows.length}</strong>
            </div>
        </div>
    `;
}
// GROUPED TOTAL FLEET POPUP - END


// TOTAL FLEET VIEW LEGALS BUTTON - START
$(document)
    .off(
        "click.total_fleet_view_legals",
        ".engineering-view-category-legals"
    )
    .on(
        "click.total_fleet_view_legals",
        ".engineering-view-category-legals",
        function (event) {
            event.preventDefault();
            event.stopPropagation();

            const machineType =
                ($(this).attr("data-machine-type") || "").trim();

            const site =
                ($(this).attr("data-site") || "").trim();

            window.openEngineeringMachineRows(
                machineType,
                site
            );
        }
    );
// TOTAL FLEET VIEW LEGALS BUTTON - END


// TOTAL FLEET VIEW ALL LEGALS - START
$(document)
    .off(
        "click.total_fleet_view_all_legals",
        ".engineering-view-all-legals"
    )
    .on(
        "click.total_fleet_view_all_legals",
        ".engineering-view-all-legals",
        function (event) {
            event.preventDefault();
            event.stopPropagation();

            const site =
                ($(this).attr("data-site") || "").trim();

            open_total_fleet_legal_status(site);
        }
    );


function open_total_fleet_legal_status(site) {
    const year =
        frappe.query_report.get_filter_value("year");

    const month =
        frappe.query_report.get_filter_value("month");

    frappe.call({
        method:
            "engineering.engineering.report.engineering_legals_monthly_summary.engineering_legals_monthly_summary.get_machine_legal_status_rows",
        args: {
            machine_type: "Total Fleet",
            site: site,
            year: year,
            month: month,
        },
        freeze: true,
        freeze_message: __("Loading all fleet legals..."),
        callback(response) {
            const result = response.message || {};
            const rows = result.rows || [];
            const escape = frappe.utils.escape_html;

            const machineTypeOrder = [
                "Excavator",
                "Dozer",
                "ADT",
                "Water Bowser",
                "Grader",
                "TLB",
                "Lighting Plant",
                "Service Truck",
                "Diesel Bowser",
                "Loader",
                "Drills",
                "LDV",
            ];

            const groupedRows = {};

            machineTypeOrder.forEach((machineType) => {
                groupedRows[machineType] = [];
            });

            rows.forEach((row) => {
                const machineType =
                    String(row.machine_type || "Other").trim();

                if (!groupedRows[machineType]) {
                    groupedRows[machineType] = [];
                }

                groupedRows[machineType].push(row);
            });

            const statusBadge = (done) => {
                return done
                    ? `
                        <span class="indicator-pill green">
                            ${__("Done")}
                        </span>
                    `
                    : `
                        <span class="indicator-pill red">
                            ${__("Missing")}
                        </span>
                    `;
            };

            const sections = machineTypeOrder
                .map((machineType) => {
                    const machineRows =
                        groupedRows[machineType] || [];

                    if (!machineRows.length) {
                        return "";
                    }

                    const bodyRows = machineRows
                        .map((row) => `
                            <tr>
                                <td>
                                    <a
                                        href="/app/asset/${encodeURIComponent(
                                            row.name
                                        )}"
                                        target="_blank"
                                        style="font-weight:700;"
                                    >
                                        ${escape(row.name || "")}
                                    </a>
                                </td>

                                <td>
                                    ${simpleLegalStatus(
                                        row.fire_suppression,
                                        __("Fire Suppression")
                                    )}
                                </td>

                                <td>
                                    ${conditionMonitoringStatus(row)}
                                </td>

                                <td>
                                    ${simpleLegalStatus(
                                        row.brake_tested,
                                        __("Brake Tested")
                                    )}
                                </td>

                                <td>
                                    ${simpleLegalStatus(
                                        row.frcs,
                                        __("FRCS")
                                    )}
                                </td>

                                <td>
                                    ${applicableLegalStatus(
                                        row.load_testing_applicable,
                                        row.load_testing,
                                        __("Load Testing")
                                    )}
                                </td>

                                <td>
                                    ${completedLegalItems(
                                        row.maintenance_done
                                    )}
                                </td>

                                <td>
                                    ${simpleLegalStatus(
                                        row.pds_mpi,
                                        __("PDS-MPI Maintenance")
                                    )}
                                </td>

                                <td>
                                    ${applicableLegalStatus(
                                        row.pressure_vessels_applicable,
                                        row.pressure_vessels,
                                        __("Pressure Vessels")
                                    )}
                                </td>
                            </tr>
                        `)
                        .join("");

                    return `
                        <div class="engineering-total-fleet-section">
                            <div
                                class="engineering-total-fleet-section__heading"
                            >
                                <span>${escape(machineType)}</span>

                                <span class="indicator-pill blue">
                                    ${machineRows.length}
                                </span>
                            </div>

                            <div class="table-responsive">
                                <table
                                    class="table table-bordered table-hover"
                                >
                                    <thead>
                                        <tr>
                                            <th>
                                                ${__("Plant Number")}
                                            </th>
                                            <th>
                                                ${__("Fire Suppression")}
                                            </th>
                                            <th>
                                                ${__("Condition Monitoring")}
                                            </th>
                                            <th>
                                                ${__("Brake Tested")}
                                            </th>
                                            <th>
                                                ${__("FRCS")}
                                            </th>
                                            <th>
                                                ${__("Load Testing")}
                                            </th>
                                            <th>
                                                ${__("Maintenance Schedules")}
                                            </th>
                                            <th>
                                                ${__("PDS-MPI Maintenance")}
                                            </th>
                                            <th>
                                                ${__("Pressure Vessels")}
                                            </th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        ${bodyRows}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    `;
                })
                .join("");

            const html = `
                <div class="engineering-machine-dialog">
                    <div class="engineering-machine-dialog__title">
                        ${__("All Fleet Legal Status — {0}", [
                            escape(
                                result.site || site || "All Sites"
                            ),
                        ])}
                    </div>

                    <div class="engineering-total-fleet-sections">
                        ${
                            sections ||
                            `
                                <div
                                    style="
                                        text-align:center;
                                        padding:28px;
                                    "
                                >
                                    ${__(
                                        "No submitted machines found."
                                    )}
                                </div>
                            `
                        }
                    </div>

                    <div
                        class="engineering-total-fleet-grand-total"
                    >
                        <span>${__("Total Machines")}</span>
                        <strong>${rows.length}</strong>
                    </div>
                </div>
            `;

            show_machine_dialog(
                __("All Fleet Legal Status"),
                "Total Fleet Legals",
                result.site || site || "All Sites",
                html
            );
        },
        error(error) {
            console.error(error);

            frappe.msgprint(
                __("Could not load all fleet legal status.")
            );
        },
    });
}

// TOTAL FLEET VIEW ALL LEGALS - END


// MAIN MACHINE PLANT LIST VIEW LEGALS - START
$(document)
    .off(
        "click.main_machine_view_legals",
        ".engineering-main-view-legals"
    )
    .on(
        "click.main_machine_view_legals",
        ".engineering-main-view-legals",
        function (event) {
            event.preventDefault();
            event.stopPropagation();

            const machineType =
                ($(this).attr("data-machine-type") || "").trim();

            const site =
                ($(this).attr("data-site") || "").trim();

            if (machineType === "Total Fleet") {
                open_total_fleet_legal_status(site);
            } else {
                window.openEngineeringMachineRows(
                    machineType,
                    site
                );
            }
        }
    );
// MAIN MACHINE PLANT LIST VIEW LEGALS - END


// MAIN MACHINE VIEW PLANT LIST - START
$(document)
    .off(
        "click.main_machine_view_plant_list",
        ".engineering-view-plant-list"
    )
    .on(
        "click.main_machine_view_plant_list",
        ".engineering-view-plant-list",
        function (event) {
            event.preventDefault();
            event.stopPropagation();

            const machineType =
                ($(this).attr("data-machine-type") || "").trim();

            const site =
                ($(this).attr("data-site") || "").trim();

            open_machine_plant_list(
                machineType,
                site
            );
        }
    );


function open_machine_plant_list(machineType, site) {
    frappe.call({
        method:
            "engineering.engineering.report.engineering_legals_monthly_summary.engineering_legals_monthly_summary.get_submitted_machine_rows",
        args: {
            machine_type: machineType,
            site: site,
        },
        freeze: true,
        freeze_message: __("Loading machine plant list..."),

        callback(response) {
            const result = response.message || {};
            const rows = result.rows || [];
            const resolvedSite =
                result.site || site || "All Sites";

            const html =
                machineType === "Total Fleet"
                    ? build_grouped_total_fleet_html(
                        rows,
                        resolvedSite
                    )
                    : build_machine_rows_html(
                        machineType,
                        resolvedSite,
                        rows
                    );

            show_machine_dialog(
                machineType === "Total Fleet"
                    ? __("Machine Plant List - Total Fleet")
                    : __(
                        "Machine Plant List - {0}",
                        [machineType]
                    ),
                machineType,
                resolvedSite,
                html
            );
        },

        error(error) {
            console.error(error);

            frappe.msgprint(
                __("Could not load the machine plant list.")
            );
        },
    });
}
// MAIN MACHINE VIEW PLANT LIST - END
