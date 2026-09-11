// Copyright (c) 2026, BuFf0k and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Licence", {
	refresh(frm) {
		// Available on Draft and Submitted (not on a new, unsaved doc, nor a
		// Cancelled one — renewing from a voided record doesn't make sense).
		if (frm.is_new() || frm.doc.docstatus === 2) {
			return;
		}

		frm.add_custom_button(__("Renew"), () => {
			frappe.new_doc("Vehicle Licence", {
				fleet_number: frm.doc.fleet_number,
				site: frm.doc.site,
				registration_number: frm.doc.registration_number,
				chassis: frm.doc.chassis,
				engine_number: frm.doc.engine_number,
				vin_number: frm.doc.vin_number,
				issue_date: frappe.datetime.get_today(),
			});
		});
	},
});
