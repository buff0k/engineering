function format_dashboard_hours(value) {
    const total_minutes = Math.round(
        Number(value || 0) * 60
    );

    const hours = Math.floor(
        total_minutes / 60
    );

    const minutes = total_minutes % 60;

    if (hours > 0 && minutes > 0) {
        return `${hours}H ${minutes}Min`;
    }

    if (hours > 0) {
        return `${hours}H`;
    }

    return `${minutes}Min`;
}



frappe.pages["daily-availability-dashboard"].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __("Daily Availability Dashboard"),
        single_column: true
    });

    wrapper.daily_availability_dashboard = new DailyAvailabilityDashboardPage(wrapper, page);
};

class DailyAvailabilityDashboardPage {
    constructor(wrapper, page) {
        this.wrapper = $(wrapper);
        this.page = page;
        this.method = "engineering.engineering.page.daily_availability_dashboard.daily_availability_dashboard.get_dashboard_html";
        this.pdf_method = "engineering.engineering.page.daily_availability_dashboard.daily_availability_dashboard.download_dashboard_pdf";
        this.downtime_method = "engineering.engineering.page.daily_availability_dashboard.daily_availability_dashboard.get_machine_downtime_details";
        this.loading = false;
        this.initializing = true;
        this.last_site_storage_key = `daily_availability_dashboard_last_site:${frappe.session.user || "Guest"}`;
        this.make();
    }

    async make() {
        this.add_mobile_styles();
        this.make_filters();
        this.make_body();
        this.make_buttons();
        await this.set_defaults();
    }

    add_mobile_styles() {
        if ($("#daily-availability-mobile-styles").length) {
            return;
        }

        $("head").append(`
            <style id="daily-availability-mobile-styles">
                .daily-availability-clickable-bar {
                    cursor: pointer;
                }

                .daily-availability-clickable-bar:hover {
                    filter: brightness(0.9);
                }

                .daily-downtime-list {
                    display: grid;
                    grid-template-columns: repeat(2, minmax(260px, 1fr));
                    gap: 10px;
                    max-height: 60vh;
                    overflow-y: auto;
                    padding: 4px;
                }

                .daily-downtime-item {
                    position: relative;
                    border: 1px solid #d1d5db;
                    border-radius: 10px;
                    padding: 12px;
                    background: #ffffff;
                    cursor: pointer;
                }

                .daily-downtime-item:hover,
                .daily-downtime-item.is-open {
                    border-color: #1d4ed8;
                    background: #eff6ff;
                }

                .daily-downtime-summary {
                    font-size: 13px;
                    line-height: 1.5;
                }

                .daily-downtime-summary strong {
                    color: #111827;
                }

                .daily-downtime-details {
                    display: none;
                    margin-top: 10px;
                    padding-top: 10px;
                    border-top: 1px solid #bfdbfe;
                    font-size: 12px;
                    line-height: 1.6;
                    color: #374151;
                }

                .daily-downtime-item:hover .daily-downtime-details,
                .daily-downtime-item.is-open .daily-downtime-details {
                    display: block;
                }

                @media (max-width: 768px) {
                    .daily-availability-dashboard-wrapper .page-form {
                        display: grid !important;
                        grid-template-columns: 1fr !important;
                        gap: 8px !important;
                    }

                    .daily-availability-dashboard-wrapper .page-form .form-group {
                        width: 100% !important;
                        min-width: 0 !important;
                    }

                    .daily-availability-page {
                        padding: 0 !important;
                    }

                    .daily-availability-page .isd-metrics {
                        display: grid !important;
                        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
                        gap: 8px !important;
                    }

                    .daily-availability-page .isd-metric {
                        width: 100% !important;
                        min-width: 0 !important;
                        margin: 0 !important;
                    }

                    .daily-availability-page .isd-contentrow {
                        display: block !important;
                    }

                    .daily-availability-page .isd-chart-stack {
                        width: 100% !important;
                        overflow-x: auto !important;
                        -webkit-overflow-scrolling: touch;
                    }

                    .daily-availability-page .isd-chart-section {
                        overflow-x: auto !important;
                    }

                    .daily-availability-page .isd-side {
                        width: 100% !important;
                        padding: 10px !important;
                    }

                    .daily-downtime-list {
                        grid-template-columns: 1fr;
                        max-height: 65vh;
                    }
                }
            </style>
        `);

        this.wrapper.addClass("daily-availability-dashboard-wrapper");
    }

