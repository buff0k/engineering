frappe.ui.form.on("Support Equipment", {
  refresh(frm) {
    frm.add_custom_button(__("Fetch Machines"), function () {
      fetch_support_equipment_assets(frm);
    });

    set_support_equipment_asset_queries(frm);
    apply_equipment_category_row_filter(frm);

    if (frm.doc.shift === "Day" || frm.doc.shift === "Night") {
      populate_opening_hours_from_previous_shift(frm);
    }
  },

  onload(frm) {
    set_support_equipment_asset_queries(frm);
  },

  location(frm) {
    if (!frm.doc.location) {
      return;
    }

    if (!has_child_rows(frm)) {
      fetch_support_equipment_assets(frm);
    } else {
      set_support_equipment_asset_queries(frm);
      apply_equipment_category_row_filter(frm);

      if (frm.doc.shift === "Day" || frm.doc.shift === "Night") {
        populate_opening_hours_from_previous_shift(frm);
      }

      frappe.show_alert({
        message: __("Site changed. Existing captured rows were kept. Click Fetch Machines to add missing machines."),
        indicator: "orange"
      });
    }
  },

  shift_date(frm) {
    if (frm.doc.shift === "Day" || frm.doc.shift === "Night") {
      populate_opening_hours_from_previous_shift(frm);
    }
  },

  shift(frm) {
    if (!frm.doc.location) {
      return;
    }

    if (!has_child_rows(frm)) {
      fetch_support_equipment_assets(frm);
    } else {
      populate_opening_hours_from_previous_shift(frm);
      apply_equipment_category_row_filter(frm);

      frappe.show_alert({
        message: __("Shift changed. Opening hours were updated from the previous shift."),
        indicator: "green"
      });
    }
  },

  equipment_category(frm) {
    set_support_equipment_asset_queries(frm);
    apply_equipment_category_row_filter(frm);

    if (!frm.doc.location) {
      return;
    }

    if (!has_child_rows(frm)) {
      fetch_support_equipment_assets(frm);
    } else {
      frappe.show_alert({
        message: frm.doc.equipment_category
          ? __("Showing only {0}. Other captured rows are hidden, not deleted.", [frm.doc.equipment_category])
          : __("Showing all support equipment rows."),
        indicator: "green"
      });
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

        if (frm.doc.shift === "Day" || frm.doc.shift === "Night") {
          populate_opening_hours_from_previous_shift(frm);
        }

        setTimeout(function () {
          apply_equipment_category_row_filter(frm);
        }, 300);
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


function has_child_rows(frm) {
  return (frm.doc.pre_use_assets || []).length > 0;
}


function fetch_support_equipment_assets(frm) {
  if (!frm.doc.location) {
    frappe.msgprint(__("Please select a Site first."));
    return;
  }

  const existing_rows_by_asset = {};

  (frm.doc.pre_use_assets || []).forEach((row) => {
    if (row.asset_name) {
      existing_rows_by_asset[row.asset_name] = {
        engine_start_hours: row.engine_start_hours,
        engine_end_hours: row.engine_end_hours,
        working_hours: row.working_hours,
        operator_name: row.operator_name,
        operator_number: row.operator_number,
        plant_number: row.plant_number,
        equipment_category: row.equipment_category,
        model: row.model
      };
    }
  });

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

      assets.forEach((asset) => {
        let row = find_child_row_by_asset(frm, asset.name);
        const existing = existing_rows_by_asset[asset.name] || {};

        if (!row) {
          row = frm.add_child("pre_use_assets");
          row.asset_name = asset.name;
        }

        row.plant_number = asset.asset_name || existing.plant_number || "";
        row.equipment_category = asset.asset_category || existing.equipment_category || "";
        row.model = asset.item_name || existing.model || "";

        /*
          Keep captured end hours.
          Start hours will be corrected by populate_opening_hours_from_previous_shift()
          for Day/Night flow.
        */
        if (existing.engine_start_hours !== undefined && existing.engine_start_hours !== null) {
          row.engine_start_hours = existing.engine_start_hours;
        } else if (row.engine_start_hours === undefined || row.engine_start_hours === null) {
          row.engine_start_hours = 0;
        }

        if (existing.engine_end_hours !== undefined && existing.engine_end_hours !== null) {
          row.engine_end_hours = existing.engine_end_hours;
        } else if (row.engine_end_hours === undefined || row.engine_end_hours === null) {
          row.engine_end_hours = 0;
        }

        if (existing.working_hours !== undefined && existing.working_hours !== null) {
          row.working_hours = existing.working_hours;
        } else if (row.working_hours === undefined || row.working_hours === null) {
          row.working_hours = 0;
        }

        if (existing.operator_name !== undefined && existing.operator_name !== null) {
          row.operator_name = existing.operator_name;
        }

        if (existing.operator_number !== undefined && existing.operator_number !== null) {
          row.operator_number = existing.operator_number;
        }
      });

      frm.refresh_field("pre_use_assets");

      if (frm.doc.shift === "Day" || frm.doc.shift === "Night") {
        populate_opening_hours_from_previous_shift(frm);
      }

      setTimeout(function () {
        apply_equipment_category_row_filter(frm);
      }, 300);

      const category_message = frm.doc.equipment_category
        ? frm.doc.equipment_category
        : __("all support equipment categories");

      frappe.show_alert({
        message: __("Fetched machines for {0}. Existing captured data was preserved.", [
          category_message
        ]),
        indicator: "green"
      });
    }
  });
}


function find_child_row_by_asset(frm, asset_name) {
  const rows = frm.doc.pre_use_assets || [];

  for (let i = 0; i < rows.length; i++) {
    if (rows[i].asset_name === asset_name) {
      return rows[i];
    }
  }

  return null;
}


function apply_equipment_category_row_filter(frm) {
  const selected_category = frm.doc.equipment_category || "";

  if (!frm.fields_dict.pre_use_assets || !frm.fields_dict.pre_use_assets.grid) {
    return;
  }

  frm.refresh_field("pre_use_assets");

  setTimeout(function () {
    const grid = frm.fields_dict.pre_use_assets.grid;
    const rows = frm.doc.pre_use_assets || [];

    rows.forEach((row) => {
      const grid_row = grid.grid_rows_by_docname[row.name];

      if (!grid_row || !grid_row.wrapper) {
        return;
      }

      if (!selected_category) {
        grid_row.wrapper.show();
        return;
      }

      if (row.equipment_category === selected_category) {
        grid_row.wrapper.show();
      } else {
        grid_row.wrapper.hide();
      }
    });

    update_visible_row_count_message(frm);
  }, 300);
}


function update_visible_row_count_message(frm) {
  const selected_category = frm.doc.equipment_category || "";
  const rows = frm.doc.pre_use_assets || [];

  let visible_count = 0;

  rows.forEach((row) => {
    if (!selected_category || row.equipment_category === selected_category) {
      visible_count += 1;
    }
  });

  frm.dashboard.clear_comment();

  if (selected_category) {
    frm.dashboard.add_comment(
      __("Showing {0} {1} machine(s). Other rows are hidden, not deleted.", [
        visible_count,
        selected_category
      ]),
      "blue",
      true
    );
  }
}


function populate_opening_hours_from_previous_shift(frm) {
  if (!(frm.doc.shift === "Day" || frm.doc.shift === "Night")) {
    return;
  }

  if (!frm.doc.location || !frm.doc.shift_date) {
    return;
  }

  const rows = frm.doc.pre_use_assets || [];

  const asset_names = rows
    .filter((row) => row.asset_name)
    .map((row) => row.asset_name);

  if (!asset_names.length) {
    return;
  }

  frappe.call({
    method: "engineering.engineering.doctype.support_equipment.support_equipment.get_opening_hours_from_previous_shift",
    args: {
      location: frm.doc.location,
      shift_date: frm.doc.shift_date,
      shift: frm.doc.shift,
      asset_names: JSON.stringify(asset_names)
    },
    callback: function (response) {
      const opening_hours_map = response.message || {};

      rows.forEach((row) => {
        if (!row.asset_name) {
          return;
        }

        const opening_hours = opening_hours_map[row.asset_name];

        if (opening_hours === undefined || opening_hours === null) {
          return;
        }

        /*
          IMPORTANT FIX:
          Always overwrite Engine Start Hours from previous shift.

          Night Shift:
            same date Day Shift Engine End Hours
            becomes Night Shift Engine Start Hours.

          Day Shift:
            previous date Night Shift Engine End Hours
            becomes Day Shift Engine Start Hours.
        */
        frappe.model.set_value(
          row.doctype,
          row.name,
          "engine_start_hours",
          opening_hours
        );

        const has_end =
          row.engine_end_hours !== undefined &&
          row.engine_end_hours !== null &&
          row.engine_end_hours !== "";

        if (has_end && flt(row.engine_end_hours) !== 0) {
          const working_hours = Math.round(
            flt(row.engine_end_hours) - flt(opening_hours)
          );

          frappe.model.set_value(
            row.doctype,
            row.name,
            "working_hours",
            working_hours
          );
        } else {
          frappe.model.set_value(
            row.doctype,
            row.name,
            "working_hours",
            0
          );
        }
      });

      frm.refresh_field("pre_use_assets");

      setTimeout(function () {
        apply_equipment_category_row_filter(frm);
      }, 300);
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

  const has_start =
    row.engine_start_hours !== undefined &&
    row.engine_start_hours !== null &&
    row.engine_start_hours !== "";

  const has_end =
    row.engine_end_hours !== undefined &&
    row.engine_end_hours !== null &&
    row.engine_end_hours !== "";

  if (!has_start || !has_end) {
    frappe.model.set_value(cdt, cdn, "working_hours", 0);
    return;
  }

  const start_hours = flt(row.engine_start_hours);
  const end_hours = flt(row.engine_end_hours);

  /*
    End Hours = 0 means not captured yet.
    Allow it and keep Working Hours as 0.
  */
  if (end_hours === 0) {
    frappe.model.set_value(cdt, cdn, "working_hours", 0);
    return;
  }

  const working_hours = Math.round(end_hours - start_hours);

  frappe.model.set_value(
    cdt,
    cdn,
    "working_hours",
    working_hours
  );
}