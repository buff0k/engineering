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

	asset(frm) {
		refresh_compliance_preview(frm);
	},

	required_licence_type(frm) {
		refresh_compliance_preview(frm);
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

		set_headline(frm);
	},
});

// Table MultiSelect fires <fieldname>_add / <fieldname>_remove against the
// CHILD doctype, not the parent — the same convention ERPNext core uses for
// plain Table fields (e.g. Stock Entry's items_add is registered under
// "Stock Entry Detail"). Registering these under "Vehicle Allocation"
// instead silently never fires.
frappe.ui.form.on("Vehicle Allocation Driver", {
	drivers_add(frm) {
		refresh_compliance_preview(frm);
	},

	drivers_remove(frm) {
		refresh_compliance_preview(frm);
	},
});

function set_headline(frm) {
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
}

function refresh_compliance_preview(frm) {
	// Driver Licence / Company Vehicle Undertaking / Vehicle Licence
	// Compliance are HTML fields (server-rendered, is_virtual: 1) — they
	// only get recomputed when the full Document is loaded, so on a plain
	// field change they'd otherwise stay stale until the next save +
	// reload. Ask the server to re-render them for the current in-progress
	// values and patch the form directly instead.
	const drivers = (frm.doc.drivers || []).map((row) => row.driver).filter(Boolean);

	if (!frm.doc.asset && !drivers.length) {
		return;
	}

	frappe.call({
		method: "engineering.engineering.doctype.vehicle_allocation.vehicle_allocation.preview_compliance",
		args: {
			asset: frm.doc.asset,
			required_licence_type: frm.doc.required_licence_type,
			drivers,
		},
		callback(r) {
			if (!r.message) {
				return;
			}

			// HTML-fieldtype controls render from df.options, not the doc's
			// field value — frm.set_value() only ever touches the latter,
			// so it silently does nothing for these three. Setting the
			// control's value directly re-renders it.
			const html_fields = [
				"vehicle_licence_compliance_html",
				"driver_licence_compliance_html",
				"company_vehicle_undertaking_html",
			];

			html_fields.forEach((fieldname) => {
				const field = frm.get_field(fieldname);
				if (field) {
					field.set_value(r.message[fieldname] || "");
				}
			});

			frm.set_value("overall_status", r.message.overall_status ?? null);

			set_headline(frm);
		},
	});
}