    make_filters() {
        this.start_date = this.page.add_field({
            fieldname: "start_date",
            label: __("Start Date"),
            fieldtype: "Date",
            reqd: 1,
            change: () => this.load_dashboard()
        });

        this.end_date = this.page.add_field({
            fieldname: "end_date",
            label: __("End Date"),
            fieldtype: "Date",
            reqd: 1,
            change: () => this.load_dashboard()
        });

        this.location = this.page.add_field({
            fieldname: "location",
            label: __("Site"),
            fieldtype: "Link",
            options: "Location",
            reqd: 1,
            change: () => {
                if (this.initializing) {
                    return;
                }

                this.set_production_dates_from_site();
            }
        });

        this.summary_type = this.page.add_field({
            fieldname: "summary_type",
            label: __("Summary Type"),
            fieldtype: "Select",
            options: [
                "Daily Summary",
                "Average Per Machine",
                "Weekly Summary",
                "Monthly Summary"
            ].join("\n"),
            default: "Average Per Machine",
            reqd: 1,
            change: () => this.load_dashboard()
        });

        this.machine_scope = this.page.add_field({
            fieldname: "machine_scope",
            label: __("Machine Filter"),
            fieldtype: "Select",
            options: [
                "Production Machines",
                "Swing/Spare Machines",
                "Production + Swing/Spare Machines"
            ].join("\n"),
            default: "Production + Swing/Spare Machines",
            reqd: 1,
            change: () => this.load_dashboard()
        });

        this.au_target_filter = this.page.add_field({
            fieldname: "au_target_filter",
            label: __("A & U Target"),
            fieldtype: "Select",
            options: [
                "100% A & U",
                "85% A & U"
            ].join("\n"),
            default: "85% A & U",
            reqd: 1,
            change: () => this.load_dashboard()
        });


    }

    make_body() {
        this.body = $(`
            <div class="daily-availability-page eng-dashboard eng-dashboard--daily-availability">
                <div class="daily-availability-loading text-muted" style="display:none; padding: 12px 0;">
                    Loading dashboard...
                </div>
                <div class="daily-availability-error" style="display:none;"></div>
                <div class="daily-availability-dashboard-body"></div>
            </div>
        `).appendTo(this.page.main);
    }

    make_buttons() {
        this.page.set_primary_action(__("Refresh"), () => {
            this.load_dashboard();
        });

        this.page.add_inner_button(__("Download PDF"), () => {
            this.download_pdf();
        });
    }

    async set_defaults() {
        this.initializing = true;

        await this.start_date.set_value(null);
        await this.end_date.set_value(null);
        await this.summary_type.set_value("Average Per Machine");
        await this.machine_scope.set_value(
            "Production + Swing/Spare Machines"
        );
        await this.au_target_filter.set_value("85% A & U");

        let saved_site = "";

        try {
            saved_site = localStorage.getItem(
                this.last_site_storage_key
            ) || "";
        } catch (error) {
            saved_site = "";
        }

        if (saved_site) {
            await this.location.set_value(saved_site);
            await this.set_production_dates_from_site();
        } else {
            this.body.find(
                ".daily-availability-dashboard-body"
            ).html(`
                <div class="frappe-card" style="padding: 18px;">
                    Please select Site. The latest Monthly Production Planning dates will load automatically.
                </div>
            `);
        }

        this.initializing = false;

        if (
            this.location.get_value() &&
            this.start_date.get_value() &&
            this.end_date.get_value()
        ) {
            this.load_dashboard();
        }
    }

    async set_production_dates_from_site() {
        const site = this.location.get_value();

        await this.start_date.set_value(null);
        await this.end_date.set_value(null);

        if (!site) {
            return;
        }

        try {
            localStorage.setItem(
                this.last_site_storage_key,
                site
            );
        } catch (error) {
            // Continue even if browser storage is unavailable.
        }

        const records = await frappe.db.get_list(
            "Monthly Production Planning",
            {
                filters: {
                    location: site
                },
                fields: [
                    "name",
                    "location",
                    "prod_month_start_date",
                    "prod_month_end_date"
                ],
                order_by: "prod_month_end_date desc",
                limit: 1
            }
        );

        if (!records.length) {
            frappe.msgprint(
                __("No Monthly Production Planning record was found for {0}.", [site])
            );
            return;
        }

        const production_plan = records[0];

        if (
            !production_plan.prod_month_start_date ||
            !production_plan.prod_month_end_date
        ) {
            frappe.msgprint(
                __("The latest Monthly Production Planning record does not have both production dates.")
            );
            return;
        }

        await this.start_date.set_value(
            production_plan.prod_month_start_date
        );

        await this.end_date.set_value(
            production_plan.prod_month_end_date
        );

        if (!this.initializing) {
            this.load_dashboard();
        }
    }

