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

		sync_html_fields(frm);
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

const HTML_FIELDS = [
	"vehicle_licence_compliance_html",
	"driver_licence_compliance_html",
	"company_vehicle_undertaking_html",
	"service_history_html",
];

function sync_html_fields(frm) {
	// A virtual HTML field's computed value DOES come through in frm.doc on
	// every load/reload (Document.get_valid_dict() evaluates is_virtual
	// properties server-side) — but ControlHTML only ever paints
	// this.df.options, which nothing keeps in sync with frm.doc on a plain
	// refresh(). Without this, these blocks render blank on open (most
	// visibly on an already-submitted doc, since nothing else ever fires a
	// field-change to accidentally trigger a repaint).
	HTML_FIELDS.forEach((fieldname) => {
		const field = frm.get_field(fieldname);
		if (field) {
			field.set_value(frm.doc[fieldname] || "");
		}
	});
}

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
			// control's value directly re-renders it; keeping frm.doc in
			// sync too means a later plain refresh() (see sync_html_fields)
			// re-applies this same value instead of the stale one the form
			// was originally loaded with.
			["vehicle_licence_compliance_html", "driver_licence_compliance_html", "company_vehicle_undertaking_html"].forEach(
				(fieldname) => {
					const html = r.message[fieldname] || "";
					frm.doc[fieldname] = html;
					const field = frm.get_field(fieldname);
					if (field) {
						field.set_value(html);
					}
				}
			);

			frm.set_value("overall_status", r.message.overall_status ?? null);

			set_headline(frm);
		},
	});
}
