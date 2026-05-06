frappe.ui.form.on("Mechanical Service Report", {
    refresh(frm) {
        // Set dynamic filter for Asset based on selected Site
        frm.set_query("asset", function() {
            if (frm.doc.site) {
                return {
                    filters: {
                        location: frm.doc.site
                    }
                };
            }
        });

        toggle_fields_until_site_selected(frm);
        toggle_new_job_field(frm);

        // Handle Service vs Breakdown visibility/requirements
        toggle_service_interval(frm);
        calculate_total_time_live(frm);
    },

    onload(frm) {
        // Ensure correct state when form loads
        toggle_fields_until_site_selected(frm);
        toggle_new_job_field(frm);
        toggle_service_interval(frm);
        calculate_total_time_live(frm);
    },

    site(frm) {
        // Refresh the asset query when site changes
        frm.set_query("asset", function() {
            if (frm.doc.site) {
                return {
                    filters: {
                        location: frm.doc.site
                    }
                };
            }
        });

        toggle_fields_until_site_selected(frm);
        toggle_new_job_field(frm);

        // Clear asset-related fields when site changes
        frm.set_value("asset", "");
        frm.set_value("model", "");
        frm.set_value("asset_category", "");
        frm.set_value("last_smr_preuse", null);

        if (frm.doc.site !== "Plot 22") {
            frm.set_value("is_this_a_new_job", "");
        }
    },

    service_breakdown(frm) {
        // When Service / Breakdown is changed
        toggle_service_interval(frm);
    },

    validate(frm) {
        // If it's a Service, service_interval must be filled
        if (frm.doc.service_breakdown === "Service" && !frm.doc.service_interval) {
            frappe.msgprint(__('Please select a Service Interval for a Service MSR.'));
            frappe.validated = false;
            return;
        }

        // Make sure total_time is always correct before saving
        

    },

    start_time(frm) {
        calculate_total_time_live(frm);
    },



    plant_breakdown_number(frm) {
        calculate_total_time_unavailable_live(frm);
    },

    end_time(frm) {
        calculate_total_time_live(frm);
        calculate_total_time_unavailable_live(frm);
    },

    asset(frm) {
        // When Fleet Number is chosen, pull last Pre-Use engine hours
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
                        // No previous pre-use record found for this asset
                        frm.set_value("last_smr_preuse", null);
                    }
                }
            }
        });
    }
});





function toggle_fields_until_site_selected(frm) {
    const site_selected = !!frm.doc.site;

    const fields_to_lock = [
        "is_this_a_new_job",
        "service_date",
        "attach",
        "plant_manager_code",
        "artisan_employee_code",
        "asset",
        "current_hours",
        "plant_breakdown_number",
        "start_time",
        "end_time",
        "service_breakdown",
        "service_interval",
        "description_of_breakdown",
        "spares_required_and_comments",
        "description_of_work_done",
        "job_card_number",
        "mechanic",
        "manager_foreman"
    ];

    fields_to_lock.forEach((fieldname) => {
        frm.set_df_property(fieldname, "read_only", site_selected ? 0 : 1);
    });
}

function toggle_new_job_field(frm) {
    const show_new_job = frm.doc.site === "Plot 22";

    frm.toggle_display("is_this_a_new_job", show_new_job);
    frm.toggle_reqd("is_this_a_new_job", show_new_job);

    frm.toggle_display("job_card_number", show_new_job);
    frm.toggle_reqd("job_card_number", show_new_job);

    if (!show_new_job && frm.doc.is_this_a_new_job) {
        frm.set_value("is_this_a_new_job", "");
    }

    if (!show_new_job && frm.doc.job_card_number) {
        frm.set_value("job_card_number", "");
    }
}






// Helper to control Service Interval field
function toggle_service_interval(frm) {
    const is_service = frm.doc.service_breakdown === "Service";

    // Show/hide the field
    frm.toggle_display('service_interval', is_service);

    // Make required / not required
    frm.toggle_reqd('service_interval', is_service);

    // Clear value when not a Service
    if (!is_service && frm.doc.service_interval) {
        frm.set_value('service_interval', null);
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

function calculate_total_time_unavailable_live(frm) {
    if (!frm.doc.plant_breakdown_number || !frm.doc.end_time) {
        frm.set_value("total_time_unavailable", 0);
        return;
    }

    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Plant Breakdown or Maintenance",
            name: frm.doc.plant_breakdown_number,
            fieldname: "breakdown_start_datetime"
        },
        callback: function(r) {
            const breakdown_start = r.message && r.message.breakdown_start_datetime;

            if (!breakdown_start) {
                frm.set_value("total_time_unavailable", 0);
                return;
            }

            const end = frappe.datetime.str_to_obj(frm.doc.end_time);
            const start = frappe.datetime.str_to_obj(breakdown_start);



            let diff_seconds = (end - start) / 1000;
            if (diff_seconds < 0) {
                frappe.msgprint("Breakdown Start Date/Time is AFTER MSR End Time. Fix breakdown_start_datetime or MSR end_time.");
                diff_seconds = 0;
            }

            frm.set_value("total_time_unavailable", Math.floor(diff_seconds));
        }
    });
}