    get_values() {
        return {
            start_date: this.start_date.get_value(),
            end_date: this.end_date.get_value(),
            location: this.location.get_value(),
            site: this.location.get_value(),
            summary_type: this.summary_type.get_value() || "Average Per Machine",
            machine_scope: this.machine_scope.get_value() || "Production + Swing/Spare Machines",
            au_target_filter: this.au_target_filter.get_value() || "85% A & U"
        };
    }

    validate(values) {
        if (!values.start_date || !values.end_date || !values.location) {
            this.body.find(".daily-availability-dashboard-body").html(`
                <div class="frappe-card" style="padding: 18px;">
                    Please select Start Date, End Date and Site.
                </div>
            `);
            return false;
        }

        return true;
    }

    load_dashboard() {
        if (this.initializing) {
            return;
        }

        const values = this.get_values();

        if (!this.validate(values)) {
            return;
        }

        if (this.loading) {
            return;
        }

        this.loading = true;

        this.body.find(".daily-availability-error").hide().empty();
        this.body.find(".daily-availability-loading").show();

        frappe.call({
            method: this.method,
            args: values,
            freeze: false,
            callback: (r) => {
                this.loading = false;
                this.body.find(".daily-availability-loading").hide();

                const html = r.message || "";

                if (!html) {
                    this.body.find(".daily-availability-dashboard-body").html(`
                        <div class="frappe-card" style="padding: 18px;">
                            No dashboard data returned.
                        </div>
                    `);
                    return;
                }

                this.body.find(".daily-availability-dashboard-body").html(html);
                this.bind_dashboard_actions();
            },
            error: () => {
                this.loading = false;
                this.body.find(".daily-availability-loading").hide();

                this.body.find(".daily-availability-error")
                    .show()
                    .html(`
                        <div class="frappe-card" style="padding: 18px; color: #b42318;">
                            Could not load Daily Availability Dashboard. Please check the filters and try again.
                        </div>
                    `);
            }
        });
    }

    bind_dashboard_actions() {
        this.body
            .off("click.daily_availability_bar", ".daily-availability-clickable-bar")
            .on(
                "click.daily_availability_bar",
                ".daily-availability-clickable-bar",
                (event) => {
                    const machine = $(event.currentTarget).data("machine") || "";

                    if (machine) {
                        this.open_machine_downtime_popup(machine);
                    }
                }
            );
    }

