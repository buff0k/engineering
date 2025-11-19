console.log("✅ AU Control Log JS loaded successfully!");

frappe.ui.form.on("AU Control Log", {
    refresh(frm) {

        // 🚀 Run Now (synchronous)
        if (frm.fields_dict.run_engine) {
            frm.fields_dict.run_engine.$input.on("click", function () {
                frappe.call({
                    method: "run_availability_engine",
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: "Running Availability & Utilisation Engine...",
                    callback: function (r) {
                        if (!r.exc) {
                            frappe.show_alert({
                                message: __("✅ Engine completed successfully!"),
                                indicator: "green",
                            });
                            frm.reload_doc();
                        } else {
                            frappe.show_alert({
                                message: __("❌ Engine failed — check logs."),
                                indicator: "red",
                            });
                        }
                    },
                });
            });
        }

        // 🕒 Run in Background (async)
        if (frm.fields_dict.run_engine_background) {
            frm.fields_dict.run_engine_background.$input.on("click", function () {
                frappe.call({
                    method: "engineering.engineering.doctype.au_control_log.au_control_log.run_availability_engine_background",
                    args: { doc: frm.doc },
                    freeze: true,
                    freeze_message: "Queuing background job...",
                    callback: function (r) {
                        if (!r.exc) {
                            frappe.show_alert({
                                message: __("⏳ Engine has been queued in background."),
                                indicator: "blue",
                            });
                            frm.reload_doc();
                        } else {
                            frappe.show_alert({
                                message: __("❌ Failed to queue background job."),
                                indicator: "red",
                            });
                        }
                    },
                });
            });
        }
    },
});
