frappe.ui.form.on('Engineering Legals', {
    refresh(frm) {
        apply_section_rules(frm);
    },

    sections(frm) {
        // Never carry over values from previous section
        frm.set_value('vehicle_type', null);
        frm.set_value('lifting_type', null);

        apply_section_rules(frm);
    }
});

function apply_section_rules(frm) {
    const section = (frm.doc.sections || '').trim();

    // Hide both conditional fields by default
    frm.toggle_display('vehicle_type', false);
    frm.toggle_display('lifting_type', false);

    // Not required by default
    frm.toggle_reqd('vehicle_type', false);
    frm.toggle_reqd('lifting_type', false);

    // Brake Test & PDS -> Vehicle Type required
    if (['Brake Test', 'PDS'].includes(section)) {
        frm.toggle_display('vehicle_type', true);
        frm.toggle_reqd('vehicle_type', true);
    }

    // Lifting Equipment -> Lifting Type required
    if (section === 'Lifting Equipment') {
        frm.toggle_display('lifting_type', true);
        frm.toggle_reqd('lifting_type', true);
    }
}