    open_machine_downtime_popup(machine) {
        const values = this.get_values();

        frappe.call({
            method: this.downtime_method,
            args: {
                machine: machine,
                location: values.location,
                start_date: values.start_date,
                end_date: values.end_date,
                au_target_filter: values.au_target_filter
            },
            freeze: true,
            freeze_message: __("Loading downtime details..."),
            callback: (r) => {
                const response = r.message || {};
                const rows = response.rows || [];

                const dialog = new frappe.ui.Dialog({
                    title: __("{0} Downtime Details", [machine]),
                    size: "extra-large"
                });

                let html = `
                    <div style="margin-bottom:12px;font-size:13px;color:#475569;">
                        ${frappe.utils.escape_html(values.location || "")}
                        |
                        ${frappe.utils.escape_html(values.start_date || "")}
                        to
                        ${frappe.utils.escape_html(values.end_date || "")}
                    </div>
                `;

                if (!rows.length) {
                    html += `
                        <div class="frappe-card" style="padding:16px;">
                            No downtime records found for this machine.
                        </div>
                    `;
                } else {
                    html += `<div class="daily-downtime-list">`;

                    rows.forEach((row) => {
                        const status = frappe.utils.escape_html(row.status || "");
                        const reason = frappe.utils.escape_html(row.reason || "");
                        const resolution = frappe.utils.escape_html(row.resolution || "");
                        const start = frappe.utils.escape_html(row.start || "");
                        const resolved = frappe.utils.escape_html(
                            row.resolved || "Still Open"
                        );
                        const hours = format_dashboard_hours(
                            row.hours || 0
                        );

                        const downtime_type = frappe.utils.escape_html(
                            row.downtime_type || ""
                        );

                        const calculation = row.calculation || {};

                        const shift = frappe.utils.escape_html(
                            calculation.shift || ""
                        );

                        const required_hours_value = Number(
                            calculation.required_hours || 9
                        );

                        const available_hours_value = Number(
                            calculation.available_hours || 0
                        );

                        const raw_downtime_value = Number(
                            calculation.raw_downtime || 0
                        );

                        const startup_excluded_value = Number(
                            calculation.startup_excluded || 0
                        );

                        const fatigue_excluded_value = Number(
                            calculation.fatigue_excluded || 0
                        );

                        const total_excluded_value = Number(
                            calculation.total_excluded || 0
                        );

                        const total_downtime_value = Number(
                            calculation.total_downtime || 0
                        );

                        const required_hours = format_dashboard_hours(
                            required_hours_value
                        );

                        const available_hours = format_dashboard_hours(
                            available_hours_value
                        );

                        const raw_downtime = format_dashboard_hours(
                            raw_downtime_value
                        );

                        const startup_excluded = format_dashboard_hours(
                            startup_excluded_value
                        );

                        const fatigue_excluded = format_dashboard_hours(
                            fatigue_excluded_value
                        );

                        const total_excluded = format_dashboard_hours(
                            total_excluded_value
                        );

                        const total_downtime = format_dashboard_hours(
                            total_downtime_value
                        );

                        const actual_availability = Number(
                            calculation.actual_availability || 0
                        ).toFixed(1);

                        const displayed_availability = Number(
                            calculation.displayed_availability || 0
                        ).toFixed(1);

                        const target_label = frappe.utils.escape_html(
                            calculation.target_label || "100% A & U"
                        );

                        html += `
                            <div class="daily-downtime-item">
                                <div class="daily-downtime-summary">
                                    <strong>${status}</strong><br>
                                    ${reason || "No reason captured"}<br>
                                    <strong>${hours}</strong>
                                </div>

                                <div class="daily-downtime-details">
                                    <div style="
                                        display:grid;
                                        grid-template-columns:minmax(260px, 1fr) minmax(240px, 0.8fr);
                                        gap:20px;
                                    ">
                                        <div>
                                            <div><strong>Type:</strong> ${downtime_type}</div>
                                            <div><strong>Start:</strong> ${start}</div>
                                            <div><strong>Back in Production:</strong> ${resolved}</div>
                                            <div><strong>Reason:</strong> ${reason}</div>
                                            <div><strong>Resolution:</strong> ${resolution || "Not captured"}</div>
                                        </div>

                                        <div style="
                                            border-left:1px solid #bfdbfe;
                                            padding-left:18px;
                                        ">
                                            <div style="
                                                font-weight:800;
                                                margin-bottom:5px;
                                                color:#111827;
                                            ">
                                                Availability Calculation
                                            </div>

                                            <div>
                                                <strong>Shift:</strong>
                                                ${shift}
                                            </div>

                                            <div>
                                                <strong>Required Hours:</strong>
                                                ${required_hours}
                                            </div>

                                            <div>
                                                <strong>Raw Downtime:</strong>
                                                ${raw_downtime}
                                            </div>

                                            <div>
                                                <strong>Startup Excluded:</strong>
                                                ${startup_excluded}
                                            </div>

                                            <div>
                                                <strong>Fatigue Excluded:</strong>
                                                ${fatigue_excluded}
                                            </div>

                                            <div>
                                                <strong>Total Excluded:</strong>
                                                ${total_excluded}
                                            </div>

                                            <div>
                                                <strong>Counted Downtime:</strong>
                                                ${total_downtime}
                                            </div>

                                            <div>
                                                <strong>Available Hours:</strong>
                                                ${required_hours} - ${total_downtime} =
                                                ${available_hours}
                                            </div>

                                            <div style="margin-top:5px;">
                                                ${available_hours_value.toFixed(2)}
                                                ÷
                                                ${required_hours_value.toFixed(2)}
                                                × 100 =
                                                <strong>${actual_availability}%</strong>
                                            </div>

                                            <div style="margin-top:5px;">
                                                <strong>${target_label}:</strong>
                                                ${displayed_availability}%
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `;
                    });

                    html += `</div>`;
                }

                dialog.$body.html(html);

                dialog.$wrapper
                    .off("click.daily_downtime_item", ".daily-downtime-item")
                    .on(
                        "click.daily_downtime_item",
                        ".daily-downtime-item",
                        function () {
                            $(this).toggleClass("is-open");
                        }
                    );

                dialog.show();
            }
        });
    }

    download_pdf() {
        const values = this.get_values();

        values.summary_type = this.summary_type.get_value() || "Average Per Machine";
        values.machine_scope = this.machine_scope.get_value() || "Production + Swing/Spare Machines";
        values.au_target_filter = this.au_target_filter.get_value() || "85% A & U";
        values.location = this.location.get_value();
        values.site = this.location.get_value();

        if (!this.validate(values)) {
            return;
        }

        const query = $.param({
            start_date: values.start_date,
            end_date: values.end_date,
            location: values.location,
            site: values.site,
            summary_type: values.summary_type,
            machine_scope: values.machine_scope,
            au_target_filter: values.au_target_filter
        });

        const url = "/api/method/" + this.pdf_method + "?" + query;

        window.open(url, "_blank");
    }
}