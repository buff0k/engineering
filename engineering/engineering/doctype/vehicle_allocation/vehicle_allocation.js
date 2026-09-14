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

	onload(frm) {
		// frm is a single JS object Frappe reuses across every Vehicle
		// Allocation record opened in this session — it is NOT recreated
		// per document. Custom state stuck directly on it (which
		// conflicts we've already warned about, whether the first-load
		// check has run) would otherwise silently carry over from
		// whichever record was open before this one, making the checks
		// look like they'd stopped firing on any record after the first.
		// onload fires fresh on every genuine document load (unlike
		// refresh, which also fires repeatedly within the same one), so
		// this is the correct place to reset it.
		frm.__fleet_conflicts_warned = new Set();
		frm.__fleet_conflict_checked = false;
	},

	asset(frm) {
		refresh_compliance_preview(frm);
		check_asset_conflict(frm);
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

		refresh_compliance_preview(frm);
		set_headline(frm);
		setup_driver_picker(frm);

		// Only on the form's first real render (opening it fresh, or
		// routing in) — not on every post-save refresh(), since validate()
		// already shows the equivalent warning server-side on save, and
		// popping up both would just be the same message twice.
		if (!frm.__fleet_conflict_checked && frm.doc.docstatus === 0) {
			frm.__fleet_conflict_checked = true;
			check_asset_conflict(frm);
			check_driver_conflicts(frm);
		}
	},
});

const HTML_FIELDS = [
	"vehicle_licence_compliance_html",
	"driver_licence_compliance_html",
	"company_vehicle_undertaking_html",
	"drivers_overview_html",
	"service_history_html",
];

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

// Two genuinely different situations were sharing one generic "Active
// Allocation Conflicts" popup — same title, same orange, same wording
// shape — regardless of whether it was the Asset side (expected, handled
// automatically on submit) or the Driver side (not handled automatically,
// needs a human decision). Split into two independently-triggered checks
// with distinct titles/indicators/wording, each firing only from the field
// that's actually relevant to it — changing a Driver no longer re-surfaces
// an unrelated Asset notice and vice versa.
function _warn_once(frm, key) {
	frm.__fleet_conflicts_warned = frm.__fleet_conflicts_warned || new Set();

	if (frm.__fleet_conflicts_warned.has(key)) {
		return false;
	}

	frm.__fleet_conflicts_warned.add(key);
	return true;
}

function check_asset_conflict(frm) {
	// Only meaningful pre-submit — once this allocation is itself Current,
	// close_previous_open_allocation has already resolved this, and
	// re-warning about it every time the doc is opened would be noise.
	if (frm.doc.docstatus !== 0 || !frm.doc.asset) {
		return;
	}

	frappe.call({
		method: "engineering.engineering.doctype.vehicle_allocation.vehicle_allocation.check_active_conflicts",
		args: { asset: frm.doc.asset, drivers: [], exclude_name: frm.doc.name },
		callback(r) {
			const conflicts = (r && r.message) || [];

			if (!conflicts.length) {
				return;
			}

			const esc = frappe.utils.escape_html;
			const fresh = conflicts.filter((c) => _warn_once(frm, `asset:${c.allocation}`));

			if (!fresh.length) {
				return;
			}

			const links = fresh
				.map(
					(c) =>
						`<a href="/app/vehicle-allocation/${encodeURIComponent(c.allocation)}" target="_blank" rel="noopener noreferrer">${esc(c.allocation)}</a>`
				)
				.join(", ");

			frappe.msgprint({
				title: __("Asset Already Allocated"),
				indicator: "blue",
				message: __(
					"{0} is currently allocated under {1}. Submitting this allocation will automatically close that one — no action needed.",
					[esc(frm.doc.asset), links]
				),
			});
		},
	});
}

function check_driver_conflicts(frm) {
	if (frm.doc.docstatus !== 0) {
		return;
	}

	const drivers = (frm.doc.drivers || []).map((row) => row.driver).filter(Boolean);

	if (!drivers.length) {
		return;
	}

	frappe.call({
		method: "engineering.engineering.doctype.vehicle_allocation.vehicle_allocation.check_active_conflicts",
		args: { asset: null, drivers, exclude_name: frm.doc.name },
		callback(r) {
			const conflicts = (r && r.message) || [];

			if (!conflicts.length) {
				return;
			}

			const esc = frappe.utils.escape_html;
			const fresh = conflicts.filter((c) => _warn_once(frm, `driver:${c.driver}:${c.allocation}`));

			if (!fresh.length) {
				return;
			}

			const lines = fresh.map((c) => {
				const link = `<a href="/app/vehicle-allocation/${encodeURIComponent(c.allocation)}" target="_blank" rel="noopener noreferrer">${esc(c.allocation)}</a>`;
				const driver_label = `<b>${esc(c.driver_name || c.driver)}</b>`;

				if (c.sole_driver) {
					return `<div>${__("{0}'s other allocation ({1}) will be closed automatically — a change of vehicle.", [driver_label, link])}</div>`;
				}

				return `<div>${__("{0} will be removed from the shared allocation {1} — that vehicle stays allocated to its other driver(s).", [
					driver_label,
					link,
				])}</div>`;
			});

			frappe.msgprint({
				title: __("Driver Reassignment"),
				indicator: "blue",
				message: lines.join(""),
			});
		},
	});
}

