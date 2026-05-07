frappe.ui.form.on("Support Equipment", {
  refresh(frm) {
    frm.add_custom_button(__("Fetch Machines"), function () {
      fetch_support_equipment_assets(frm);
    });

    set_support_equipment_asset_queries(frm);
  },

  onload(frm) {
    set_support_equipment_asset_queries(frm);
  },

  location(frm) {
    if (frm.doc.location) {
      fetch_support_equipment_assets(frm);
    }
  },

  equipment_category(frm) {
    if (frm.doc.location) {
      fetch_support_equipment_assets(frm);
    }
  }
});


frappe.ui.form.on("Support Equipment Assets", {
  asset_name(frm, cdt, cdn) {
    const row = locals[cdt][cdn];

    if (!row.asset_name) {
      return;
    }

    frappe.db.get_value(
      "Asset",
      row.asset_name,
      [
        "asset_name",
        "item_name",
        "asset_category"
      ],
      function (asset) {
        if (!asset) {
          return;
        }

        frappe.model.set_value(cdt, cdn, "plant_number", asset.asset_name || "");
        frappe.model.set_value(cdt, cdn, "equipment_category", asset.asset_category || "");
        frappe.model.set_value(cdt, cdn, "model", asset.item_name || "");
      }
    );
  },

  engine_start_hours(frm, cdt, cdn) {
    calculate_child_working_hours(cdt, cdn);
  },

  engine_end_hours(frm, cdt, cdn) {
    calculate_child_working_hours(cdt, cdn);
  }
});


function fetch_support_equipment_assets(frm) {
  if (!frm.doc.location) {
    frappe.msgprint(__("Please select a Site first."));
    return;
  }

  frappe.call({
    method: "engineering.engineering.doctype.support_equipment.support_equipment.get_support_equipment_assets",
    args: {
      location: frm.doc.location,
      equipment_category: frm.doc.equipment_category || ""
    },
    freeze: true,
    freeze_message: __("Fetching support equipment machines..."),
    callback: function (response) {
      const assets = response.message || [];

      frm.clear_table("pre_use_assets");

      assets.forEach((asset) => {
        const row = frm.add_child("pre_use_assets");

        row.asset_name = asset.name;
        row.plant_number = asset.asset_name || "";
        row.equipment_category = asset.asset_category || "";
        row.model = asset.item_name || "";
        row.working_hours = 0;
      });

      frm.refresh_field("pre_use_assets");

      const category_message = frm.doc.equipment_category
        ? frm.doc.equipment_category
        : __("all support equipment categories");

      frappe.show_alert({
        message: __("Fetched {0} machines for {1}", [
          assets.length,
          category_message
        ]),
        indicator: "green"
      });
    }
  });
}


function set_support_equipment_asset_queries(frm) {
  frm.set_query("asset_name", "pre_use_assets", function () {
    const filters = {
      location: frm.doc.location,
      docstatus: 1
    };

    if (frm.doc.equipment_category) {
      filters.asset_category = frm.doc.equipment_category;
    } else {
      filters.asset_category = ["in", [
        "Water Pump",
        "Lightning Plant",
        "Generator"
      ]];
    }

    return {
      filters: filters
    };
  });
}


function calculate_child_working_hours(cdt, cdn) {
  const row = locals[cdt][cdn];

  const start_hours = flt(row.engine_start_hours);
  const end_hours = flt(row.engine_end_hours);

  if (!row.engine_start_hours && row.engine_start_hours !== 0) {
    return;
  }

  if (!row.engine_end_hours && row.engine_end_hours !== 0) {
    return;
  }

  const working_hours = end_hours - start_hours;

  frappe.model.set_value(
    cdt,
    cdn,
    "working_hours",
    working_hours
  );
}