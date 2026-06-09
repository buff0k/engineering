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
        this.loading = false;
        this.make();
    }

    make() {
        this.make_filters();
        this.make_body();
        this.make_buttons();
        this.set_defaults();
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
            change: () => this.load_dashboard()
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
            default: "Daily Summary",
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
                "Include Swing/Spare"
            ].join("\n"),
            default: "Include Swing/Spare",
            reqd: 1,
            change: () => this.load_dashboard()
        });
    }

    make_body() {
        this.body = $(`
            <div class="daily-availability-page">
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
        const today = frappe.datetime.get_today();
        const yesterday = frappe.datetime.add_days(today, -1);

        this.start_date.set_value(yesterday);
        this.end_date.set_value(yesterday);
        this.summary_type.set_value("Daily Summary");
        this.machine_scope.set_value("Include Swing/Spare");

        this.body.find(".daily-availability-dashboard-body").html(`
            <div class="frappe-card" style="padding: 18px;">
                Please select Site, then click Refresh.
            </div>
        `);
    }

    get_values() {
        return {
            start_date: this.start_date.get_value(),
            end_date: this.end_date.get_value(),
            location: this.location.get_value(),
            site: this.location.get_value(),
            summary_type: this.summary_type.get_value() || "Daily Summary",
            machine_scope: this.machine_scope.get_value() || "Include Swing/Spare"
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

                setTimeout(() => {
                    this.align_target_lines();
                }, 100);

                setTimeout(() => {
                    this.align_target_lines();
                }, 500);
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

    download_pdf() {
        const values = this.get_values();

        values.summary_type = this.summary_type.get_value() || "Daily Summary";
        values.machine_scope = this.machine_scope.get_value() || "Include Swing/Spare";
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
            machine_scope: values.machine_scope
        });

        const url = "/api/method/" + this.pdf_method + "?" + query;

        window.open(url, "_blank");
    }
}
