frappe.ui.form.on("Define Production date", {
    refresh(frm) {
        render_production_date_selector(frm);
    },

    site(frm) {
        render_production_date_selector(frm);
    },

    before_save(frm) {
        save_production_dates_to_storage(frm);
    }
});

function get_saved_production_dates(frm) {
    if (!frm.doc.storage) {
        return {
            start_date: "",
            end_date: ""
        };
    }

    try {
        const stored = JSON.parse(frm.doc.storage);

        return {
            start_date: stored.start_date || "",
            end_date: stored.end_date || ""
        };
    } catch (error) {
        return {
            start_date: "",
            end_date: ""
        };
    }
}

function save_production_dates_to_storage(frm) {
    const wrapper = frm.fields_dict.date.$wrapper;
    const start_date = wrapper.find("#production-start-date").val() || "";
    const end_date = wrapper.find("#production-end-date").val() || "";

    if (!start_date || !end_date) {
        return;
    }

    frm.set_value(
        "storage",
        JSON.stringify({
            start_date: start_date,
            end_date: end_date
        })
    );
}

function render_production_date_selector(frm) {
    const wrapper = frm.fields_dict.date.$wrapper;
    const saved_dates = get_saved_production_dates(frm);
    const site_name = frappe.utils.escape_html(frm.doc.site || "Select a site first");

    wrapper.html(`
        <div style="
            max-width: 760px;
            padding: 20px;
            border: 1px solid #d8dfe6;
            border-radius: 12px;
            background: #ffffff;
            box-shadow: 0 3px 12px rgba(0, 0, 0, 0.06);
        ">
            <div style="
                margin-bottom: 18px;
                font-size: 16px;
                font-weight: 700;
                color: #1f272e;
            ">
                Production Month Dates
            </div>

            <div style="
                margin-bottom: 16px;
                padding: 10px 12px;
                border-radius: 8px;
                background: #f3f8fc;
                font-size: 13px;
            ">
                Site: <strong>${site_name}</strong>
            </div>

            <div style="
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 16px;
            ">
                <div>
                    <label style="
                        display: block;
                        margin-bottom: 6px;
                        font-size: 12px;
                        font-weight: 700;
                    ">
                        Production Start Date
                    </label>

                    <input
                        id="production-start-date"
                        type="date"
                        class="form-control"
                        value="${saved_dates.start_date}"
                        ${frm.doc.site ? "" : "disabled"}
                    >
                </div>

                <div>
                    <label style="
                        display: block;
                        margin-bottom: 6px;
                        font-size: 12px;
                        font-weight: 700;
                    ">
                        Production End Date
                    </label>

                    <input
                        id="production-end-date"
                        type="date"
                        class="form-control"
                        value="${saved_dates.end_date}"
                        ${frm.doc.site ? "" : "disabled"}
                    >
                </div>
            </div>

            <button
                id="save-production-dates"
                type="button"
                class="btn btn-primary"
                style="margin-top: 18px;"
                ${frm.doc.site ? "" : "disabled"}
            >
                Save Production Dates
            </button>

            <div style="
                margin-top: 10px;
                font-size: 12px;
                color: #6b7280;
            ">
                These dates will become the default dashboard date filters for this site.
            </div>
        </div>
    `);

    wrapper.find("#save-production-dates").on("click", async function() {
        const start_date = wrapper.find("#production-start-date").val();
        const end_date = wrapper.find("#production-end-date").val();

        if (!start_date || !end_date) {
            frappe.msgprint(__("Select both production dates."));
            return;
        }

        if (end_date < start_date) {
            frappe.msgprint(__("The production end date cannot be before the start date."));
            return;
        }

        save_production_dates_to_storage(frm);
        await frm.save();

        frappe.show_alert({
            message: __("Production dates saved"),
            indicator: "green"
        });
    });
}