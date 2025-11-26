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
        }
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
