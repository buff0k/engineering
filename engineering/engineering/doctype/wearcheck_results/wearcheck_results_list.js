// Copyright (c) 2026, BuFf0k and contributors
// For license information, please see license.txt

frappe.listview_settings["WearCheck Results"] = {
    onload(listview) {
        listview.page.add_inner_button(__("Retry Failed Imports"), () => {
            frappe.confirm(
                __("Retry all failed WearCheck imports against the current API Wearcheck Settings mappings?"),
                () => {
                    frappe.call({
                        method: "engineering.controllers.importer.enqueue_retry_failed_imports",
                        freeze: true,
                        freeze_message: __("Queuing failed WearCheck imports..."),
                        callback(r) {
                            if (!r.message || !r.message.ok) {
                                return;
                            }

                            frappe.msgprint({
                                title: __("Retry Queued"),
                                indicator: "blue",
                                message: __("Failed WearCheck imports have been queued. Refresh the list after the background job completes."),
                            });

                            listview.refresh();
                        },
                    });
                }
            );
        });
    },
};