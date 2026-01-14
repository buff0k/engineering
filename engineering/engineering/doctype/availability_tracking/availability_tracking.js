// engineering/engineering/doctype/availability_tracking/availability_tracking.js

frappe.ui.form.on("Availability Tracking", {
  onload(frm) {
    ensure_default_month(frm);
    render_month_picker(frm);

    // When opening an existing doc, ensure table is filled
    maybe_build_fridays(frm);
  },

  refresh(frm) {
    ensure_default_month(frm);
    render_month_picker(frm);

    maybe_build_fridays(frm);
    draw_monthly_chart(frm);
    draw_yearly_chart(frm);
  },

  month(frm) {
    render_month_picker(frm);

    // When user changes month, rebuild Fridays
    build_fridays_for_month(frm, { force: true });
    draw_monthly_chart(frm);
    draw_yearly_chart(frm);
  },

  target_percentage(frm) {
    draw_monthly_chart(frm);
    draw_yearly_chart(frm);
  },

  weekly_entries_add(frm) {
    draw_monthly_chart(frm);
  },

  weekly_entries_remove(frm) {
    draw_monthly_chart(frm);
  },
});


frappe.ui.form.on("Availability Tracking Entry", {
  uitgevallen(frm) {
    draw_monthly_chart(frm);
  },
  koppie(frm) {
    draw_monthly_chart(frm);
  },
  bankfontein(frm) {
    draw_monthly_chart(frm);
  },
});

// -------------------- Friday row builder --------------------

function maybe_build_fridays(frm) {
  if (!frm.doc.month) return;
  if (!frm.doc.weekly_entries || frm.doc.weekly_entries.length === 0) {
    build_fridays_for_month(frm, { force: true });
  }
}

function build_fridays_for_month(frm, { force = false } = {}) {
  if (!frm.doc.month) return;

  if (!force && frm.doc.weekly_entries && frm.doc.weekly_entries.length) {
    return;
  }

  // Clear existing rows
  frm.clear_table("weekly_entries");

  const m = moment(frm.doc.month);
  const start = m.clone().startOf("month");
  const end = m.clone().endOf("month");

  // Find first Friday in the month
  let d = start.clone();
  while (d.day() !== 5) { // Friday = 5 (Sun=0)
    d.add(1, "day");
  }

  // Add each Friday
  while (d.isSameOrBefore(end, "day")) {
    const row = frm.add_child("weekly_entries");
    row.friday_date = d.format("YYYY-MM-DD");
    d.add(7, "days");
  }

  frm.refresh_field("weekly_entries");
}

// -------------------- Charts --------------------

function get_target(frm) {
  return flt(frm.doc.target_percentage || 85);
}

function clear_html_field(frm, fieldname) {
  const f = frm.get_field(fieldname);
  if (!f || !f.$wrapper) return null;
  f.$wrapper.empty();
  return f.$wrapper.get(0);
}

function draw_monthly_chart(frm) {
  const wrapper = clear_html_field(frm, "monthly_graph");
  if (!wrapper) return;

  const rows = (frm.doc.weekly_entries || [])
    .slice()
    .sort((a, b) => (a.friday_date || "").localeCompare(b.friday_date || ""));

  if (!rows.length) {
    wrapper.innerHTML = `<div class="text-muted">Select a month to generate Fridays.</div>`;
    return;
  }

  const labels = rows.map((r) => r.friday_date || "");
  const uit = rows.map((r) => (r.uitgevallen == null ? null : flt(r.uitgevallen)));
  const kop = rows.map((r) => (r.koppie == null ? null : flt(r.koppie)));
  const ban = rows.map((r) => (r.bankfontein == null ? null : flt(r.bankfontein)));

  const target = get_target(frm);
  const target_line = rows.map(() => target);

  new frappe.Chart(wrapper, {
    title: "Monthly Availability",
    data: {
      labels,
      datasets: [
        { name: "Uitgevallen", values: uit },
        { name: "Koppie", values: kop },
        { name: "Bankfontein", values: ban },
        { name: "Target %", values: target_line },
      ],
    },
    type: "line",
    height: 280,
    axisOptions: { xAxisMode: "tick", xIsSeries: true },
    lineOptions: { hideDots: 0, regionFill: 0 },
    colors: ["#ff7aa2", "#5b7cfa", "#2ecc71", "#ff0000"],
    tooltipOptions: {
      formatTooltipX: (d) => d,
      formatTooltipY: (d) => `${d}%`,
    },
  });
}

