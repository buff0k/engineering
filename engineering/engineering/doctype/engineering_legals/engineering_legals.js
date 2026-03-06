frappe.ui.form.on('Engineering Legals', {
  refresh(frm) {
    apply_section_rules(frm);
    apply_hsec_rules(frm);
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

function set_near_expire_table(frm, selected_site = "All Sites", range_days = 7) {
  // remember last selections
  frm.__near_expire_site = selected_site;
  frm.__near_expire_range = range_days;

  get_near_expire_rows(frm, selected_site, range_days, (rows) => {
    render_near_expire_table(frm, rows, selected_site, range_days);
  });
}


function render_near_expire_table(frm, rows, selected_site = "All Sites", range_days = 7) {
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
  dates.push("__OVERDUE__");
  for (let i = 0; i < range_days; i++) dates.push(frappe.datetime.add_days(today, i));

  // bucket[dateKey][section] = [fleet...]
  const bucket = {};
  for (const d of dates) bucket[d] = {};
  for (const sec of sections) for (const d of dates) bucket[d][sec] = [];

  for (const x of (rows || [])) {
    const sec = (x.sections || "").trim();
    const d = x.expiry_date;
    const fleet = (x.fleet_number || "").trim();
    const site = (x.site || "").trim();

    if (!sec || !fleet) continue;

    const is_overdue = d && (d < today); // yyyy-mm-dd string compare works
    const key = is_overdue ? "__OVERDUE__" : d;

    if (!bucket[key] || !bucket[key][sec]) continue;

    bucket[key][sec].push({ fleet, sec, site });
  }

  const ranges = [7, 14, 21, 28, 35];

  let html = `
<div style="display:flex; gap:12px; align-items:center; margin:8px 0 12px 0; flex-wrap:wrap;">
  <div style="min-width:60px; font-weight:600;">Site</div>
  <select id="near-expire-site" class="form-control" style="max-width:280px;"></select>

  <div style="min-width:70px; font-weight:600;">Range</div>
  <select id="near-expire-range" class="form-control" style="max-width:160px;">
    ${ranges.map(d => `<option value="${d}">${d} days</option>`).join("")}
  </select>

  <button id="open-eng-legals-report" class="btn btn-primary btn-sm open-eng-legals-btn">
    Open Engineering Legals Report
  </button>

  <div style="opacity:.75; font-size:12px;">
    Click a fleet number to open the filtered list.
  </div>
</div>

<div class="near-expire-table" style="overflow:auto">
  <table class="table table-bordered near-expire-grid">
    <thead><tr><th class="sticky-col">Expiry</th>`;

  for (const sec of sections) html += `<th style="min-width:180px">${frappe.utils.escape_html(sec)}</th>`;
  html += `</tr></thead><tbody>`;

  const dateLabel = (d) => {
    if (d === "__OVERDUE__") return "OVERDUE";
    return frappe.datetime.str_to_user(d);
  };

  const dateCellStyle = (d, idx) => {
    if (d === "__OVERDUE__") return "background:#8b0000;color:#fff;font-weight:700;";
    if (idx === 1) return "background:#b22222;color:#fff;font-weight:700;"; // today
    if (idx <= 7) return "background:#d96c6c;color:#fff;font-weight:700;"; // next 7
    return "background:#f3c5c5;color:#000;font-weight:700;"; // later
  };

  for (let idx = 0; idx < dates.length; idx++) {
    const d = dates[idx];
    html += `<tr><td class="sticky-col date-cell" style="${dateCellStyle(d, idx)}"><b>${dateLabel(d)}</b></td>`;

    for (const sec of sections) {
      const fleets = (bucket[d][sec] || []);

      const cell = fleets.length
        ? fleets.map(obj => {
            const f = frappe.utils.escape_html(obj.fleet);
            const s = frappe.utils.escape_html(obj.sec);
            const site = frappe.utils.escape_html(obj.site || "");
            return `<a href="#" class="near-expire-fleet" data-fleet="${f}" data-sec="${s}" data-site="${site}">${f}</a>`;
          }).join("<br>")
        : "";

      html += `<td style="white-space:normal; vertical-align:top">${cell}</td>`;
    }
    html += `</tr>`;
  }

  html += `</tbody></table></div>`;

  html += `
<style>
  .open-eng-legals-btn { background:#1f6feb; border-color:#1f6feb; color:#fff; }
  .near-expire-grid { border-collapse: separate; }
  .near-expire-grid .sticky-col {
    position: sticky; left: 0; background: #fff; z-index: 2;
    min-width: 140px; box-shadow: 2px 0 5px rgba(0,0,0,0.05);
  }
  .near-expire-grid thead .sticky-col { z-index: 3; background: #f8f9fa; }
  .near-expire-grid a.near-expire-fleet { text-decoration: underline; }
</style>
`;

  wrapper.html(html);

  // Populate Site dropdown from rows
  const siteSet = new Set((rows || []).map(r => (r.site || "").trim()).filter(Boolean));
  const sites = ["All Sites", ...Array.from(siteSet).sort()];

  const $site = wrapper.find("#near-expire-site");
  $site.empty();
  sites.forEach(s => $site.append(`<option value="${frappe.utils.escape_html(s)}">${frappe.utils.escape_html(s)}</option>`));

  // defaults: remembered > doc.site > All Sites
  const rememberedSite = (frm.__near_expire_site || "").trim();
  const docSite = (frm.doc.site || "").trim();
  const defaultSite = (rememberedSite && sites.includes(rememberedSite)) ? rememberedSite
                    : (docSite && sites.includes(docSite)) ? docSite
                    : "All Sites";
  $site.val(defaultSite);

  const $range = wrapper.find("#near-expire-range");
  const rememberedRange = parseInt(frm.__near_expire_range || range_days || 7, 10);
  $range.val(String(ranges.includes(rememberedRange) ? rememberedRange : 7));

  // open Engineering Legals Report (Query Report)
  wrapper.find("#open-eng-legals-report").on("click", () => {
    const site = $site.val();
    const params = {
      as_at_date: frappe.datetime.get_today(),
      view: "Summary"
    };
    if (site && site !== "All Sites") params.site = site;

    frappe.set_route("query-report", "Engineering Legals Report", params);
  });

  // re-run query when controls change
  $site.on("change", () => set_near_expire_table(frm, $site.val(), parseInt($range.val(), 10)));
  $range.on("change", () => set_near_expire_table(frm, $site.val(), parseInt($range.val(), 10)));

  // click fleet => open filtered list
  wrapper.find(".near-expire-fleet").on("click", function (e) {
    e.preventDefault();
    const fleet = $(this).data("fleet");
    const sec = $(this).data("sec");
    const site = $site.val();

    const route_opts = { fleet_number: fleet, sections: sec };
    if (site && site !== "All Sites") route_opts.site = site;

    frappe.set_route("List", "Engineering Legals", route_opts);
  });
}









function get_near_expire_rows(frm, selected_site, range_days, callback) {
  const today = frappe.datetime.get_today();
  const end = frappe.datetime.add_days(today, (parseInt(range_days || 7, 10) - 1));

  const base = [
    ["expiry_date", "is", "set"],
    ["docstatus", "<", 2]
  ];

  if (selected_site && selected_site !== "All Sites") {
    base.push(["site", "=", selected_site]);
  }

  const due_filters = [...base, ["expiry_date", "between", [today, end]]];
  const overdue_filters = [...base, ["expiry_date", "<", today]];

  // 1) overdue
  frappe.call({
    method: "frappe.client.get_list",
    args: {
      doctype: "Engineering Legals",
      fields: ["name", "sections", "fleet_number", "expiry_date", "site"],
      filters: overdue_filters,
      limit_page_length: 1000
    },
    callback: (r1) => {
      const overdue = r1.message || [];

      // 2) due window
      frappe.call({
        method: "frappe.client.get_list",
        args: {
          doctype: "Engineering Legals",
          fields: ["name", "sections", "fleet_number", "expiry_date", "site"],
          filters: due_filters,
          limit_page_length: 1000
        },
        callback: (r2) => {
          const due = r2.message || [];
          callback([...(overdue || []), ...(due || [])]);
        }
      });
    }
  });
}
