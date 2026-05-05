frappe.ui.form.on("Repair Log Sheet", {
    refresh(frm) {
        frm.set_query("plant_no", function() {
            return {
                filters: {
                    docstatus: ["!=", 2]
                }
            };
        });
    },

    plant_no(frm) {
        if (!frm.doc.plant_no) {
            frm.clear_table("repair_entries");
            frm.refresh_field("repair_entries");
            frm.set_value("make", "");
            frm.set_value("model", "");
            return;
        }

        populate_repair_entries_from_msr(frm);
    }
});


function populate_repair_entries_from_msr(frm) {
    frappe.call({
        method: "engineering.engineering.doctype.repair_log_sheet.repair_log_sheet.get_msr_entries_for_asset",
        args: {
            plant_no: frm.doc.plant_no
        },
        freeze: true,
        freeze_message: __("Loading MSR entries..."),
        callback: function(r) {
            if (r.exc) {
                return;
            }

            frm.clear_table("repair_entries");

            const entries = r.message || [];

            if (!entries.length) {
                frm.refresh_field("repair_entries");
                frappe.msgprint(__("No Mechanical Service Reports found for Plant No {0}", [frm.doc.plant_no]));
                return;
            }

            entries.forEach(function(entry) {
                let row = frm.add_child("repair_entries");

                row.msr = entry.msr || "";
                row.service_date = entry.service_date || "";
                row.hours = entry.hours || 0;
                row.defect = entry.defect || "";
                row.description = entry.description || "";
                row.rep_by = entry.rep_by || "";
                row.site = entry.site || "";
            });

            frm.refresh_field("repair_entries");
        }
    });
}