function draw_yearly_chart(frm) {
  const wrapper = clear_html_field(frm, "yearly_graph");
  if (!wrapper) return;

  if (!frm.doc.month) {
    wrapper.innerHTML = `<div class="text-muted">Select a Month to see the yearly graph.</div>`;
    return;
  }

  const year = moment(frm.doc.month).year();
  const target = get_target(frm);

  wrapper.innerHTML = `<div class="text-muted">Loading yearly graph...</div>`;

  frappe.call({
    method:
      "engineering.engineering.doctype.availability_tracking.availability_tracking.get_yearly_availability",
    args: { year },
    callback: (r) => {
      const data = r.message;
      if (!data) {
        wrapper.innerHTML = `<div class="text-danger">Could not load yearly data.</div>`;
        return;
      }

      clear_html_field(frm, "yearly_graph");
      const target_line = (data.labels || []).map(() => target);

      new frappe.Chart(wrapper, {
        title: `Yearly Availability (${year})`,
        data: {
          labels: data.labels || [],
          datasets: [
            { name: "Uitgevallen", values: data.uitgevallen || [] },
            { name: "Koppie", values: data.koppie || [] },
            { name: "Bankfontein", values: data.bankfontein || [] },
            { name: "Target %", values: target_line },
          ],
        },
        type: "line",
        height: 280,
        axisOptions: { xAxisMode: "tick", xIsSeries: true },
        lineOptions: { hideDots: 0, regionFill: 0 },
        colors: ["#ff7aa2", "#5b7cfa", "#2ecc71", "#ff0000"],
        tooltipOptions: {
          formatTooltipX: (d) => d,
          formatTooltipY: (d) => `${d}%`,
        },
      });
    },
    error: () => {
      wrapper.innerHTML = `<div class="text-danger">Server error while loading yearly data.</div>`;
    },
  });
}

// -------------------- Month Picker (HTML field: month_html) --------------------

function ensure_default_month(frm) {
  // On new docs, default to current month if empty
  if (frm.is_new() && !frm.doc.month) {
    const val = moment().startOf("month").format("YYYY-MM-DD");
    frm.set_value("month", val);
  }
}

function render_month_picker(frm) {
  const f = frm.get_field("month_html");
  if (!f || !f.$wrapper) return;

  const selected = frm.doc.month ? moment(frm.doc.month) : moment().startOf("month");
  const year = selected.year();
  const selected_month = selected.month(); // 0..11

  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

  f.$wrapper.empty();

  const $root = $(`<div class="at-month-picker"></div>`).appendTo(f.$wrapper);

  $(`
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
      <button class="btn btn-xs btn-default" data-action="prev_year">◀</button>
      <div style="font-weight:600;">${year}</div>
      <button class="btn btn-xs btn-default" data-action="next_year">▶</button>
    </div>
  `).appendTo($root);

  const $grid = $(`<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:8px;"></div>`).appendTo($root);

  months.forEach((m, idx) => {
    const cls = idx === selected_month ? "btn btn-sm btn-primary" : "btn btn-sm btn-default";
    $grid.append(`<button class="${cls}" data-month="${idx}">${m}</button>`);
  });

  $root.on("click", "button", (e) => {
    const $btn = $(e.currentTarget);
    const action = $btn.data("action");

    if (action === "prev_year") {
      set_month(frm, year - 1, selected_month);
      return;
    }
    if (action === "next_year") {
      set_month(frm, year + 1, selected_month);
      return;
    }

    const month_idx = $btn.data("month");
    if (month_idx === undefined || month_idx === null) return;

    set_month(frm, year, month_idx);
  });
}

function set_month(frm, year, month_idx) {
  // Store ONE date value: first day of selected month
  const val = moment({ year: year, month: month_idx, day: 1 }).format("YYYY-MM-DD");
  frm.set_value("month", val);
}
