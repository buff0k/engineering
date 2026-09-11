const VEHICLE_ALLOCATION_COLOURS = {
	Compliant: "green",
	"Attention Required": "orange",
	"Non-Compliant": "red",
};
const VEHICLE_ALLOCATION_ALL_COLOURS = "green orange red grey blue yellow light-blue darkgrey purple pink";

frappe.listview_settings["Vehicle Allocation"] = {
	// overall_status is virtual (computed live, never stored), so it isn't
	// available in the bulk list-view query the way "status" (the real
	// allocation-period lifecycle column) is. get_indicator() shows a
	// neutral placeholder for "Current" rows on first paint; refresh()
	// below fetches the live compliance status for the rows actually on
	// screen and patches the indicator afterwards — nothing is cached.
	add_fields: ["status", "driver", "driver_name"],

	formatters: {
		driver(value, df, doc) {
			if (!value) return "";
			return doc.driver_name ? `${value} - ${frappe.utils.escape_html(doc.driver_name)}` : value;
		},
	},

	get_indicator(doc) {
		if (doc.status !== "Current") {
			const map = { Closed: "grey", Cancelled: "grey" };
			return [__(doc.status), map[doc.status] || "grey", `status,=,${doc.status}`];
		}

		return [__("Current"), "grey", "status,=,Current"];
	},

	refresh(listview) {
		const rows = (listview.data || []).filter((d) => d.status === "Current");

		if (!rows.length) {
			return;
		}

		frappe.call({
			method: "engineering.engineering.doctype.vehicle_allocation.vehicle_allocation.get_overall_statuses",
			args: { names: rows.map((r) => r.name) },
			callback(r) {
				const statuses = r.message || {};

				for (const [name, status] of Object.entries(statuses)) {
					const colour = VEHICLE_ALLOCATION_COLOURS[status] || "grey";
					const $row = listview.$result.find(`[data-name='${name}']`);

					$row.find(".indicator-pill").each(function () {
						const $pill = $(this);
						$pill.removeClass(VEHICLE_ALLOCATION_ALL_COLOURS).addClass(colour);
						$pill.find(".ellipsis").text(" " + __(status));
						$pill.attr("title", __(status));
					});

					$row.find(".indicator").each(function () {
						const $dot = $(this);
						$dot.removeClass(VEHICLE_ALLOCATION_ALL_COLOURS).addClass(colour);
						$dot.attr("title", __(status));
					});
				}
			},
		});
	},
};
