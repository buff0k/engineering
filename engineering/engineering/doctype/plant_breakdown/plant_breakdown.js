frappe.ui.form.on('Plant Breakdown', {
    location: function (frm) {
        if (frm.doc.location) {
            // Fetch submitted assets based on the selected location
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Asset",
                    filters: {
                        location: frm.doc.location,
                        docstatus: 1, // Include only submitted documents
                    },
                    fields: ["asset_name"], // Fetch the asset_name field
                    limit_page_length: 100, // Optional: Limit the number of assets fetched
                },
                callback: function (response) {
                    if (response.message) {
                        // Populate asset_name select field with fetched asset names
                        let options = response.message.map(asset => asset.asset_name);

                        // Retain existing value if present in fetched options
                        let current_value = frm.doc.asset_name;
                        frm.set_df_property("asset_name", "options", options);
                        frm.refresh_field("asset_name");

                        if (current_value && options.includes(current_value)) {
                            frm.set_value("asset_name", current_value); // Restore value
                        } else {
                            frm.set_value("asset_name", null); // Clear invalid value
                        }
                    }
                },
                error: function () {
                    frappe.msgprint({
                        title: __("Error"),
                        indicator: "red",
                        message: __("Failed to fetch submitted assets for the selected location."),
                    });
                },
            });
        } else {
            // Clear asset_name options if location is not set
            frm.set_df_property("asset_name", "options", []);
            frm.refresh_field("asset_name");
            frm.set_value("asset_name", null); // Clear the value
        }
    },

    refresh: function (frm) {
        if (frm.doc.location) {
            // Re-populate asset_name options on form reload
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Asset",
                    filters: {
                        location: frm.doc.location,
                        docstatus: 1, // Include only submitted documents
                    },
                    fields: ["asset_name"], // Fetch the asset_name field
                    limit_page_length: 100, // Optional: Limit the number of assets fetched
                },
                callback: function (response) {
                    if (response.message) {
                        let options = response.message.map(asset => asset.asset_name);

                        // Restore options and reselect saved value
                        frm.set_df_property("asset_name", "options", options);
                        frm.refresh_field("asset_name");

                        if (frm.doc.asset_name && options.includes(frm.doc.asset_name)) {
                            frm.set_value("asset_name", frm.doc.asset_name);
                        } else {
                            frm.set_value("asset_name", null); // Clear invalid value
                        }
                    }
                },
            });
        }
    },
});

