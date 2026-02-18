// Copyright (c) 2025, Isambane Mining (Pty) Ltd
// For license information, please see license.txt

frappe.ui.form.on("Plant Breakdown or Maintenance", {
  breakdown_start_datetime(frm) {
    frm.trigger("set_breakdown_start_key");
    frm.trigger("calculate_hours");
  },

  resolved_datetime(frm) {
    frm.trigger("calculate_hours");
    frm.trigger("set_open_closed");
  },


  // Build YYYYMMDD from breakdown_start_datetime
  set_breakdown_start_key(frm) {
    const dt = frm.doc.breakdown_start_datetime;
    if (!dt) {
      frm.set_value("breakdown_start_key", "");
      return;
    }
    frm.set_value("breakdown_start_key", moment(dt).format("YYYYMMDD"));
  },


  set_open_closed(frm) {
    frm.set_value("open_closed", frm.doc.resolved_datetime ? "Closed" : "Open");
  },



  calculate_hours(frm) {
    const start = frm.doc.breakdown_start_datetime;
    const end = frm.doc.resolved_datetime;

    if (start && end) {
      const startTime = moment(start);
      const endTime = moment(end);

      if (endTime.isBefore(startTime)) {
        frappe.msgprint(__("Resolved time cannot be earlier than breakdown start."));
        frm.set_value("breakdown_hours", 0);
        return;
      }

      const diffHours = endTime.diff(startTime, "hours", true);
      frm.set_value("breakdown_hours", diffHours.toFixed(2));
    } else {
      frm.set_value("breakdown_hours", 0);
    }
  },

  async validate(frm) {
    frm.trigger("set_breakdown_start_key");
    frm.trigger("set_open_closed");
    await frm.trigger("enforce_single_open_breakdown");
  },

  async enforce_single_open_breakdown(frm) {
    if (!frm.is_new() || !frm.doc.asset_name) return;

    const r = await frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "Plant Breakdown or Maintenance",
        filters: {
          asset_name: frm.doc.asset_name,
          open_closed: "Open",
        },
        fields: ["name", "breakdown_start_datetime"],
        order_by: "breakdown_start_datetime desc",
        limit_page_length: 1,
      },
    });

    const row = (r.message || [])[0];
    if (!row) return;

    const link = frappe.utils.get_form_link(
      "Plant Breakdown or Maintenance",
      row.name,
      true
    );

    frappe.msgprint(
      `Cannot create a new record. Last record for this asset is still Open: ${link}`
    );
    frappe.validated = false;
  },





  refresh(frm) {
    // Make breakdown_hours read-only
    frm.set_df_property("breakdown_hours", "read_only", 1);

    // Make open_closed read-only + sync value
    frm.set_df_property("open_closed", "read_only", 1);
    frm.trigger("set_open_closed");

    // Show alert if excluded from A&U
    if (frm.doc.exclude_from_au) {
      frappe.show_alert({
        message: __("⚠️ This record is excluded from A&U downtime calculations."),
        indicator: "blue",
      });
    }
  },
});
