frappe.ui.form.on('Engineering Legals', {
  refresh(frm) {
    apply_section_rules(frm);
    set_expiry_date(frm);
    set_near_expire_table(frm);
  },

  sections(frm) {
    frm.set_value('vehicle_type', null);
    frm.set_value('lifting_type', null);

    apply_section_rules(frm);
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

function set_near_expire_table(frm, selected_site = "All Sites") {
  get_near_expire_rows(frm, selected_site, (rows) => {
    render_near_expire_table(frm, rows);
  });
}


function render_near_expire_table(frm, rows) {
  const wrapper = frm.fields_dict.legals && frm.fields_dict.legals.$wrapper;
  if (!wrapper) return;

const sections = [
  "Brake Test",
  "Fire Suppression",
  "FRCS",
  "Lifting Equipment",
  "NDT",
  "PDS",
  "Tyre Inspection Report",
  "Illumination Baseline"
];

  const today = frappe.datetime.get_today();
  const dates = [];
  for (let i = 0; i < 7; i++) dates.push(frappe.datetime.add_days(today, i));

  const bucket = {};
  for (const d of dates) bucket[d] = {};
  for (const sec of sections) for (const d of dates) bucket[d][sec] = [];

  for (const x of (rows || [])) {
    const sec = (x.sections || "").trim();
    const d = x.expiry_date;
    if (!sec || !bucket[d] || !bucket[d][sec]) continue;
    bucket[d][sec].push(x.fleet_number || "");
  }

  let html = `
<div style="display:flex; gap:12px; align-items:center; margin:8px 0 12px 0;">
  <div style="min-width:80px; font-weight:600;">Site</div>
  <select id="near-expire-site" class="form-control" style="max-width:280px;"></select>
</div>
<div class="near-expire-table" style="overflow:auto">
  <table class="table table-bordered near-expire-grid">
    <thead><tr><th class="sticky-col">Expiry Date</th>`;

  for (const sec of sections) html += `<th style="min-width:180px">${frappe.utils.escape_html(sec)}</th>`;
  html += `</tr></thead><tbody>`;

  for (const d of dates) {
    html += `<tr><td class="sticky-col date-cell" data-row="${dates.indexOf(d)}"><b>${frappe.datetime.str_to_user(d)}</b></td>`;
    for (const sec of sections) {
      const fleets = (bucket[d][sec] || []).filter(Boolean);
      const cell = fleets.length ? fleets.map(f => frappe.utils.escape_html(f)).join("<br>") : "";
      html += `<td style="white-space:normal; vertical-align:top">${cell}</td>`;
    }
    html += `</tr>`;
  }

  html += `</tbody></table></div>`;

  html += `
<style>
  .near-expire-grid { border-collapse: separate; }
  .near-expire-grid .sticky-col {
    position: sticky; left: 0; background: #fff; z-index: 2;
    min-width: 140px; box-shadow: 2px 0 5px rgba(0,0,0,0.05);
  }
  .near-expire-grid thead .sticky-col { z-index: 3; background: #f8f9fa; }
  .near-expire-grid td.date-cell { color: #fff; font-weight: 600; }
  .near-expire-grid td.date-cell[data-row="0"] { background: #8b0000; }
  .near-expire-grid td.date-cell[data-row="1"] { background: #a11212; }
  .near-expire-grid td.date-cell[data-row="2"] { background: #b22222; }
  .near-expire-grid td.date-cell[data-row="3"] { background: #c94a4a; }
  .near-expire-grid td.date-cell[data-row="4"] { background: #d96c6c; }
  .near-expire-grid td.date-cell[data-row="5"] { background: #e89a9a; }
  .near-expire-grid td.date-cell[data-row="6"] { background: #f3c5c5; color:#000; }
</style>
`;

  wrapper.html(html);

  // Populate Site dropdown from rows
  const siteSet = new Set((rows || []).map(r => (r.site || "").trim()).filter(Boolean));
  const sites = ["All Sites", ...Array.from(siteSet).sort()];

  const $select = wrapper.find("#near-expire-site");
  $select.empty();
  sites.forEach(s => $select.append(`<option value="${frappe.utils.escape_html(s)}">${frappe.utils.escape_html(s)}</option>`));

  // Default selection: current doc site if present else All
  const defaultSite = (frm.doc.site || "").trim();
  if (defaultSite && sites.includes(defaultSite)) $select.val(defaultSite);
  else $select.val("All Sites");

  // Filter table by site by re-running query
  $select.on("change", () => set_near_expire_table(frm, $select.val()));
}

function get_near_expire_rows(frm, selected_site, callback) {
  const today = frappe.datetime.get_today();
  const end = frappe.datetime.add_days(today, 6);

  const filters = [
    ["expiry_date", "is", "set"],
    ["expiry_date", "between", [today, end]],
    ["docstatus", "<", 2]
  ];

  if (selected_site && selected_site !== "All Sites") {
    filters.push(["site", "=", selected_site]);
  }

  frappe.call({
    method: "frappe.client.get_list",
    args: {
      doctype: "Engineering Legals",
      fields: ["name", "sections", "fleet_number", "expiry_date", "site"],
      filters,
      limit_page_length: 1000
    },
    callback: (r) => callback(r.message || [])
  });
}
