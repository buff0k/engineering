frappe.ui.form.on("WhatsApp Breakdown Chat Import", {
    refresh(frm) {
        if (frm.doc.__islocal) {
            return;
        }

        frm.add_custom_button(__("Import WhatsApp Chat"), function () {
            frappe.call({
                method: "engineering.engineering.doctype.whatsapp_breakdown_chat_import.whatsapp_breakdown_chat_import.import_chat",
                args: {
                    import_name: frm.doc.name
                },
                freeze: true,
                freeze_message: __("Importing WhatsApp chat..."),
                callback: function (r) {
                    if (r.message) {
                        frappe.msgprint(
                            __("Import completed.<br><br>Total Messages: {0}<br>Logs Created: {1}<br>Duplicates Skipped: {2}<br>Ignored Messages: {3}<br>Needs Review Messages: {4}", [
                                r.message.total_messages_found || 0,
                                r.message.logs_created || 0,
                                r.message.duplicates_skipped || 0,
                                r.message.ignored_messages || 0,
                                r.message.needs_review_messages || 0
                            ])
                        );
                    }

                    frm.reload_doc();
                }
            });
        }).addClass("btn-primary");

        frm.add_custom_button(__("Create/Update All Breakdowns"), function () {
            frappe.confirm(
                __("This will create/update Plant Breakdown or Maintenance records for all Parsed Book Down and Book Back logs linked to this import. Continue?"),
                function () {
                    frappe.call({
                        method: "engineering.engineering.doctype.whatsapp_breakdown_chat_import.whatsapp_breakdown_chat_import.create_or_update_all_breakdowns",
                        args: {
                            import_name: frm.doc.name
                        },
                        freeze: true,
                        freeze_message: __("Creating/updating breakdown records..."),
                        callback: function (r) {
                            if (r.message && r.message.message) {
                                frappe.msgprint({
                                    title: __("Bulk Breakdown Update Complete"),
                                    message: frappe.utils.escape_html(r.message.message).replace(/\n/g, "<br>"),
                                    indicator: r.message.errors ? "orange" : "green"
                                });
                            }

                            frm.reload_doc();
                        }
                    });
                }
            );
        }).addClass("btn-success");
    }
});
