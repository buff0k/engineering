frappe.listview_settings["Vehicle Allocation"] = {
	// overall_status / driver_licence_status / vehicle_licence_status /
	// addendum_status are virtual (computed live, not stored), so they are
	// not available in bulk list-view queries — only "status" (the
	// allocation-period lifecycle) is a real column here. Use the Fleet
	// Compliance Overview report or the Fleet Management dashboard for a
	// compliance-status view across many records at once.
	add_fields: ["status"],
	get_indicator(doc) {
		const colour_map = {
			Current: "green",
			Closed: "grey",
			Cancelled: "grey",
		};

		return [__(doc.status), colour_map[doc.status] || "grey", `status,=,${doc.status}`];
	},
};
