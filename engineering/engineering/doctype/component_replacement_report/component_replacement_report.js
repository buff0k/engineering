// Copyright (c) 2025, Jorrie Jordaan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Component Replacement Report', {
    plant_no: function(frm) {
        //Fetch asset_name field from Asset document and enter into plant_description field
        if (frm.doc.plant_no) {
            frappe.db.get_value('Asset', frm.doc.plant_no, 'asset_name', (r) => {
                if (r && r.asset_name) {
                    frm.set_value('plant_description', r.asset_name);
                } else {
                    frm.set_value('plant_description', '');
                }
            });
        }
        //Fetch company field from Asset document and enter into company field
        if (frm.doc.plant_no) {
            frappe.db.get_value('Asset', frm.doc.plant_no, 'company', (s) => {
                if (s && s.company) {
                    frm.set_value('company', s.company);
                } else {
                    frm.set_value('company', '');
                }
            });
        }
        //Fetch custodian field from Asset document and enter into custodian field
        if (frm.doc.plant_no) {
            frappe.db.get_value('Asset', frm.doc.plant_no, 'custodian', (t) => {
                if (t && t.custodian) {
                    frm.set_value('custodian', t.custodian);
                } else {
                    frm.set_value('custodian', '');
                }
            });
        }
    }
});
frappe.ui.form.on('Component Replacement Report', {
    company: function(frm) {
        if (frm.doc.company) {
            frappe.db.get_value('Company', frm.doc.company, 'abbr', (u) => {
                if (u && u.abbr) {
                    frm.set_value('company_abbr', u.abbr);
                } else {
                    frm.set_value('company_abbr', '');
                }
            });
        }
        if (frm.doc.company) {
            frappe.db.get_value('Company', frm.doc.company, 'default_letter_head', (v) => {
                if (v && v.default_letter_head) {
                    frm.set_value('letter_head', v.default_letter_head);
                } else {
                    frm.set_value('letter_head', '');
                }
            });
        }
}});