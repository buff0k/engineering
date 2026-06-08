frappe.ui.form.on("Travel Log Sheet", {
    fleet_number(frm) {
        if (!frm.doc.fleet_number) {
            return;
        }

        frappe.call({
            method: "engineering.api.mobile.get_last_travel_log_odo",
            args: {
                fleet_number: frm.doc.fleet_number,
            },
            callback(r) {
                if (r.message && r.message.odo_meter_out !== null) {
                    frm.set_value("odo_meter_out", r.message.odo_meter_out);
                }
            },
        });
    },

    odo_meter_out(frm) {
        validate_odo_meters(frm);
    },

    odo_meter_in(frm) {
        validate_odo_meters(frm);
    },
});

function validate_odo_meters(frm) {
    if (!frm.doc.odo_meter_out || !frm.doc.odo_meter_in) {
        return;
    }

    if (frm.doc.odo_meter_in < frm.doc.odo_meter_out) {
        frappe.msgprint("ODO Meter In cannot be less than ODO Meter Out");
        frm.set_value("odo_meter_in", "");
    }
}