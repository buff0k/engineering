frappe.ui.form.on("Parts Requisition Form", {
	refresh(frm) {
		if (frm.doc.plant_no) {
			load_asset_details(frm);
		}
	},

	plant_no(frm) {
		load_asset_details(frm);
	}
});

function split_item_code(item_code) {
	if (!item_code) {
		return {
			plant_make: "",
			model: ""
		};
	}

	const cleaned = String(item_code).trim().replace(/\s+/g, " ");
	const parts = cleaned.split(" ");

	if (parts.length === 1) {
		return {
			plant_make: parts[0],
			model: parts[0]
		};
	}

	const plant_make = parts[parts.length - 1];
	const model = parts.slice(0, -1).join(" ");

	return {
		plant_make: plant_make || "",
		model: model || ""
	};
}

function load_asset_details(frm) {
	if (!frm.doc.plant_no) {
		frm.set_value("plant_make", "");
		frm.set_value("model", "");
		return;
	}

	frappe.db.get_doc("Asset", frm.doc.plant_no)
		.then(doc => {
			const item_code = doc.item_code || "";
			const split_values = split_item_code(item_code);

			const current_vin = frm.doc.vin_no || "";

			const vin_no =
				current_vin ||
				doc.vin_no ||
				doc.serial_no ||
				doc.chassis_no ||
				doc.custom_vin_no ||
				"";

			frm.set_value("plant_make", split_values.plant_make);
			frm.set_value("model", split_values.model);

			if (!frm.doc.vin_no) {
				frm.set_value("vin_no", vin_no);
			}
		})
		.catch(err => {
			console.error("Failed to load Asset details", err);
			frm.set_value("plant_make", "");
			frm.set_value("model", "");
			frappe.msgprint(__("Could not load Plant Make / Model from Asset."));
		});
}