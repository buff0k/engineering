// Copyright (c) 2024, Isambane Mining (Pty) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Availability and Utilisation", {
    avail_util_engine: function(frm) {
        frappe.call({
            method: "engineering.engineering.doctype.availability_and_utilisation.availability_and_utilisation.create_availability_and_utilisation",
            callback: function(response) {
                if (response.message) {
                    frappe.msgprint({
                        title: __('Documents Created'),
                        message: __('Created Availability and Utilisation records: ') + response.message.join(', '),
                        indicator: 'green'
                    });
                    frm.reload_doc();  // Reload form to reflect new records if necessary
                }
            }
        });
    }
});