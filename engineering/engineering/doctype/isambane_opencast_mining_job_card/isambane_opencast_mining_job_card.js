frappe.ui.form.on('Isambane Opencast Mining Job Card', {
    onload(frm) {
        set_employee_queries(frm);
    },

    refresh(frm) {
        set_employee_queries(frm);
        calculate_total_downtime(frm);
        populate_requested_by_display(frm);
        populate_artisan_display(frm);
        populate_supervisor_display(frm);
        populate_site_engineering_manager_display(frm);
        populate_equipment_details(frm);
    },

    company_no(frm) {
        set_employee_name_from_link(frm, 'company_no', 'requested_by_site_engineering_manager');
        populate_site_engineering_manager_display(frm);
    },

    company_no1(frm) {
        set_employee_name_from_link(frm, 'company_no1', 'artisan_name_and_surname');
        populate_artisan_display(frm);
    },

    company_no2(frm) {
        set_employee_name_from_link(frm, 'company_no2', 'supervisor_forman_name_and_surname');
        populate_supervisor_display(frm);
    },

    equipment_no(frm) {
        populate_equipment_details(frm);
    },

    start_of_downtime(frm) {
        calculate_total_downtime(frm);
    },

    end_of_downtime(frm) {
        calculate_total_downtime(frm);
    },

    after_save(frm) {
        populate_requested_by_display(frm);
        populate_artisan_display(frm);
        populate_supervisor_display(frm);
        populate_site_engineering_manager_display(frm);
        populate_equipment_details(frm);
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

function set_employee_queries(frm) {
    frm.set_query('company_no', function () {
        return {};
    });

    frm.set_query('company_no1', function () {
        return {};
    });

    frm.set_query('company_no2', function () {
        return {};
    });
}

async function set_employee_name_from_link(frm, linkFieldname, targetFieldname) {
    const employeeId = frm.doc[linkFieldname];

    if (!employeeId) {
        await frm.set_value(targetFieldname, '');
        return;
    }

    try {
        const r = await frappe.db.get_value('Employee', employeeId, [
            'employee_name',
            'first_name',
            'last_name'
        ]);

        if (r && r.message) {
            const firstName = r.message.first_name || '';
            const lastName = r.message.last_name || '';
            const employeeName = r.message.employee_name || '';
            const fullName = [firstName, lastName].join(' ').trim() || employeeName || '';

            await frm.set_value(targetFieldname, fullName);
        }
    } catch (e) {
        console.error(`Failed to set ${targetFieldname} from ${linkFieldname}`, e);
    }
}

async function populate_requested_by_display(frm) {
    await set_employee_description_from_link(frm, 'company_no', 'requested_by_site_engineering_manager', 'Requested By Site Engineering Manager');
}

async function populate_artisan_display(frm) {
    await set_employee_description_from_link(frm, 'company_no1', 'artisan_name_and_surname', 'Artisan');
}

async function populate_supervisor_display(frm) {
    await set_employee_description_from_link(frm, 'company_no2', 'supervisor_forman_name_and_surname', 'Supervisor/Forman');
}

async function populate_site_engineering_manager_display(frm) {
    await set_employee_description_from_link(frm, 'company_no', 'requested_by_site_engineering_manager', 'Requested By Site Engineering Manager');
}

async function set_employee_description_from_link(frm, linkFieldname, targetFieldname, title) {
    frm.set_df_property(targetFieldname, 'description', '');
    frm.refresh_field(targetFieldname);

    const employeeId = frm.doc[linkFieldname];
    if (!employeeId) {
        return;
    }

    try {
        const emp = await frappe.db.get_doc('Employee', employeeId);

        const firstName = emp.first_name || '';
        const lastName = emp.last_name || '';
        const employeeName = emp.employee_name || '';
        const fullName = [firstName, lastName].join(' ').trim() || employeeName || employeeId;

        frm.set_df_property(targetFieldname, 'description', `${title} Name: ${fullName}`);
        frm.refresh_field(targetFieldname);
    } catch (e) {
        console.error(`Failed to load Employee details for ${targetFieldname}`, e);
    }
}

async function populate_equipment_details(frm) {
    if (!frm.doc.equipment_no) {
        await frm.set_value('machine_type', '');
        await frm.set_value('model', '');
        return;
    }

    try {
        const asset = await frappe.db.get_doc('Asset', frm.doc.equipment_no);

        let machineType =
            asset.machine_type ||
            asset.custom_machine_type ||
            asset.asset_category ||
            asset.item_group ||
            asset.item_name ||
            asset.item_code ||
            asset.asset_name ||
            '';

        let model =
            asset.model ||
            asset.custom_model ||
            asset.model_number ||
            asset.custom_model_number ||
            '';

        if ((!machineType || !model) && asset.item_code) {
            try {
                const item = await frappe.db.get_doc('Item', asset.item_code);

                if (!machineType) {
                    machineType =
                        item.item_group ||
                        item.item_name ||
                        item.item_code ||
                        '';
                }

                if (!model) {
                    model =
                        item.variant_of ||
                        item.item_name ||
                        item.item_code ||
                        '';
                }
            } catch (itemError) {
                console.error('Failed to load linked Item details', itemError);
            }
        }

        await frm.set_value('machine_type', machineType || '');
        await frm.set_value('model', model || '');
    } catch (e) {
        console.error('Failed to load Asset details', e);
        await frm.set_value('machine_type', '');
        await frm.set_value('model', '');
    }
}

function parseDateTime(value) {
    if (!value) return null;
    if (value instanceof Date) return value;
    if (typeof value !== 'string') return null;

    const v = value.trim();

    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?$/.test(v)) {
        const parts = v.split(' ');
        const d = parts[0].split('-').map(Number);
        const t = parts[1].split(':').map(Number);
        return new Date(d[0], d[1] - 1, d[2], t[0] || 0, t[1] || 0, t[2] || 0);
    }

    if (/^\d{2}-\d{2}-\d{4} \d{2}:\d{2}(:\d{2})?$/.test(v)) {
        const parts = v.split(' ');
        const d = parts[0].split('-').map(Number);
        const t = parts[1].split(':').map(Number);
        return new Date(d[2], d[1] - 1, d[0], t[0] || 0, t[1] || 0, t[2] || 0);
    }

    const jsDate = new Date(v);
    if (!isNaN(jsDate.getTime())) {
        return jsDate;
    }

    return null;
}

function calculate_row_downtime(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const start = parseDateTime(row.date_start_time);
    const finish = parseDateTime(row.date_finish_time);

    let hours = 0;
    if (start && finish) {
        const diff = (finish.getTime() - start.getTime()) / 3600000;
        hours = diff > 0 ? diff : 0;
    }

    frappe.model.set_value(cdt, cdn, 'downtime_hrs', flt(hours, 2));
    calculate_total_downtime(frm);
}

function calculate_total_downtime(frm) {
    let total = 0;

    (frm.doc.items || []).forEach(row => {
        const start = parseDateTime(row.date_start_time);
        const finish = parseDateTime(row.date_finish_time);

        let rowHours = flt(row.downtime_hrs);

        if (start && finish) {
            const diff = (finish.getTime() - start.getTime()) / 3600000;
            rowHours = diff > 0 ? diff : 0;

            if (flt(row.downtime_hrs) !== flt(rowHours, 2)) {
                frappe.model.set_value(row.doctype, row.name, 'downtime_hrs', flt(rowHours, 2));
            }
        }

        total += flt(rowHours, 2);
    });

    const parentStart = parseDateTime(frm.doc.start_of_downtime);
    const parentFinish = parseDateTime(frm.doc.end_of_downtime);

    if (parentStart && parentFinish) {
        const parentHours = (parentFinish.getTime() - parentStart.getTime()) / 3600000;
        if (parentHours > 0) {
            total = parentHours;
        }
    }

    frm.set_value('total_downtime_hrs', flt(total, 2));
}