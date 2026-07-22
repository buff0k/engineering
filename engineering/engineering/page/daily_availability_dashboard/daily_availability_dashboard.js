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
        this.make();
    }

    make() {
        this.add_mobile_styles();
        this.make_filters();
        this.make_body();
        this.make_buttons();
        this.set_defaults();
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
            change: () => this.set_production_dates_from_site()
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

    set_defaults() {
        this.start_date.set_value(null);
        this.end_date.set_value(null);
        this.summary_type.set_value("Average Per Machine");
        this.machine_scope.set_value("Production + Swing/Spare Machines");
        this.au_target_filter.set_value("85% A & U");

        this.body.find(".daily-availability-dashboard-body").html(`
            <div class="frappe-card" style="padding: 18px;">
                Please select Site. The saved production dates will load automatically.
            </div>
        `);
    }

    async set_production_dates_from_site() {
        const site = this.location.get_value();

        if (!site) {
            return;
        }

        const records = await frappe.db.get_list("Define Production date", {
            filters: {
                site: site
            },
            fields: [
                "name",
                "storage"
            ],
            order_by: "modified desc",
            limit: 1
        });

        if (!records.length || !records[0].storage) {
            frappe.msgprint(
                __("No production dates have been configured for {0}.", [site])
            );
            return;
        }

        let saved_dates;

        try {
            saved_dates = JSON.parse(records[0].storage);
        } catch (error) {
            frappe.msgprint(__("The saved production dates are invalid."));
            return;
        }

        if (!saved_dates.start_date || !saved_dates.end_date) {
            frappe.msgprint(__("Both production dates must be configured."));
            return;
        }

        await this.start_date.set_value(saved_dates.start_date);
        await this.end_date.set_value(saved_dates.end_date);

        this.load_dashboard();
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
                end_date: values.end_date
            },
            freeze: true,
            freeze_message: __("Loading downtime details..."),
            callback: (r) => {
                const rows = r.message || [];
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
                        const hours = frappe.utils.escape_html(
                            String(row.hours || 0)
                        );
                        const downtime_type = frappe.utils.escape_html(
                            row.downtime_type || ""
                        );

                        html += `
                            <div class="daily-downtime-item">
                                <div class="daily-downtime-summary">
                                    <strong>${status}</strong><br>
                                    ${reason || "No reason captured"}<br>
                                    <strong>${hours} hours</strong>
                                </div>

                                <div class="daily-downtime-details">
                                    <div><strong>Type:</strong> ${downtime_type}</div>
                                    <div><strong>Start:</strong> ${start}</div>
                                    <div><strong>Back in Production:</strong> ${resolved}</div>
                                    <div><strong>Reason:</strong> ${reason}</div>
                                    <div><strong>Resolution:</strong> ${resolution || "Not captured"}</div>
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