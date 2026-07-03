// Copyright (c) 2026, Isambane Mining (Pty) Ltd
// For license information, please see license.txt

frappe.ui.form.on("Hourly Downtime Summary", {
    refresh(frm) {
        frm.set_df_property("summary_message", "read_only", 1);
        frm.set_df_property("channel_id", "read_only", 1);
        frm.set_df_property("sent_to_raven", "read_only", 1);

        if (!frm.is_new() && frm.doc.summary_message) {
            frm.add_custom_button(__("Copy Summary Message"), function () {
                frappe.utils.copy_to_clipboard(frm.doc.summary_message);

                frappe.show_alert({
                    message: __("Summary copied"),
                    indicator: "green"
                });
            });
        }
    }
});