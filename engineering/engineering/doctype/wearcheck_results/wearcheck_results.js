// Copyright (c) 2026, BuFf0k and contributors
// For license information, please see license.txt

frappe.ui.form.on("WearCheck Results", {
    refresh(frm) {
        if (frm.doc.__islocal) {
            return;
        }

        if (frm.doc.import_failed || frm.doc.import_status === "Failed") {
            frm.add_custom_button(__("Retry Import"), () => {
                frappe.confirm(
                    __("Retry this WearCheck import against the current API Wearcheck Settings mappings?"),
                    () => {
                        frappe.call({
                            method: "engineering.controllers.importer.retry_import",
                            args: {
                                name: frm.doc.name,
                            },
                            freeze: true,
                            freeze_message: __("Retrying WearCheck import..."),
                            callback(r) {
                                if (!r.message) {
                                    return;
                                }

                                const msg = r.message;

                                if (msg.import_failed) {
                                    frappe.msgprint({
                                        title: __("Retry Failed"),
                                        indicator: "red",
                                        message: msg.import_error || __("The record is still failing import."),
                                    });
                                } else {
                                    frappe.msgprint({
                                        title: __("Retry Successful"),
                                        indicator: "green",
                                        message: __("WearCheck result imported successfully."),
                                    });
                                }

                                frm.reload_doc();
                            },
                        });
                    }
                );
            }, __("Actions"));
        }
    },
});