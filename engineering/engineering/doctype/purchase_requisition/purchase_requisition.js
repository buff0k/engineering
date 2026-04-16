frappe.ui.form.on('Purchase Requisition', {
    refresh(frm) {
        if (frm.doc.name && !frm.doc.__islocal && frm.doc.pr_no !== frm.doc.name) {
            frm.set_value('pr_no', frm.doc.name);
        }
    },

    requested_by(frm) {
        if (!frm.doc.requested_by) {
            frm.set_value('requested_by_name', '');
            return;
        }

        frappe.db.get_value(
            'Employee',
            frm.doc.requested_by,
            ['employee_name']
        ).then(r => {
            if (r.message) {
                frm.set_value('requested_by_name', r.message.employee_name || '');
            }
        });
    },

    authorised_by(frm) {
        if (!frm.doc.authorised_by) {
            frm.set_value('authorised_by_name', '');
            return;
        }

        frappe.db.get_value(
            'Employee',
            frm.doc.authorised_by,
            ['employee_name']
        ).then(r => {
            if (r.message) {
                frm.set_value('authorised_by_name', r.message.employee_name || '');
            }
        });
    },

    discount(frm) {
        calculate_totals(frm);
    },

    vat(frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Purchase Requisition Item', {
    qty(frm, cdt, cdn) {
        calculate_row(frm, cdt, cdn);
    },

    unit_price(frm, cdt, cdn) {
        calculate_row(frm, cdt, cdn);
    },

    items_remove(frm) {
        calculate_totals(frm);
    }
});

function calculate_row(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.total_cost = (flt(row.qty) || 0) * (flt(row.unit_price) || 0);
    frm.refresh_field('items');
    calculate_totals(frm);
}

function calculate_totals(frm) {
    let items_total = 0;

    (frm.doc.items || []).forEach(function(row) {
        items_total += flt(row.total_cost);
    });

    frm.set_value('total', items_total - flt(frm.doc.discount) + flt(frm.doc.vat));
}