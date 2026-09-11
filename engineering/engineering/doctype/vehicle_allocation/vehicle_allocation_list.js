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

	onload(listview) {
		listview.page.add_inner_button(__("Export to Excel"), () => {
			frappe.call({
				method: "engineering.engineering.doctype.vehicle_allocation.vehicle_allocation.export_road_asset_register_xlsx",
				freeze: true,
				freeze_message: __("Building Excel file…"),
				callback(r) {
					if (!r || !r.message || !r.message.content) return;

					const filename = r.message.filename || "road_asset_register.xlsx";
					const mime =
						r.message.type ||
						"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

					download_base64_file_vehicle_allocation(r.message.content, filename, mime);
				},
			});
		});
	},

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

function download_base64_file_vehicle_allocation(base64_content, filename, mime_type) {
	const byte_chars = atob(base64_content);
	const byte_numbers = new Array(byte_chars.length);

	for (let i = 0; i < byte_chars.length; i++) {
		byte_numbers[i] = byte_chars.charCodeAt(i);
	}

	const byte_array = new Uint8Array(byte_numbers);
	const blob = new Blob([byte_array], { type: mime_type });
	const url = window.URL.createObjectURL(blob);

	const link = document.createElement("a");
	link.href = url;
	link.download = filename;

	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);

	window.URL.revokeObjectURL(url);
}
