frappe.ui.form.on('Isambane Opencast Mining Job Card', {
    refresh(frm) {
        calculate_total_downtime(frm);
    },
    start_of_downtime(frm) {
        calculate_total_downtime(frm);
    },
    end_of_downtime(frm) {
        calculate_total_downtime(frm);
    },
    items_add(frm) {
        calculate_total_downtime(frm);
    }
});

frappe.ui.form.on('Isambane Opencast Mining Job Card Item', {
    date_start_time(frm, cdt, cdn) {
        calculate_row_downtime(frm, cdt, cdn);
    },
    date_finish_time(frm, cdt, cdn) {
        calculate_row_downtime(frm, cdt, cdn);
    },
    items_remove(frm) {
        calculate_total_downtime(frm);
    }
});

function calculate_row_downtime(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.date_start_time && row.date_finish_time) {
        const start = frappe.datetime.str_to_obj(row.date_start_time);
        const finish = frappe.datetime.str_to_obj(row.date_finish_time);
        const hours = (finish - start) / 3600000;
        frappe.model.set_value(cdt, cdn, 'downtime_hrs', hours > 0 ? flt(hours, 2) : 0);
    } else {
        frappe.model.set_value(cdt, cdn, 'downtime_hrs', 0);
    }
    calculate_total_downtime(frm);
}

function calculate_total_downtime(frm) {
    let total = 0;
    (frm.doc.items || []).forEach(row => {
        total += flt(row.downtime_hrs);
    });

    if (frm.doc.start_of_downtime && frm.doc.end_of_downtime) {
        const start = frappe.datetime.str_to_obj(frm.doc.start_of_downtime);
        const finish = frappe.datetime.str_to_obj(frm.doc.end_of_downtime);
        const parent_hours = (finish - start) / 3600000;
        if (parent_hours > 0) {
            total = flt(parent_hours, 2);
        }
    }

    frm.set_value('total_downtime_hrs', flt(total, 2));
}
