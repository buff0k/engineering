// Copyright (c) 2026, BuFf0k and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Allocation", {
	setup(frm) {
		frm.set_query("asset", () => ({
			query: "engineering.engineering.doctype.vehicle_allocation.vehicle_allocation.public_road_asset_query",
		}));

		frm.set_query("required_licence_type", () => ({
			filters: { is_licence: 1 },
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === "Current") {
			frm.add_custom_button(__("Return Vehicle"), () => {
				frappe.confirm(
					__("Close this allocation? The Asset will show as unallocated until a new Vehicle Allocation is submitted."),
					() => {
						frm.call("close").then(() => frm.reload_doc());
					}
				);
			});
		}

		if (frm.doc.addendum_url) {
			const $wrapper = frm.get_field("addendum_url").$wrapper;
			$wrapper.find(".control-value").html(
				`<a href="${frappe.utils.escape_html(frm.doc.addendum_url)}" target="_blank">${__("View Uploaded Undertaking")}</a>`
			);
		}

		if (!frm.doc.overall_status) {
			return;
		}

		const indicator_map = {
			Compliant: "green",
			"Attention Required": "orange",
			"Non-Compliant": "red",
		};

		frm.dashboard.clear_headline();
		frm.dashboard.set_headline_alert(
			`Overall Status: ${frm.doc.overall_status}`,
			indicator_map[frm.doc.overall_status] || "grey"
		);
	},
});
