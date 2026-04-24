frappe.ui.form.on('Purchase Requisition', {
    onload(frm) {
        populate_plant_fields(frm);
        set_official_company_order_no_read_only(frm);
    },

    refresh(frm) {
        populate_plant_fields(frm);
        add_forced_delete(frm);
        set_official_company_order_no_read_only(frm);
    },

    after_save(frm) {
        set_official_company_order_no_read_only(frm);
    },

    official_company_order_no(frm) {
        set_official_company_order_no_read_only(frm);
    },

    plant_no(frm) {
        populate_plant_fields(frm);
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

function set_official_company_order_no_read_only(frm) {
    const fieldname = 'official_company_order_no';
    const has_value = cint(frm.doc.__islocal) === 0 && !!frm.doc[fieldname];

    if (frm.fields_dict[fieldname]) {
        frm.fields_dict[fieldname].df.read_only = has_value ? 1 : 0;
        frm.fields_dict[fieldname].refresh();
    }

    frm.refresh_field(fieldname);
}

function populate_plant_fields(frm) {
    if (!frm.doc.plant_no) {
        frm.set_value('plant_make', '');
        frm.set_value('model', '');
        return;
    }

    frappe.db.get_value(
        'Asset',
        frm.doc.plant_no,
        ['asset_category', 'item_code']
    ).then(r => {
        if (r.message) {
            frm.set_value('plant_make', r.message.asset_category || '');
            frm.set_value('model', r.message.item_code || '');
        }
    });
}

function add_forced_delete(frm) {
    if (frm.is_new()) return;
    if (frm.__delete_button_added) return;

    frm.__delete_button_added = true;

    frm.add_custom_button(__('Delete'), function () {
        frappe.confirm(
            __('Are you sure you want to delete this Purchase Requisition?'),
            function () {
                frappe.call({
                    method: 'frappe.client.delete',
                    args: {
                        doctype: frm.doc.doctype,
                        name: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __('Deleting...')
                }).then(() => {
                    frappe.show_alert({
                        message: __('Purchase Requisition deleted'),
                        indicator: 'green'
                    });
                    frappe.set_route('List', 'Purchase Requisition');
                }).catch((r) => {
                    frappe.msgprint({
                        title: __('Delete Failed'),
                        indicator: 'red',
                        message: r?.message || __('Unable to delete this document.')
                    });
                });
            }
        );
    });
}

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