function setup_driver_picker(frm) {
	// Drivers (the real Table MultiSelect field) is hidden — this wires up
	// search/add/remove entirely inside the drivers_overview_html block's
	// own markup instead, via event delegation on its $wrapper (survives
	// the block being fully re-painted by refresh_compliance_preview on
	// every add/remove, since delegation is bound once to the stable
	// wrapper element, not to the swapped-out children).
	if (frm.__driver_picker_bound) {
		return;
	}

	const field = frm.fields_dict.drivers_overview_html;

	if (!field) {
		return;
	}

	frm.__driver_picker_bound = true;

	const $wrapper = field.$wrapper;
	let debounce_timer = null;

	$wrapper.on("input", "[data-fleet-driver-search]", function () {
		const $input = $(this);
		const $results = $wrapper.find("[data-fleet-driver-results]");
		const txt = $input.val();

		clearTimeout(debounce_timer);

		if (!txt) {
			$results.hide().empty();
			return;
		}

		debounce_timer = setTimeout(() => {
			frappe.call({
				method: "frappe.desk.search.search_link",
				args: { doctype: "Employee", txt, reference_doctype: "Vehicle Allocation Driver" },
				callback(r) {
					render_driver_search_results(frm, $wrapper, (r && r.message) || []);
				},
			});
		}, 250);
	});

	$wrapper.on("click", "[data-fleet-driver-remove]", function (e) {
		e.stopPropagation();
		remove_driver(frm, $(this).attr("data-fleet-driver-remove"));
	});

	$(document).on("click.fleet_driver_picker", (e) => {
		if (!$(e.target).closest($wrapper).length) {
			$wrapper.find("[data-fleet-driver-results]").hide();
		}
	});
}

function render_driver_search_results(frm, $wrapper, matches) {
	const $results = $wrapper.find("[data-fleet-driver-results]");
	const existing = (frm.doc.drivers || []).map((row) => row.driver);
	const filtered = matches.filter((m) => !existing.includes(m.value));
	const esc = frappe.utils.escape_html;

	if (!filtered.length) {
		$results.html(`<div style="padding:8px 10px; color:var(--text-muted); font-size:12px;">${__("No matches")}</div>`).show();
		return;
	}

	$results
		.html(
			filtered
				.map(
					(m) =>
						`<div class="fleet-driver-result" data-value="${esc(m.value)}" style="padding:6px 10px; cursor:pointer; font-size:12px;">${esc(m.value)} - ${esc(m.description || m.label || "")}</div>`
				)
				.join("")
		)
		.show();

	$results
		.find(".fleet-driver-result")
		.on("mouseenter", function () {
			$(this).css("background", "var(--fg-hover-color)");
		})
		.on("mouseleave", function () {
			$(this).css("background", "");
		})
		.on("click", function () {
			add_driver(frm, $(this).attr("data-value"));
			$wrapper.find("[data-fleet-driver-search]").val("");
			$results.hide().empty();
		});
}

function add_driver(frm, employee) {
	if (!employee || (frm.doc.drivers || []).some((row) => row.driver === employee)) {
		return;
	}

	const row = frappe.model.add_child(frm.doc, "Vehicle Allocation Driver", "drivers");
	row.driver = employee;
	frm.dirty();
	refresh_compliance_preview(frm);
	check_driver_conflicts(frm);
}

function remove_driver(frm, employee) {
	const rows = frm.doc.drivers || [];
	const row = rows.find((r) => r.driver === employee);

	if (!row) {
		return;
	}

	frappe.model.clear_doc("Vehicle Allocation Driver", row.name);
	frm.doc.drivers = rows.filter((r) => r.driver !== employee);
	frm.dirty();
	refresh_compliance_preview(frm);
	check_driver_conflicts(frm);
}

function refresh_compliance_preview(frm) {
	// Driver Licence / Company Vehicle Undertaking / Vehicle Licence
	// Compliance / Service History are HTML fields (server-rendered,
	// is_virtual: 1). Following the same pattern used across the ir app
	// (e.g. Disciplinary Action's render_linked_docs) rather than trusting
	// frm.doc to already carry the right value: always make a live call on
	// refresh — never assume the initial doc payload threaded a virtual
	// field's value into the control correctly. This runs unconditionally
	// (including on a brand-new, still-empty form and on an already-
	// submitted doc) so every block always reflects reality, not just
	// after a field change.
	const drivers = (frm.doc.drivers || []).map((row) => row.driver).filter(Boolean);

	frappe.call({
		method: "engineering.engineering.doctype.vehicle_allocation.vehicle_allocation.preview_compliance",
		args: {
			asset: frm.doc.asset,
			required_licence_type: frm.doc.required_licence_type,
			drivers,
		},
		callback(r) {
			const data = r.message || {};

			HTML_FIELDS.forEach((fieldname) => {
				if (!frm.fields_dict[fieldname]) return;

				const html = data[fieldname] || "";
				frm.doc[fieldname] = html;
				frm.fields_dict[fieldname].$wrapper.html(html);
			});

			frm.set_value("overall_status", data.overall_status ?? null);

			set_headline(frm);
		},
	});
}
