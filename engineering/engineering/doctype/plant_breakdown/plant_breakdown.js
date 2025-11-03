frappe.ui.form.on('Plant Breakdown', {
  setup(frm) {
    // Prevent manual edits to status; only drag-and-drop can change it
    frm.set_df_property('breakdown_status', 'read_only', 1);
    // Filter asset_name Link by Site
    frm.set_query('asset_name', () => ({ filters: { location: frm.doc.location || '' } }));
  },

  location(frm) {
    // Re-render when Site changes (Link field auto-filters)
    render_breakdown_ui(frm);
  },

  refresh(frm) {
    // Always re-render zones
    render_breakdown_ui(frm);
    // Seal form when resolved
    if (frm.doc.breakdown_status === '3') {
      frm.disable_form();
    }
  },

  asset_name(frm) {
    // Re-render when Plant No. changes
    render_breakdown_ui(frm);
  }
});

/** Render the three-zone drag & drop interface */
function render_breakdown_ui(frm) {
  const wrap = frm.get_field('breakdown_situation').$wrapper.empty();
  if (!frm.doc.location || !frm.doc.asset_name) {
    wrap.html('<p><em>Select Site and Plant No. to view situation.</em></p>');
    return;
  }

  // Zone definitions
  const defs = {
    green:  { label: '🟢 In Production', bg: '#e6ffe6', bd: '#b3ffb3' },
    red:    { label: '🔴 Breakdown/Planned Maintenance',     bg: '#ffe6e6', bd: '#ffb3b3' },
    yellow: { label: '🟡 Workshop',      bg: '#fff9e6', bd: '#ffe38a' }
  };

  // Build container
  const container = $('<div style="display:flex;gap:12px;"></div>').appendTo(wrap);
  Object.entries(defs).forEach(([zone, cfg]) => {
    const col = $(
      `<div style="flex:1;padding:8px;background:${cfg.bg};border:1px solid ${cfg.bd};border-radius:4px;">
         <h4>${cfg.label}</h4>
         <ul class="zone-list" data-zone="${zone}" style="min-height:60px;list-style:none;padding:0;margin:0;"></ul>
       </div>`
    );
    container.append(col);
  });

  // Determine zone by breakdown_status
  let zone = 'green';
  if (frm.doc.breakdown_status === '1') zone = 'red';
  else if (frm.doc.breakdown_status === '2') zone = 'yellow';

  // Render the asset item
  const label = `🚜 ${frm.doc.asset_name}${frm.doc.item_name ? ' — ' + frm.doc.item_name : ''}`;
  const li = $(`<li data-asset="${frm.doc.asset_name}" class="zone-item" style="margin:4px;padding:6px;background:#fff;border:1px solid #ddd;border-radius:3px;cursor:move;">${label}</li>`);
  wrap.find(`.zone-list[data-zone="${zone}"]`).append(li);

  // Wire up drag & drop
  enableDragAndDrop(frm);
}

/** Enable drag-and-drop with allowed transitions */
function enableDragAndDrop(frm) {
    // 🚫 once status is 3 (Resolved), disable all further drag-and-drop
  if (frm.doc.breakdown_status === '3') {
    return;
  }
  const allowed = { green: ['red'], red: ['yellow'], yellow: ['green'] };
  $('.zone-list').each(function() {
    Sortable.create(this, {
      group: 'breakdown',
      animation: 150,
      onAdd(evt) {
        const from = evt.from.dataset.zone;
        const to = evt.to.dataset.zone;
        if (!allowed[from] || !allowed[from].includes(to)) {
          frappe.msgprint(__('Cannot move from {0} to {1}', [from, to]));
          return render_breakdown_ui(frm);
        }
        // Handle transition prompts and save
        handleZoneTransition(frm, to).then(() => {
          frm.save().then(() => {
            frm.refresh_field('breakdown_history');
            render_breakdown_ui(frm);
          });
        });
      }
    });
  });
}

/** Prompt for details, append one history row including hours and reason */
function handleZoneTransition(frm, toZone) {
  return new Promise(resolve => {
    let newStatus, prompts = [];
    if (toZone === 'red') {
      newStatus = '1';
      prompts = [
        { fieldtype: 'Float',     fieldname: 'hours', label: 'Hours at Breakdown Start', reqd: 1 },
        { fieldtype: 'Small Text', fieldname: 'reason', label: 'Breakdown Reason',        reqd: 1 }
      ];
    } else if (toZone === 'yellow') {
      newStatus = '2';
      prompts = [
        { fieldtype: 'Data',       fieldname: 'jobcard',   label: 'Jobcard No.',            reqd: 1 },
        { fieldtype: 'Small Text', fieldname: 'work_done', label: 'Workshop Action',        reqd: 1 },
        { fieldtype: 'Datetime',   fieldname: 'eta',       label: 'ETA Back in Production', reqd: 1 }
      ];
    } else {
      newStatus = '3';
      prompts = [
        { fieldtype: 'Small Text', fieldname: 'resolution', label: 'Resolution Summary', reqd: 1 }
      ];
    }

    const appendHistory = data => {
      // Build breakdown_reason_updates string
      let reasonStr;
      if (newStatus === '1') {
        reasonStr = `Hours: ${data.hours} | ${data.reason}`;
      } else if (newStatus === '2') {
        reasonStr = `${data.jobcard} | ${data.work_done} | ETA: ${data.eta}`;
      } else {
        reasonStr = data.resolution;
      }

      // Append a single history child row
      frm.add_child('breakdown_history', {
  downtime_type: frm.doc.downtime_type || 'Plant Breakdown',
  update_by: frappe.session.user,
  update_date_time: frappe.datetime.now_datetime(),
  location: frm.doc.location,
  asset_name: frm.doc.asset_name,
  breakdown_status: newStatus,
  breakdown_reason_updates: reasonStr,
  breakdown_start_hours: (newStatus === '1' ? data.hours : frm.doc.hours_breakdown_start),
  breakdown_resolved: newStatus === '3' ? 1 : 0
});


      // Update parent doc fields
      frm.set_value('breakdown_status', newStatus);
      frm.set_value('breakdown_reason_updates', reasonStr);
      frm.refresh_field('breakdown_reason_updates');

      resolve();
    };

    // Prompt user if needed
    if (prompts.length) {
      frappe.prompt(prompts, appendHistory, __('Enter details for transition'));
    } else {
      appendHistory({});
    }
  });
}
