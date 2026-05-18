frappe.ui.form.on("Mechanical Service Report", {
    refresh(frm) {
        // Set dynamic filter for Asset based on selected Site
        // Only submitted Assets for selected Site will show
        set_asset_filter(frm);

        toggle_fields_until_site_selected(frm);
        toggle_new_job_field(frm);
        toggle_service_interval(frm);
        calculate_total_time_live(frm);

        // Make saved comment history read-only on the form side.
        // Server-side Python still controls the real lock.
        lock_comment_history_grid(frm);
    },

    onload(frm) {
        set_asset_filter(frm);

        toggle_fields_until_site_selected(frm);
        toggle_new_job_field(frm);
        toggle_service_interval(frm);
        calculate_total_time_live(frm);
        lock_comment_history_grid(frm);
    },

    site(frm) {
        set_asset_filter(frm);

        toggle_fields_until_site_selected(frm);
        toggle_new_job_field(frm);

        // Clear asset-related fields when site changes
        frm.set_value("asset", "");
        frm.set_value("model", "");
        frm.set_value("asset_category", "");
        frm.set_value("last_smr_preuse", null);

        if (frm.doc.site !== "Plot 22") {
            frm.set_value("is_this_a_new_job", "");
            frm.set_value("job_card_number", "");
        }
    },

    service_breakdown(frm) {
        toggle_service_interval(frm);
    },

    validate(frm) {
        // If it is a Service, service_interval must be filled
        if (frm.doc.service_breakdown === "Service" && !frm.doc.service_interval) {
            frappe.msgprint(__("Please select a Service Interval for a Service MSR."));
            frappe.validated = false;
            return;
        }

        // Make sure total_time is correct before saving
        calculate_total_time_live(frm);
    },

    after_save(frm) {
        // Server-side Python moves typed comments into Comment History
        // and clears the comment fields. Reload so the screen reflects that.
        frm.reload_doc();
    },

    start_time(frm) {
        calculate_total_time_live(frm);
    },

    end_time(frm) {
        calculate_total_time_live(frm);
    },

    asset(frm) {
        if (!frm.doc.asset) {
            frm.set_value("last_smr_preuse", null);
            return;
        }

        frappe.call({
            method: "engineering.engineering.doctype.mechanical_service_report.mechanical_service_report.get_last_preuse_hours",
            args: {
                asset: frm.doc.asset
            },
            callback: function(r) {
                if (!r.exc) {
                    if (r.message) {
                        frm.set_value("last_smr_preuse", r.message);
                    } else {
                        frm.set_value("last_smr_preuse", null);
                    }
                }
            }
        });
    },

    artisan_employee_code(frm) {
        fetch_employee_name(frm, "artisan_employee_code", "artisan_fullname");
    },

    plant_manager_forman_code(frm) {
        fetch_employee_name(frm, "plant_manager_forman_code", "plant_man_forman_name");
    }
});


function set_asset_filter(frm) {
    frm.set_query("asset", function() {
        if (frm.doc.site) {
            return {
                filters: {
                    location: frm.doc.site,
                    docstatus: 1
                }
            };
        }

        return {
            filters: {
                docstatus: 1
            }
        };
    });
}


function toggle_fields_until_site_selected(frm) {
    const site_selected = !!frm.doc.site;

    const fields_to_lock = [
        "is_this_a_new_job",
        "service_date",
        "attach",
        "plant_manager_forman_code",
        "plant_man_forman_name",
        "artisan_employee_code",
        "artisan_fullname",
        "asset",
        "model",
        "asset_category",
        "last_smr_preuse",
        "current_hours",
        "start_time",
        "end_time",
        "total_time",
        "service_breakdown",
        "service_interval",
        "description_of_breakdown",
        "spares_required_and_comments",
        "description_of_work_done",
        "job_card_number",
        "artisan",
        "plant_manager_forman1",
        "artisan1",
        "plant_manager_forman"
    ];

    fields_to_lock.forEach((fieldname) => {
        if (frm.fields_dict[fieldname]) {
            frm.set_df_property(fieldname, "read_only", site_selected ? 0 : 1);
        }
    });

    // Keep these read-only because they are fetched/calculated fields
    set_read_only_if_exists(frm, "plant_man_forman_name", 1);
    set_read_only_if_exists(frm, "artisan_fullname", 1);
    set_read_only_if_exists(frm, "model", 1);
    set_read_only_if_exists(frm, "asset_category", 1);
    set_read_only_if_exists(frm, "last_smr_preuse", 1);
    set_read_only_if_exists(frm, "total_time", 1);
}


function toggle_new_job_field(frm) {
    const show_new_job = frm.doc.site === "Plot 22";

    frm.toggle_display("is_this_a_new_job", show_new_job);
    frm.toggle_reqd("is_this_a_new_job", false);

    frm.toggle_display("job_card_number", show_new_job);
    frm.toggle_reqd("job_card_number", false);

    if (!show_new_job && frm.doc.is_this_a_new_job) {
        frm.set_value("is_this_a_new_job", "");
    }

    if (!show_new_job && frm.doc.job_card_number) {
        frm.set_value("job_card_number", "");
    }
}


function toggle_service_interval(frm) {
    const is_service = frm.doc.service_breakdown === "Service";

    frm.toggle_display("service_interval", is_service);
    frm.toggle_reqd("service_interval", is_service);

    if (!is_service && frm.doc.service_interval) {
        frm.set_value("service_interval", null);
    }
}


function calculate_total_time_live(frm) {
    if (!frm.doc.start_time || !frm.doc.end_time) {
        frm.set_value("total_time", 0);
        return;
    }

    const start = frappe.datetime.str_to_obj(frm.doc.start_time);
    const end = frappe.datetime.str_to_obj(frm.doc.end_time);

    let diff_seconds = (end - start) / 1000;

    if (diff_seconds < 0) {
        diff_seconds = 0;
    }

    frm.set_value("total_time", Math.floor(diff_seconds));
}


function fetch_employee_name(frm, employee_field, name_field) {
    const employee = frm.doc[employee_field];

    if (!employee) {
        frm.set_value(name_field, "");
        return;
    }

    frappe.db.get_value("Employee", employee, "employee_name")
        .then((r) => {
            if (r && r.message && r.message.employee_name) {
                frm.set_value(name_field, r.message.employee_name);
            }
        });
}


function lock_comment_history_grid(frm) {
    if (!frm.fields_dict.comment_history) {
        return;
    }

    const grid = frm.fields_dict.comment_history.grid;

    grid.cannot_add_rows = true;
    grid.cannot_delete_rows = true;

    grid.update_docfield_property("comment_from", "read_only", 1);
    grid.update_docfield_property("comment", "read_only", 1);
    grid.update_docfield_property("commented_by", "read_only", 1);
    grid.update_docfield_property("commented_on", "read_only", 1);

    grid.refresh();
}


function set_read_only_if_exists(frm, fieldname, value) {
    if (frm.fields_dict[fieldname]) {
        frm.set_df_property(fieldname, "read_only", value);
    }
}