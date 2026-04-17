frappe.ui.form.on('Purchase Requisition', {
    onload(frm) {
        if (frm.doc.name && !frm.doc.__islocal) {
            frm.set_value('pr_no', frm.doc.name);
        }
    },

    refresh(frm) {
        if (frm.doc.name && !frm.doc.__islocal && frm.doc.pr_no !== frm.doc.name) {
            frm.set_value('pr_no', frm.doc.name);
        }
    },

    plant_no(frm) {
        if (!frm.doc.plant_no) {
            frm.set_value('plant_make', '');
            frm.set_value('model', '');
            return;
        }

        frappe.db.get_value(
            'Asset',
            frm.doc.plant_no,
            ['item_name']
        ).then(r => {
            if (r.message) {
                frm.set_value('plant_make', r.message.item_name || '');
                frm.set_value('model', r.message.item_name || '');
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