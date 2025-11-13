// Copyright (c) 2025, Isambane Mining (Pty) Ltd
// For license information, please see license.txt

frappe.ui.form.on("Plant Breakdown or Maintenance", {
  breakdown_start_datetime(frm) {
    frm.trigger("calculate_hours");
  },

  resolved_datetime(frm) {
    frm.trigger("calculate_hours");
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

  refresh(frm) {
    // Make breakdown_hours read-only
    frm.set_df_property("breakdown_hours", "read_only", 1);

    // Show alert if excluded from A&U
    if (frm.doc.exclude_from_au) {
      frappe.show_alert({
        message: __("⚠️ This record is excluded from A&U downtime calculations."),
        indicator: "blue",
      });
    }
  },
});
