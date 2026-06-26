frappe.ui.form.on("WhatsApp Breakdown Message Log", {
    refresh(frm) {
        if (frm.doc.__islocal) {
            return;
        }

        frm.add_custom_button("Create/Update Breakdown", function () {
            frappe.call({
                method: "engineering.engineering.doctype.whatsapp_breakdown_message_log.whatsapp_breakdown_message_log.create_or_update_breakdown",
                args: {
                    log_name: frm.doc.name
                },
                freeze: true,
                freeze_message: "Creating/updating breakdown...",
                callback: function (r) {
                    if (r.message) {
                        frappe.msgprint(
                            "Done: " + r.message.status + "<br>Breakdown: " + r.message.breakdown
                        );
                        frm.reload_doc();
                    }
                }
            });
        }).addClass("btn-primary");
    }
});
