// Copyright (c) 2025, BuFf0k and contributors
// For license information, please see license.txt

frappe.ui.form.on('Plant Technical Specification', {
    asset_category: function(frm) {
        if (frm.doc.asset_category) {
            frm.set_query('item_name', function() {
                return {
                    filters: {
                        'item_group': frm.doc.asset_category
                    }
                };
            });
        }
    },
    before_save: function(frm) {
        if (frm.is_dirty()) {
            frm.set_value('revision_date', frappe.datetime.now_datetime());
        }
    },
    refresh: function(frm) {
        if (frm.doc.item_name) {
            frm.trigger('populate_models_site');
        }
    },
    item_name: function(frm) {
        if (frm.doc.item_name) {
            frm.trigger('populate_models_site');
        }
    },
    populate_models_site: function(frm) {
        console.log("Fetching assets for item_name:", frm.doc.item_name);
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Asset",
                filters: {
                    "item_name": frm.doc.item_name,
                    "docstatus": 1  // Only fetch submitted documents
                },
                fields: ["asset_name", "location"]
            },
            callback: function(response) {
                console.log("Assets fetched:", response.message);
                const assets = response.message;
                const siteData = {};
                let grandTotal = 0;

                // Organize assets by location and calculate grand total
                assets.forEach(asset => {
                    if (!siteData[asset.location]) {
                        siteData[asset.location] = [];
                    }
                    siteData[asset.location].push(asset.asset_name);
                    grandTotal++;
                });

                // Build HTML content in 3 columns
                let html_content = "<table style='width:100%; table-layout: fixed;'><tr>";
                let colCount = 0;

                for (const [location, assetNames] of Object.entries(siteData)) {
                    if (colCount % 3 === 0 && colCount !== 0) {
                        html_content += "</tr><tr>"; // Start a new row every 3 sites
                    }
                    html_content += `<td style='vertical-align: top; padding: 10px;'><h4>${location}</h4><ul>`;
                    assetNames.forEach(name => {
                        html_content += `<li>${name}</li>`;
                    });
                    html_content += `</ul><p>Total ${frm.doc.item_name}'s for ${location}: ${assetNames.length}</p></td>`;
                    colCount++;
                }

                html_content += "</tr></table>";
                html_content += `<p style='text-align: right; font-weight: bold;'>Grand Total of ${frm.doc.item_name}'s: ${grandTotal}</p>`;

                console.log("Generated HTML content:", html_content);

                // Ensure wrapper exists and render HTML
                if (frm.fields_dict.models_site) {
                    frm.fields_dict.models_site.$wrapper.html(html_content);
                    frm.refresh_field("models_site");
                    console.log("HTML content rendered to models_site field");
                } else {
                    console.warn("models_site field wrapper not found.");
                }
            }
        });
    }
});
