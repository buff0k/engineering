frappe.ui.form.on('Purchase Requisition', {
    refresh(frm) {
        if (frm.is_new()) return;

        if (frm.__custom_delete_button_added) return;
        frm.__custom_delete_button_added = true;

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
                            message: r?.message || __('You are not allowed to delete this document or it is linked elsewhere.')
                        });
                    });
                }
            );
        }, __('Actions'));
    }
});