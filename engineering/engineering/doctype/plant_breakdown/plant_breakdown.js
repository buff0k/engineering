// Copyright (c) 2024, Isambane Mining (Pty) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Plant Breakdown', {
    before_save: function(frm) {
        console.log("Running before_save function...");

        // Prevent recursive confirmation prompts by using a custom flag
        if (frm.skip_confirmation) {
            console.log("Skipping confirmation as flag is set.");
            frm.skip_confirmation = false; // Reset flag for future saves
            return; // Allow save to proceed without further checks
        }

        // Initially prevent saving
        frappe.validated = false;

        // Fields to track for changes
        const fieldsToTrack = [
            'location', 'asset_name', 'item_name', 'asset_category', 
            'breakdown_start_date', 'breakdown_start_time', 
            'breakdown_status', 'breakdown_status_description', 
            'hours_breakdown_start', 'last_pre_use_prod_shift_date', 
            'last_pre_use_prod_shift', 'last_pre_use_hours_start', 
            'last_pre_use_avail_status'
        ];

        // Check if any tracked field has unsaved changes
        let hasChanges = fieldsToTrack.some(field => {
            const isDirty = frm.is_dirty(field);
            console.log(`Checking field: ${field}, isDirty: ${isDirty}`);
            return isDirty;
        });

        // Only proceed if there are changes
        if (hasChanges) {
            console.log("Detected changes in tracked fields, prompting user for confirmation.");
            frappe.confirm(
                'Information has changed. Do you want to confirm the details?',
                function() {
                    console.log("User confirmed changes.");

                    // Append new entry to breakdown_history if confirmed
                    const now = frappe.datetime.now_datetime();
                    const update_by = frappe.session.user;

                    const new_entry = {
                        update_by: update_by,
                        date: now,
                        location: frm.doc.location,
                        asset_name: frm.doc.asset_name,
                        breakdown_reason_updates: frm.doc.breakdown_reason_updates || '',
                        breakdown_status: frm.doc.breakdown_status,
                        breakdown_start_hours: frm.doc.hours_breakdown_start
                    };

                    console.log("Adding new entry to breakdown_history:", new_entry);

                    // Append the entry to the breakdown_history child table
                    frm.add_child('breakdown_history', new_entry);
                    frm.refresh_field('breakdown_history');

                    // Allow save to proceed after confirmation by setting the flag
                    frappe.validated = true;
                    frm.skip_confirmation = true; // Set flag to skip confirmation next time
                    frm.save();
                },
                function() {
                    // If user cancels, keep frappe.validated as false to prevent save
                    console.log("User did not confirm changes, cancelling save.");
                }
            );
        } else {
            console.log("No changes detected in tracked fields; skipping history update.");
            frappe.validated = true; // Allow save without updating history if no changes detected
        }
    },

    location: function(frm) {
        console.log("Location field triggered. Checking for assets linked to location:", frm.doc.location);
        if (frm.doc.location) {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Asset',
                    filters: { location: frm.doc.location },
                    fields: ['name']
                },
                callback: function(response) {
                    const assets = response.message;
                    console.log("Assets found for location:", assets);

                    // Create a filtered options list based on assets linked to the location
                    if (assets && assets.length > 0) {
                        let asset_options = assets.map(asset => asset.name);
                        frm.set_query('asset_name', function() {
                            return {
                                filters: {
                                    name: ['in', asset_options]
                                }
                            };
                        });
                        
                        // Automatically set asset_name if there is only one option
                        if (assets.length === 1) {
                            frm.set_value('asset_name', assets[0].name);
                        } else {
                            frm.set_value('asset_name', ''); // Clear the field if multiple options exist
                        }
                    } else {
                        frappe.msgprint(__('No assets found for the selected location.'));
                        frm.set_value('asset_name', ''); // Clear the asset_name field if no assets match
                    }
                }
            });
        } else {
            frm.set_value('asset_name', ''); // Clear asset_name if location is not set
        }
    },

    refresh: function(frm) {
        console.log("Running refresh function to set breakdown_history fields as read-only.");

        // Lock all fields in breakdown_history table to make them read-only
        frm.fields_dict['breakdown_history'].grid.wrapper.find('.grid-delete-row').hide();
        frm.fields_dict['breakdown_history'].grid.wrapper.find('.grid-edit-row').hide();

        const fields = ['update_by', 'date', 'location', 'asset_name', 
                        'breakdown_reason_updates', 'breakdown_status', 
                        'breakdown_start_hours'];
        fields.forEach(field => {
            frm.fields_dict['breakdown_history'].grid.fields_map[field].read_only = true;
            console.log(`Set field ${field} as read-only in breakdown_history.`);
        });

        frm.refresh_field('breakdown_history');
    }
});
