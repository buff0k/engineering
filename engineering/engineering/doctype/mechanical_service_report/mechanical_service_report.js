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

        // Handle Service vs Breakdown visibility/requirements
        toggle_service_interval(frm);
    },

    onload(frm) {
        // Ensure correct state when form loads
        toggle_service_interval(frm);
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

        // Clear asset-related fields when site changes
        frm.set_value("asset", "");
        frm.set_value("model", "");
        frm.set_value("asset_category", "");
        frm.set_value("last_smr_preuse", null);
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
        calculate_total_hours(frm);

    },

    // when Start Time changes, update total_time
    start_time(frm) {
        calculate_total_hours(frm);
    },

    // when End Time changes, update total_time
    end_time(frm) {
        calculate_total_hours(frm);
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

// Helper to calculate total_time from start_time and end_time
function calculate_total_hours(frm) {
    if (!frm.doc.start_time || !frm.doc.end_time) {
        frm.set_value("total_time", 0);
        return;
    }

    // start_time and end_time are strings like "08:30:00" or "08:30"
    function time_to_seconds(t) {
        const parts = t.split(":").map(Number);
        const h = parts[0] || 0;
        const m = parts[1] || 0;
        const s = parts[2] || 0;
        return (h * 3600) + (m * 60) + s;
    }

    let start_sec = time_to_seconds(frm.doc.start_time);
    let end_sec = time_to_seconds(frm.doc.end_time);

    // If end is smaller, assume it went past midnight
    if (end_sec < start_sec) {
        end_sec += 24 * 3600;
    }

    let diff_seconds = end_sec - start_sec;

    // Optional: round to nearest minute so it looks clean (no odd seconds)
    diff_seconds = Math.round(diff_seconds / 60) * 60;

    // Duration field expects seconds
    frm.set_value("total_time", diff_seconds);
}
