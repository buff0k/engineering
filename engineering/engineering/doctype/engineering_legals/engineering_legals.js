frappe.ui.form.on('Engineering Legals', {
  refresh(frm) {
    apply_section_rules(frm);
    apply_hsec_rules(frm);
    set_expiry_date(frm);
    add_eng_legals_report_button(frm);
  },

  sections(frm) {
    frm.set_value('vehicle_type', null);
    frm.set_value('lifting_type', null);

    const section = (frm.doc.sections || '').trim();

    // populate HSEC external code from selected section
    frm.set_value('hsec_qualification_id_external', section || null);

    // Auto-send only for HSEC sections
    const HSEC_SEND_SECTIONS = ['Brake Test', 'FRCS'];
    frm.set_value('hsec_send', HSEC_SEND_SECTIONS.includes(section) ? 1 : 0);

    apply_section_rules(frm);
    apply_hsec_rules(frm);
    set_expiry_date(frm);
  },

  vehicle_type(frm) {
    set_expiry_date(frm);
  },

  lifting_type(frm) {
    set_expiry_date(frm);
  },

  start_date(frm) {
    set_expiry_date(frm);
  },

  hsec_send(frm) {
    apply_hsec_rules(frm);
  },

  // Stop Save until the upload created a real File row (prevents FileNotFoundError)
  validate: async function (frm) {
    const url = (frm.doc.attach_paper || "").trim();

    if (!url) {
      frappe.throw("Attach Paper is required.");
    }

    const r = await frappe.db.get_value("File", { file_url: url }, "name");
    if (!r || !r.message || !r.message.name) {
      frappe.throw("File is still uploading. Wait a few seconds, then Save again.");
    }
  }
});


// Block save until the uploaded file actually exists as a File record.
// Prevents "Error Attaching File" race condition on slow uploads.
frappe.ui.form.on("Engineering Legals", {
  validate: async function (frm) {
    const url = (frm.doc.attach_paper || "").trim();
    if (!url) return;

    // If user typed/pasted a path, it might not exist yet
    const r = await frappe.db.get_value("File", { file_url: url }, "name");

    if (!r || !r.message || !r.message.name) {
      frappe.throw("Attachment is still uploading (or not saved). Please wait a few seconds, then Save again.");
    }
  }
});


function apply_section_rules(frm) {
  const section = (frm.doc.sections || '').trim();

  frm.toggle_display('vehicle_type', false);
  frm.toggle_display('lifting_type', false);

  frm.toggle_reqd('vehicle_type', false);
  frm.toggle_reqd('lifting_type', false);

  if (['Brake Test', 'PDS'].includes(section)) {
    frm.toggle_display('vehicle_type', true);
    frm.toggle_reqd('vehicle_type', true);
  }

  if (section === 'Lifting Equipment') {
    frm.toggle_display('lifting_type', true);
    frm.toggle_reqd('lifting_type', true);
  }
}


function apply_hsec_rules(frm) {
  const send = !!frm.doc.hsec_send;

  // Only required if we are sending to HSEC
  frm.toggle_reqd('hsec_qualification_id_external', send);

  // Optional: hide the fields unless enabled
  frm.toggle_display('hsec_qual_category_id', send);
  frm.toggle_display('hsec_qualification_id_external', send);
  frm.toggle_display('hsec_inserted_at', send);
}




function set_expiry_date(frm) {
  const section = (frm.doc.sections || '').trim();
  const start = frm.doc.start_date;

  // default: blank expiry
  if (!start) {
    frm.set_value('expiry_date', null);
    return;
  }

  // NO expiry sections
  const NO_EXPIRY = new Set([
    'Machine Service Records',
    'Service Schedule',
    'Wearcheck'
  ]);

  if (NO_EXPIRY.has(section)) {
    frm.set_value('expiry_date', null);
    return;
  }

  const addMonths = (m) => frappe.datetime.add_months(start, m);

  let expiry = null;

  if (section === 'Brake Test') {
    if (frm.doc.vehicle_type === 'TMM') expiry = addMonths(1);
    else if (frm.doc.vehicle_type === 'LDV') expiry = addMonths(3);
  } else if (section === 'PDS') {
    if (frm.doc.vehicle_type === 'TMM') expiry = addMonths(1);
    else if (frm.doc.vehicle_type === 'LDV') expiry = addMonths(3);
  } else if (section === 'FRCS') {
    expiry = addMonths(3);
  } else if (section === 'Lifting Equipment') {
    if (frm.doc.lifting_type === 'Inspection') expiry = addMonths(3);
    else if (frm.doc.lifting_type === 'Certificate') expiry = addMonths(12);
  } else if (section === 'NDT') {
    expiry = addMonths(6);
  } else if (section === 'Fire Suppression') {
    expiry = addMonths(3);
} else if (section === 'Tyre Inspection Report') {
  expiry = addMonths(1);
} else if (section === 'Illumination Baseline') {
  expiry = addMonths(24); // +2 years
} else {
  expiry = null; // safe default
}


  frm.set_value('expiry_date', expiry);
}



function add_eng_legals_report_button(frm) {
  frm.remove_custom_button("Open Engineering Legals Report");

  frm.add_custom_button("Open Engineering Legals Report", () => {
    const params = new URLSearchParams({
      report_name: "Engineering Legals Report",
      as_at_date: frappe.datetime.get_today(),
      view: "Summary"
    });

    if (frm.doc.site) {
      params.set("site", frm.doc.site);
    }

    const url = `/app/query-report/Engineering%20Legals%20Report?${params.toString()}`;
    window.open(url, "_blank");
  });
}



