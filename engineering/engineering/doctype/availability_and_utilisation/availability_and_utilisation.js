frappe.ui.form.on("Availability and Utilisation", {
    refresh: function(frm) {
        // Only allow System Managers to run the engine
        if (frappe.user_roles.includes("System Manager")) {
            frm.add_custom_button(__('Run Availability & Utilisation Engine'), () => {
                frappe.call({
                    method: "engineering.engineering.doctype.availability_and_utilisation.availability_and_utilisation.queue_availability_and_utilisation",
                    freeze: true,
                    freeze_message: __("Queuing Availability & Utilisation Engine..."),
                    callback: function() {
                        frappe.msgprint({
                            title: __('Process Queued'),
                            message: __('The Availability & Utilisation Engine is now running in the background. Check Error Log for updates.'),
                            indicator: 'blue'
                        });
                    }
                });
            });
        }
    }
});
