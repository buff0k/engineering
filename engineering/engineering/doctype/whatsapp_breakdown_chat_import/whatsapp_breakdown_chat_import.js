frappe.ui.form.on("WhatsApp Breakdown Chat Import", {
    refresh(frm) {
        if (frm.doc.__islocal) {
            return;
        }

        frm.add_custom_button("Import WhatsApp Chat", function () {
            frappe.confirm(
                "This will create WhatsApp Breakdown Message Log records from the attached chat file. Continue?",
                function () {
                    frappe.call({
                        method: "engineering.engineering.doctype.whatsapp_breakdown_chat_import.whatsapp_breakdown_chat_import.import_chat",
                        args: {
                            import_name: frm.doc.name
                        },
                        freeze: true,
                        freeze_message: "Importing WhatsApp chat...",
                        callback: function (r) {
                            if (r.message) {
                                frappe.msgprint(
                                    "Import completed<br>" +
                                    "Total Messages Found: " + r.message.total_messages_found + "<br>" +
                                    "Logs Created: " + r.message.logs_created + "<br>" +
                                    "Duplicates Skipped: " + r.message.duplicates_skipped + "<br>" +
                                    "Ignored Messages: " + r.message.ignored_messages + "<br>" +
                                    "Needs Review: " + r.message.needs_review_messages
                                );
                                frm.reload_doc();
                            }
                        }
                    });
                }
            );
        }).addClass("btn-primary");
    }
});
