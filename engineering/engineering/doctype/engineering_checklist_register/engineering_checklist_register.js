function get_child_table_fieldname(frm) {
    const table_field = (frm.meta.fields || []).find(df =>
        df.fieldtype === 'Table' && df.options === 'Engineering Checklist Register Row'
    );
    return table_field ? table_field.fieldname : null;
}


function lock_header_fields(frm) {
    const should_lock = !frm.doc.__islocal;

    ['site', 'month', 'year'].forEach(fieldname => {
        frm.set_df_property(fieldname, 'read_only', should_lock ? 1 : 0);
        frm.refresh_field(fieldname);
    });
}


function lock_child_table(frm) {
    const child_table_fieldname = get_child_table_fieldname(frm);
    if (!child_table_fieldname) return;

    const grid = frm.fields_dict[child_table_fieldname]?.grid;
    if (!grid) return;

    grid.cannot_add_rows = true;
    grid.cannot_delete_rows = true;
    grid.wrapper.find('.grid-add-row').hide();
    grid.wrapper.find('.grid-remove-rows').hide();
}

function normalize_text(value) {
    if (value === null || value === undefined) return '';
    return String(value).replace(/\s+/g, ' ').trim();
}

function normalize_machine_type(value) {
    const text = normalize_text(value);
    const key = text.toLowerCase();

    const aliases = {
        'excavator': 'Excavator',
        'adt': 'ADT',
        'dozer': 'DOZER',

        'water bowser': 'WATER BOWSER',
        'water bowsers': 'WATER BOWSER',

        'diesel bowser': 'Diesel bowser',
        'diesel bowsers': 'Diesel bowser',

        'grader': 'GRADER',
        'tlb': 'TLB',

        'drill': 'DRILLS',
        'drills': 'DRILLS',
        'drilling': 'DRILLS',

        'ldv': 'LDV',
        'lighting plant': 'LIGHTING PLANT',
        'lightning plant': 'LIGHTING PLANT',

        'water pump': 'WATER PUMP',
        'generator': 'GENERATOR',
        'genarator': 'GENERATOR',

        'fel': 'FEL',
        'front end loader': 'FEL',
        'front-end loader': 'FEL',

        'loader': 'Loader',
        'loaders': 'Loader',

        'service truck': 'Service Truck',
        'service trucks': 'Service Truck'
    };

    return aliases[key] || text;
}

/* =========================
   LIVE ID / TITLE
   ========================= */

function build_register_live_id(frm) {
    const site = normalize_text(frm.doc.site).toUpperCase().replace(/\s+/g, '-');
    const month = normalize_text(frm.doc.month).toUpperCase().replace(/\s+/g, '-');
    const year = normalize_text(frm.doc.year).toUpperCase().replace(/\s+/g, '-');

    if (!site || !month || !year) {
        return '';
    }

    return `${site}-${month}-${year}`;
}

function update_register_live_title(frm) {
    const live_id = build_register_live_id(frm);
    if (!live_id) return;

    frm.page.set_title(live_id);

    if (frm.is_new()) {
        frm.doc.__newname = live_id;
    }
}

/* =========================
   KEEP ROW STATE WHEN FILTERING
   ========================= */

function get_row_cache_key(row) {
    const fleet_no = normalize_text(row.fleet_no);
    const machine_type = normalize_machine_type(row.machine_type);
    return `${fleet_no}||${machine_type}`;
}

function ensure_row_state_cache(frm) {
    if (!frm.__row_state_cache) {
        frm.__row_state_cache = {};
    }
    return frm.__row_state_cache;
}

const CHECKLIST_CHILD_DOCTYPE = 'Engineering Checklist Register Row';

function get_status_fieldnames() {
    const meta = frappe.get_meta(CHECKLIST_CHILD_DOCTYPE);

    return (meta.fields || [])
        .filter(df => {
            const label = (df.label || '').toLowerCase();
            const fieldname = (df.fieldname || '').toLowerCase();

            return (
                df.fieldtype === 'Select' &&
                (
                    label.includes('day') ||
                    label.includes('night') ||
                    fieldname.includes('day') ||
                    fieldname.includes('night')
                )
            );
        })
        .map(df => df.fieldname);
}

function snapshot_current_row_state(frm) {
    const child_table_fieldname = get_child_table_fieldname(frm);
    if (!child_table_fieldname) return;

    const cache = ensure_row_state_cache(frm);
    const rows = frm.doc[child_table_fieldname] || [];
    const status_fields = get_status_fieldnames();

    rows.forEach(row => {
        const key = get_row_cache_key(row);
        if (!key || key === '||') return;

        const state = {
            fleet_no: normalize_text(row.fleet_no),
            machine_type: normalize_machine_type(row.machine_type),
            item_name: normalize_text(row.item_name),
            checklist_submission: row.checklist_submission
        };

        status_fields.forEach(fieldname => {
            state[fieldname] = row[fieldname];
        });

        cache[key] = state;
    });
}

function apply_cached_row_state_to_row(frm, row) {
    const cache = ensure_row_state_cache(frm);
    const key = get_row_cache_key(row);
    const saved_state = cache[key];

    if (!saved_state) return;

    const status_fields = get_status_fieldnames();

    status_fields.forEach(fieldname => {
        if (saved_state[fieldname] !== undefined) {
            row[fieldname] = saved_state[fieldname];
        }
    });

    if (saved_state.checklist_submission !== undefined) {
        row.checklist_submission = saved_state.checklist_submission;
    }
}

/* =========================
   MONTH / YEAR DAY LOGIC
   ========================= */

function get_days_in_selected_month(frm) {
    const month_map = {
        January: 1,
        February: 2,
        March: 3,
        April: 4,
        May: 5,
        June: 6,
        July: 7,
        August: 8,
        September: 9,
        October: 10,
        November: 11,
        December: 12
    };

    const month_name = frm.doc.month;
    const year_value = parseInt(frm.doc.year, 10);

    if (!month_name || !year_value || !month_map[month_name]) {
        return 31;
    }

    const month_index = month_map[month_name];
    return new Date(year_value, month_index, 0).getDate();
}

function get_checklist_total_target(frm) {
    return get_days_in_selected_month(frm) * 2;
}

function get_checklist_check_fields_meta() {
    const meta = frappe.get_meta(CHECKLIST_CHILD_DOCTYPE);

    return (meta.fields || [])
        .filter(df => {
            if (df.fieldtype !== 'Select') return false;

            const label = (df.label || '').toLowerCase();
            const fieldname = (df.fieldname || '').toLowerCase();

            return (
                label.includes('day') ||
                label.includes('night') ||
                fieldname.includes('day') ||
                fieldname.includes('night')
            );
        })
        .map(df => {
            const source_text = `${df.label || ''} ${df.fieldname || ''}`;
            const match = source_text.match(/(\d+)/);

            return {
                fieldname: df.fieldname,
                label: df.label || df.fieldname,
                day_number: match ? parseInt(match[1], 10) : null
            };
        });
}

function get_active_check_fields(frm) {
    const days_in_month = get_days_in_selected_month(frm);

    return get_checklist_check_fields_meta()
        .filter(df => df.day_number && df.day_number <= days_in_month)
        .map(df => df.fieldname);
}

function apply_month_day_visibility(frm) {
    const child_table_fieldname = get_child_table_fieldname(frm);
    if (!child_table_fieldname) return;

    const grid = frm.fields_dict[child_table_fieldname]?.grid;
    if (!grid) return;

    const days_in_month = get_days_in_selected_month(frm);
    const fields_meta = get_checklist_check_fields_meta();

    fields_meta.forEach(df => {
        const should_hide = df.day_number && df.day_number > days_in_month;

        const $header = get_header_cell(grid, df.fieldname);
        if ($header && $header.length) {
            $header.toggleClass('checklist-hidden-day-column', !!should_hide);
        }

        (grid.grid_rows || []).forEach(grid_row => {
            const $cell = get_grid_cell_wrapper(grid_row, df.fieldname);
            if ($cell && $cell.length) {
                $cell.toggleClass('checklist-hidden-day-column', !!should_hide);
            }
        });
    });
}

/* =========================
   MACHINE FILTER
   ========================= */

function set_select_options(frm, fieldname, values) {
    let unique_values = [...new Set(
        (Array.isArray(values) ? values : [])
            .map(v => normalize_machine_type(v))
            .filter(v => v)
    )];

    const forced_machine_types = [
        'DRILLS',
        'FEL',
        'Loader',
        'Diesel bowser',
        'Service Truck'
    ];

    forced_machine_types.forEach(machine_type => {
        if (!unique_values.includes(machine_type)) {
            unique_values.push(machine_type);
        }
    });

    unique_values = unique_values.sort((a, b) => a.localeCompare(b, undefined, {
        numeric: true,
        sensitivity: 'base'
    }));

    const options = [''].concat(unique_values);

    frm.set_df_property(fieldname, 'options', options.join('\n'));
    frm.refresh_field(fieldname);
}

function natural_desc_compare(a, b) {
    return normalize_text(b).localeCompare(normalize_text(a), undefined, {
        numeric: true,
        sensitivity: 'base'
    });
}

function populate_machine_type_options(frm) {
    if (!frm.doc.site) {
        if (frm.is_new()) {
            frm.set_value('machine_type_filter', '');
        }
        set_select_options(frm, 'machine_type_filter', []);
        return Promise.resolve();
    }

    const current_value = normalize_machine_type(frm.doc.machine_type_filter);

    return frappe.call({
        method: 'engineering.engineering.doctype.engineering_checklist_register.engineering_checklist_register.get_machine_type_options',
        args: {
            site: frm.doc.site
        }
    }).then(r => {
        const types = Array.isArray(r.message) ? r.message : [];

        set_select_options(frm, 'machine_type_filter', types);

        const allowed_types = [
            ...types.map(type => normalize_machine_type(type)),
            'DRILLS',
            'FEL',
            'Loader',
            'Diesel bowser',
            'Service Truck'
        ];

        if (current_value && !allowed_types.includes(current_value)) {
            frm.set_value('machine_type_filter', '');
        }
    }).catch(err => {
        console.error('Failed to load machine type options:', err);
        frappe.msgprint(__('Failed to load Machine Type options. Check browser console.'));
    });
}

function apply_machine_type_row_visibility(frm) {
    const child_table_fieldname = get_child_table_fieldname(frm);
    if (!child_table_fieldname) return;

    const grid = frm.fields_dict[child_table_fieldname]?.grid;
    if (!grid) return;

    const selected_machine_type = normalize_machine_type(frm.doc.machine_type_filter);
    const all_rows = frm.doc[child_table_fieldname] || [];

    if (selected_machine_type && all_rows.length) {
        const required_page_length = Math.max(all_rows.length, 50);

        if (grid.grid_pagination) {
            grid.grid_pagination.page_length = required_page_length;
            grid.grid_pagination.page = 1;
        }

        grid.page_length = required_page_length;

        if (grid.df) {
            grid.df.page_length = required_page_length;
        }

        if (typeof grid.refresh === 'function') {
            grid.refresh();
        }
    }

    setTimeout(() => {
        (grid.grid_rows || []).forEach(grid_row => {
            const row_machine_type = normalize_machine_type(grid_row.doc?.machine_type);
            const should_show = !selected_machine_type || row_machine_type === selected_machine_type;

            if (grid_row.wrapper) {
                $(grid_row.wrapper).toggle(should_show);
            }

            if (grid_row.row) {
                $(grid_row.row).toggle(should_show);
            }
        });

        lock_child_table(frm);
    }, 150);
}

function load_machine_rows(frm) {
    const child_table_fieldname = get_child_table_fieldname(frm);

    if (!child_table_fieldname) {
        frappe.msgprint(__('Could not find the child table field for Engineering Checklist Register Row.'));
        return Promise.resolve();
    }

    snapshot_current_row_state(frm);

    if (!frm.doc.site) {
        frm.refresh_field(child_table_fieldname);
        update_checklist_submission_average(frm);
        lock_child_table(frm);
        return Promise.resolve();
    }

    return frappe.call({
        method: 'engineering.engineering.doctype.engineering_checklist_register.engineering_checklist_register.get_site_machines',
        args: {
            site: frm.doc.site,
            machine_type: ''
        },
        freeze: true,
        freeze_message: __('Loading submitted machines...')
    }).then(r => {
        let machines = Array.isArray(r.message) ? r.message : [];

        machines = machines
            .map(machine => ({
                fleet_no: normalize_text(machine.fleet_no),
                machine_type: normalize_machine_type(machine.machine_type),
                item_name: normalize_text(machine.item_name)
            }))
            .filter(machine => machine.fleet_no || machine.machine_type || machine.item_name)
            .sort((a, b) => natural_desc_compare(a.fleet_no, b.fleet_no));

        const existing_rows = frm.doc[child_table_fieldname] || [];
        const existing_keys = new Set();

        existing_rows.forEach(row => {
            const key = get_row_cache_key(row);

            if (key && key !== '||') {
                existing_keys.add(key);
            }
        });

        let added_count = 0;
        let updated_count = 0;

        machines.forEach(machine => {
            const machine_key = `${normalize_text(machine.fleet_no)}||${normalize_machine_type(machine.machine_type)}`;

            if (!machine_key || machine_key === '||') {
                return;
            }

            const existing_row = existing_rows.find(row => get_row_cache_key(row) === machine_key);

            if (existing_row) {
                if (!normalize_text(existing_row.item_name) && machine.item_name) {
                    existing_row.item_name = machine.item_name;
                    updated_count += 1;
                }

                apply_cached_row_state_to_row(frm, existing_row);
                return;
            }

            if (!existing_keys.has(machine_key)) {
                const row = frm.add_child(child_table_fieldname);
                row.fleet_no = machine.fleet_no;
                row.machine_type = machine.machine_type;
                row.item_name = machine.item_name;

                apply_cached_row_state_to_row(frm, row);

                existing_keys.add(machine_key);
                added_count += 1;
            }
        });

        frm.refresh_field(child_table_fieldname);
        lock_child_table(frm);

        setTimeout(() => {
            refresh_checklist_submission_ui(frm, true);
            apply_machine_type_row_visibility(frm);

            frappe.show_alert({
                message: __('Reload complete. Added {0} new machine(s). Existing captured rows were kept.', [added_count]),
                indicator: 'green'
            });
        }, 200);
    }).catch(err => {
        console.error('Failed to load machine rows:', err);
        frappe.msgprint(__('Failed to load machine rows. Check browser console.'));
    });
}

/* =========================
   CHECKLIST SUBMISSION
   ========================= */

function inject_checklist_submission_styles() {
    if (document.getElementById('checklist-submission-style-block')) return;

    const style = document.createElement('style');
    style.id = 'checklist-submission-style-block';
    style.innerHTML = `
        .engineering-checklist-grid-styled .checklist-box-red {
            background: #ffb3b8 !important;
            border: 2px solid #dc3545 !important;
            border-radius: 6px !important;
            box-shadow: inset 0 0 0 1px rgba(220, 53, 69, 0.18) !important;
        }

        .engineering-checklist-grid-styled .checklist-box-green {
            background: #8fe3b0 !important;
            border: 2px solid #198754 !important;
            border-radius: 6px !important;
            box-shadow: inset 0 0 0 1px rgba(25, 135, 84, 0.18) !important;
        }

        .engineering-checklist-grid-styled .checklist-box-offsite {
            background: #d9d9d9 !important;
            border: 2px solid #7a7a7a !important;
            border-radius: 6px !important;
            box-shadow: inset 0 0 0 1px rgba(122, 122, 122, 0.18) !important;
        }

        .engineering-checklist-grid-styled .checklist-box-breakdown {
            background: #ffd59e !important;
            border: 2px solid #fd7e14 !important;
            border-radius: 6px !important;
            box-shadow: inset 0 0 0 1px rgba(253, 126, 20, 0.18) !important;
        }

        .engineering-checklist-grid-styled .checklist-box-service {
            background: #bfe4ff !important;
            border: 2px solid #0d6efd !important;
            border-radius: 6px !important;
            box-shadow: inset 0 0 0 1px rgba(13, 110, 253, 0.18) !important;
        }

        .engineering-checklist-grid-styled .checklist-status-short {
            display: inline-block !important;
            width: 100% !important;
            text-align: center !important;
            font-weight: 800 !important;
            color: #000000 !important;
        }

        .engineering-checklist-grid-styled .checklist-submission-red {
            background: #ffb3b8 !important;
            color: #7a0010 !important;
            font-weight: 800 !important;
            border: 2px solid #dc3545 !important;
            border-radius: 6px !important;
            padding: 6px !important;
            box-shadow: inset 0 0 0 1px rgba(220, 53, 69, 0.18) !important;
        }

        .engineering-checklist-grid-styled .checklist-submission-green {
            background: #8fe3b0 !important;
            color: #0b4f2f !important;
            font-weight: 800 !important;
            border: 2px solid #198754 !important;
            border-radius: 6px !important;
            padding: 6px !important;
            box-shadow: inset 0 0 0 1px rgba(25, 135, 84, 0.18) !important;
        }

        .engineering-checklist-grid-styled .grid-heading-row,
        .engineering-checklist-grid-styled .grid-heading-row [data-fieldname],
        .engineering-checklist-grid-styled .grid-heading-row .row-index,
        .engineering-checklist-grid-styled .grid-heading-row div,
        .engineering-checklist-grid-styled .grid-heading-row span {
            color: #000000 !important;
            font-weight: 800 !important;
        }

        .engineering-checklist-grid-styled .grid-body [data-fieldname],
        .engineering-checklist-grid-styled .grid-body .row-index,
        .engineering-checklist-grid-styled .grid-body div,
        .engineering-checklist-grid-styled .grid-body span,
        .engineering-checklist-grid-styled .grid-body input,
        .engineering-checklist-grid-styled .grid-body select {
            color: #000000 !important;
            font-weight: 700 !important;
        }

        .engineering-checklist-grid-styled .checklist-top-scrollbar {
            overflow-x: auto !important;
            overflow-y: hidden !important;
            height: 18px !important;
            margin-bottom: 6px !important;
            border-bottom: 1px solid #d1d8dd !important;
        }

        .engineering-checklist-grid-styled .checklist-top-scrollbar-inner {
            height: 1px !important;
        }

        .engineering-checklist-grid-styled .form-grid {
            overflow-x: auto !important;
            overflow-y: hidden !important;
            position: relative !important;
        }

        .engineering-checklist-grid-styled .grid-body {
            overflow-x: visible !important;
            overflow-y: visible !important;
            position: relative !important;
        }

        .engineering-checklist-grid-styled .grid-heading-row {
            position: relative !important;
            z-index: 50 !important;
        }

        .engineering-checklist-grid-styled [data-fieldname],
        .engineering-checklist-grid-styled .row-index {
            box-sizing: border-box !important;
        }

        .engineering-checklist-grid-styled .checklist-frozen-cell,
        .engineering-checklist-grid-styled .checklist-frozen-header {
            position: sticky !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            background-clip: padding-box !important;
        }

        .engineering-checklist-grid-styled .checklist-frozen-cell {
            background: #ffffff !important;
        }

        .engineering-checklist-grid-styled .checklist-frozen-header {
            background: #f5f5f5 !important;
        }

        .engineering-checklist-grid-styled .checklist-frozen-divider {
            box-shadow: 2px 0 0 #d1d8dd !important;
        }

        .engineering-checklist-grid-styled .checklist-frozen-idx {
            z-index: 60 !important;
        }

        .engineering-checklist-grid-styled .checklist-frozen-fleet {
            z-index: 61 !important;
        }

        .engineering-checklist-grid-styled .checklist-frozen-machine {
            z-index: 62 !important;
        }

        .engineering-checklist-grid-styled .checklist-frozen-header.checklist-frozen-idx {
            z-index: 70 !important;
        }

        .engineering-checklist-grid-styled .checklist-frozen-header.checklist-frozen-fleet {
            z-index: 71 !important;
        }

        .engineering-checklist-grid-styled .checklist-frozen-header.checklist-frozen-machine {
            z-index: 72 !important;
        }

        .engineering-checklist-grid-styled .checklist-hidden-day-column {
            display: none !important;
        }
    `;
    document.head.appendChild(style);
}

function get_checklist_submission_fieldname() {
    const meta = frappe.get_meta(CHECKLIST_CHILD_DOCTYPE);

    const exact_field = (meta.fields || []).find(df => df.fieldname === 'checklist_submission');
    if (exact_field) return exact_field.fieldname;

    const label_field = (meta.fields || []).find(df =>
        (df.label || '').toLowerCase().includes('checklist submission')
    );
    return label_field ? label_field.fieldname : null;
}

function get_checklist_submission_average_fieldname(frm) {
    const exact_field = (frm.meta.fields || []).find(df => df.fieldname === 'checklist_submission_average');
    if (exact_field) return exact_field.fieldname;

    const label_field = (frm.meta.fields || []).find(df =>
        (df.label || '').toLowerCase().includes('checklist submission average')
    );
    return label_field ? label_field.fieldname : null;
}

function normalize_status(value) {
    return normalize_text(value).toLowerCase();
}

function is_checked(value) {
    const status = normalize_status(value);
    return status === 'submitted' || status === 'late submission';
}

function get_status_short_label(value) {
    const status = normalize_status(value);

    if (status === 'submitted') return 'SUB';
    if (status === 'late submission') return 'L/S';
    if (status === 'offsite') return 'OFF';
    if (status === 'breakdown') return 'B/D';
    if (status === 'service') return 'SER';
    return '';
}

function calculate_row_checklist_submission(frm, row) {
    const check_fields = get_active_check_fields(frm);
    const total_target = get_checklist_total_target(frm);

    let selected_count = 0;

    check_fields.forEach(fieldname => {
        if (is_checked(row[fieldname])) {
            selected_count += 1;
        }
    });

    if (!total_target) {
        return 0;
    }

    const percentage = (selected_count / total_target) * 100;
    return Number(percentage.toFixed(1));
}

function update_row_checklist_submission_values(frm) {
    const child_table_fieldname = get_child_table_fieldname(frm);
    const checklist_submission_fieldname = get_checklist_submission_fieldname();

    if (!child_table_fieldname || !checklist_submission_fieldname) return;

    const rows = frm.doc[child_table_fieldname] || [];

    rows.forEach(row => {
        row[checklist_submission_fieldname] = calculate_row_checklist_submission(frm, row);
    });

    frm.refresh_field(child_table_fieldname);
}

function parse_percentage_value(value) {
    if (typeof value === 'number') {
        return Number.isFinite(value) ? value : 0;
    }

    const text = normalize_text(value).replace('%', '');
    const number = parseFloat(text);

    return Number.isFinite(number) ? number : 0;
}

function update_checklist_submission_average(frm) {
    const child_table_fieldname = get_child_table_fieldname(frm);
    const average_fieldname = get_checklist_submission_average_fieldname(frm);

    if (!child_table_fieldname || !average_fieldname) return;

    const rows = frm.doc[child_table_fieldname] || [];

    let new_average_value = '0.0%';

    if (rows.length) {
        let total = 0;

        rows.forEach(row => {
            const row_value = row.checklist_submission !== undefined && row.checklist_submission !== null && row.checklist_submission !== ''
                ? row.checklist_submission
                : calculate_row_checklist_submission(frm, row);

            total += parse_percentage_value(row_value);
        });

        const average = total / rows.length;
        new_average_value = average.toFixed(1) + '%';
    }

    const current_value = normalize_text(frm.doc[average_fieldname]);

    if (current_value !== new_average_value) {
        frm.set_value(average_fieldname, new_average_value);
    }
}

function get_grid_cell_wrapper(grid_row, fieldname) {
    let $cell = $(grid_row.row).find(`[data-fieldname="${fieldname}"]`).first();

    if (!$cell.length) {
        $cell = $(grid_row.wrapper).find(`[data-fieldname="${fieldname}"]`).first();
    }

    if (!$cell.length) {
        $cell = $(grid_row.wrapper).find(`.${fieldname}`).first();
    }

    return $cell;
}

function get_header_cell(grid, fieldname) {
    let $cell = grid.wrapper.find(`.grid-heading-row [data-fieldname="${fieldname}"]`).first();

    if (!$cell.length) {
        $cell = grid.wrapper.find(`.grid-heading-row .${fieldname}`).first();
    }

    return $cell;
}

function get_row_index_header_cell(grid) {
    let $cell = grid.wrapper.find('.grid-heading-row .row-index').first();

    if (!$cell.length) {
        $cell = grid.wrapper.find('.grid-heading-row [data-fieldname="idx"]').first();
    }

    return $cell;
}

function get_row_index_cell(grid_row) {
    let $cell = $(grid_row.row).find('.row-index').first();

    if (!$cell.length) {
        $cell = $(grid_row.wrapper).find('.row-index').first();
    }

    if (!$cell.length) {
        $cell = $(grid_row.row).find('[data-fieldname="idx"]').first();
    }

    return $cell;
}

function reset_frozen_columns(grid) {
    grid.wrapper.find(
        '.checklist-frozen-cell, .checklist-frozen-header, .checklist-frozen-divider, ' +
        '.checklist-frozen-idx, .checklist-frozen-fleet, .checklist-frozen-machine'
    ).each(function () {
        $(this)
            .removeClass(
                'checklist-frozen-cell checklist-frozen-header checklist-frozen-divider ' +
                'checklist-frozen-idx checklist-frozen-fleet checklist-frozen-machine'
            )
            .css({
                left: '',
                minWidth: '',
                maxWidth: '',
                width: '',
                background: '',
                zIndex: '',
                boxShadow: ''
            });
    });
}

function get_effective_width($cell, fallbackWidth) {
    if (!$cell || !$cell.length) return fallbackWidth;

    const rectWidth = Math.ceil($cell.outerWidth() || 0);
    return rectWidth > 0 ? rectWidth : fallbackWidth;
}

function apply_sticky($cell, left, width, isHeader, extraClass, isLastFrozen) {
    if (!$cell || !$cell.length) return;

    $cell
        .addClass(isHeader ? 'checklist-frozen-header' : 'checklist-frozen-cell')
        .addClass(extraClass || '')
        .css({
            left: `${left}px`,
            minWidth: `${width}px`,
            maxWidth: `${width}px`,
            width: `${width}px`,
            background: isHeader ? '#f5f5f5' : '#ffffff'
        });

    if (isLastFrozen) {
        $cell.addClass('checklist-frozen-divider');
    }
}

function freeze_left_columns(frm) {
    const child_table_fieldname = get_child_table_fieldname(frm);
    if (!child_table_fieldname) return;

    const grid = frm.fields_dict[child_table_fieldname]?.grid;
    if (!grid) return;

    grid.wrapper.addClass('engineering-checklist-grid-styled');
    reset_frozen_columns(grid);

    const $idxHeader = get_row_index_header_cell(grid);
    const $fleetHeader = get_header_cell(grid, 'fleet_no');
    const $machineHeader = get_header_cell(grid, 'machine_type');

    const columns = [];

    if ($idxHeader.length) {
        columns.push({
            type: 'idx',
            className: 'checklist-frozen-idx',
            width: get_effective_width($idxHeader, 44),
            header: $idxHeader
        });
    }

    if ($fleetHeader.length) {
        columns.push({
            type: 'field',
            fieldname: 'fleet_no',
            className: 'checklist-frozen-fleet',
            width: get_effective_width($fleetHeader, 140),
            header: $fleetHeader
        });
    }

    if ($machineHeader.length) {
        columns.push({
            type: 'field',
            fieldname: 'machine_type',
            className: 'checklist-frozen-machine',
            width: get_effective_width($machineHeader, 170),
            header: $machineHeader
        });
    }

    if (!columns.length) return;

    let left = 0;

    columns.forEach((column, index) => {
        const isLastFrozen = index === columns.length - 1;

        apply_sticky(
            column.header,
            left,
            column.width,
            true,
            column.className,
            isLastFrozen
        );

        (grid.grid_rows || []).forEach(grid_row => {
            const $cell = column.type === 'idx'
                ? get_row_index_cell(grid_row)
                : get_grid_cell_wrapper(grid_row, column.fieldname);

            apply_sticky(
                $cell,
                left,
                column.width,
                false,
                column.className,
                isLastFrozen
            );
        });

        left += column.width;
    });
}

function style_row_checkbox_cells(frm) {
    const child_table_fieldname = get_child_table_fieldname(frm);
    const checklist_submission_fieldname = get_checklist_submission_fieldname();
    const check_fields = get_active_check_fields(frm);

    if (!child_table_fieldname) return;

    const grid = frm.fields_dict[child_table_fieldname]?.grid;
    if (!grid) return;

    grid.wrapper.addClass('engineering-checklist-grid-styled');

    const is_dirty = frm.is_dirty && frm.is_dirty();

    (grid.grid_rows || []).forEach(grid_row => {
        const row_doc = grid_row.doc;
        if (!row_doc) return;

        check_fields.forEach(fieldname => {
            const $cell = get_grid_cell_wrapper(grid_row, fieldname);
            if (!$cell || !$cell.length) return;

            const status = normalize_status(row_doc[fieldname]);
            const short_label = get_status_short_label(row_doc[fieldname]);

            $cell.removeClass(
                'checklist-box-red checklist-box-green checklist-box-offsite checklist-box-breakdown checklist-box-service'
            );

            if (status === 'submitted' || status === 'late submission') {
                $cell.addClass('checklist-box-green');
            } else if (status === 'offsite') {
                $cell.addClass('checklist-box-offsite');
            } else if (status === 'breakdown') {
                $cell.addClass('checklist-box-breakdown');
            } else if (status === 'service') {
                $cell.addClass('checklist-box-service');
            } else {
                $cell.addClass('checklist-box-red');
            }

            const $staticArea = $cell.find('.static-area');

            if ($staticArea.length) {
                $staticArea.html(`<span class="checklist-status-short">${short_label}</span>`);
            }
        });

        if (checklist_submission_fieldname) {
            const $submissionCell = get_grid_cell_wrapper(grid_row, checklist_submission_fieldname);

            if ($submissionCell && $submissionCell.length) {
                $submissionCell.removeClass('checklist-submission-red checklist-submission-green');

                const numeric_value = parse_percentage_value(row_doc[checklist_submission_fieldname]);
                const display_value = numeric_value ? numeric_value.toFixed(1) + '%' : '0.0%';

                const $staticArea = $submissionCell.find('.static-area');

                if (is_dirty) {
                    if ($staticArea.length) {
                        $staticArea.html('');
                    }

                    $submissionCell.removeClass('checklist-submission-red checklist-submission-green');
                    return;
                }

                if ($staticArea.length) {
                    $staticArea.html(display_value);
                }

                if (numeric_value > 0) {
                    $submissionCell.addClass('checklist-submission-green');
                } else {
                    $submissionCell.addClass('checklist-submission-red');
                }
            }
        }
    });
}

function add_top_horizontal_scrollbar(frm) {
    const child_table_fieldname = get_child_table_fieldname(frm);
    if (!child_table_fieldname) return;

    const grid = frm.fields_dict[child_table_fieldname]?.grid;
    if (!grid) return;

    grid.wrapper.addClass('engineering-checklist-grid-styled');

    const $formGrid = grid.wrapper.find('.form-grid').first();
    if (!$formGrid.length) return;

    let $topScrollbar = grid.wrapper.find('.checklist-top-scrollbar').first();

    if (!$topScrollbar.length) {
        $topScrollbar = $(`
            <div class="checklist-top-scrollbar">
                <div class="checklist-top-scrollbar-inner"></div>
            </div>
        `);

        $formGrid.before($topScrollbar);
    }

    const $topScrollbarInner = $topScrollbar.find('.checklist-top-scrollbar-inner').first();

    setTimeout(() => {
        const scrollWidth = $formGrid.get(0)?.scrollWidth || 0;
        $topScrollbarInner.css('width', `${scrollWidth}px`);
        $topScrollbar.scrollLeft($formGrid.scrollLeft());
    }, 100);

    if (!$formGrid.data('checklist-top-scroll-bound')) {
        $formGrid.data('checklist-top-scroll-bound', true);

        $formGrid.on('scroll.checklist_top_scroll', function () {
            $topScrollbar.scrollLeft($formGrid.scrollLeft());
        });

        $topScrollbar.on('scroll.checklist_bottom_scroll', function () {
            $formGrid.scrollLeft($topScrollbar.scrollLeft());
        });
    }
}

function refresh_checklist_submission_ui(frm, update_values = false) {
    inject_checklist_submission_styles();

    if (update_values) {
        update_row_checklist_submission_values(frm);
        update_checklist_submission_average(frm);
    }

    setTimeout(() => {
        add_top_horizontal_scrollbar(frm);
        apply_month_day_visibility(frm);
        style_row_checkbox_cells(frm);
        freeze_left_columns(frm);
        apply_machine_type_row_visibility(frm);
    }, 200);
}

function bind_checklist_checkbox_listener(frm) {
    if ($(frm.wrapper).data('checklist-submission-bound')) return;

    $(frm.wrapper).data('checklist-submission-bound', true);

    $(frm.wrapper).on('change', '.grid-body select', function () {
        setTimeout(() => {
            snapshot_current_row_state(frm);
            refresh_checklist_submission_ui(frm, false);
        }, 80);
    });

    $(window).off('resize.checklist_freeze').on('resize.checklist_freeze', function () {
        setTimeout(() => {
            refresh_checklist_submission_ui(frm, false);
        }, 120);
    });
}

function should_load_machine_rows(frm) {
    const child_table_fieldname = get_child_table_fieldname(frm);
    if (!child_table_fieldname) return false;

    const rows = frm.doc[child_table_fieldname] || [];

    return frm.is_new() || rows.length === 0;
}

function add_reload_machines_button(frm) {
    if (!frm.doc.site) return;

    if (frm.__reload_machines_menu_added) return;
    frm.__reload_machines_menu_added = true;

    frm.page.add_menu_item(__('Reload Machines from Submitted Assets'), function () {
        snapshot_current_row_state(frm);

        populate_machine_type_options(frm).then(() => {
            return load_machine_rows(frm);
        }).then(() => {
            refresh_checklist_submission_ui(frm, true);
            frappe.show_alert({
                message: __('Machines reloaded from Submitted Assets. Please Save.'),
                indicator: 'green'
            });
        });
    });
}



function csv_escape(value) {
    const text = value === null || value === undefined ? '' : String(value);
    return '"' + text.replace(/"/g, '""') + '"';
}

function download_csv_file(filename, rows) {
    const csv_content = 'sep=,\r\n' + rows
        .map(row => row.map(value => csv_escape(value)).join(','))
        .join('\r\n');

    const blob = new Blob(['\ufeff' + csv_content], {
        type: 'text/csv;charset=utf-8;'
    });

    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
}

function format_export_percentage(value) {
    if (value === null || value === undefined || value === '') {
        return '';
    }

    const text = normalize_text(value);

    if (text.endsWith('%')) {
        return text;
    }

    const number = parseFloat(text);

    if (!Number.isFinite(number)) {
        return text;
    }

    return number.toString() + '%';
}

function format_export_cell(fieldname, value) {
    if (value === null || value === undefined) {
        return '';
    }

    const percentage_fields = [
        'target',
        'checklist_submission'
    ];

    if (percentage_fields.includes(fieldname)) {
        return format_export_percentage(value);
    }

    return value;
}

function export_checklist_rows(frm) {
    const child_table_fieldname = get_child_table_fieldname(frm);

    if (!child_table_fieldname) {
        frappe.msgprint(__('Could not find checklist rows table.'));
        return;
    }

    const selected_machine_type = normalize_machine_type(frm.doc.machine_type_filter);
    let rows = frm.doc[child_table_fieldname] || [];

    if (selected_machine_type) {
        rows = rows.filter(row => {
            return normalize_machine_type(row.machine_type) === selected_machine_type;
        });
    }

    if (!rows.length) {
        frappe.msgprint(__('No rows available to export.'));
        return;
    }

    const child_meta = frappe.get_meta(CHECKLIST_CHILD_DOCTYPE);
    const export_fields = (child_meta.fields || [])
        .filter(df => {
            return df.fieldname &&
                !df.hidden &&
                !['Section Break', 'Column Break', 'HTML', 'Button'].includes(df.fieldtype);
        })
        .map(df => ({
            fieldname: df.fieldname,
            label: df.label || df.fieldname
        }));

    const csv_rows = [];

    csv_rows.push([
        'Register',
        frm.doc.name || '',
        'Site',
        frm.doc.site || '',
        'Month',
        frm.doc.month || '',
        'Year',
        frm.doc.year || '',
        'Machine Type Filter',
        frm.doc.machine_type_filter || '',
        'Checklist Submission Average',
        format_export_percentage(frm.doc.checklist_submission_average || '')
    ]);

    csv_rows.push([]);

    csv_rows.push(export_fields.map(df => df.label));

    rows.forEach(row => {
        csv_rows.push(export_fields.map(df => {
            return format_export_cell(df.fieldname, row[df.fieldname]);
        }));
    });

    const safe_name = normalize_text(frm.doc.name || 'Engineering Checklist Register')
        .replace(/[^\w\-]+/g, '_');

    const safe_filter = selected_machine_type
        ? '_' + selected_machine_type.replace(/[^\w\-]+/g, '_')
        : '';

    download_csv_file(`${safe_name}${safe_filter}.csv`, csv_rows);

    frappe.show_alert({
        message: __('Checklist rows exported.'),
        indicator: 'green'
    });
}

function add_export_checklist_button(frm) {
    if (frm.__export_checklist_menu_added) return;
    frm.__export_checklist_menu_added = true;

    frm.page.add_menu_item(__('Export Checklist Rows'), function () {
        export_checklist_rows(frm);
    });
}

frappe.ui.form.on('Engineering Checklist Register', {
    onload(frm) {
        update_register_live_title(frm);
        lock_header_fields(frm);
        lock_child_table(frm);
        bind_checklist_checkbox_listener(frm);

        if (frm.doc.site && should_load_machine_rows(frm)) {
            populate_machine_type_options(frm).then(() => {
                return load_machine_rows(frm);
            });
        } else if (frm.doc.site) {
            populate_machine_type_options(frm).then(() => {
                apply_machine_type_row_visibility(frm);
            });
        }
    },

    refresh(frm) {
        update_register_live_title(frm);
        lock_header_fields(frm);
        lock_child_table(frm);
        bind_checklist_checkbox_listener(frm);
        add_reload_machines_button(frm);
        add_export_checklist_button(frm);

        refresh_checklist_submission_ui(frm, false);

        if (frm.doc.site) {
            populate_machine_type_options(frm).then(() => {
                apply_machine_type_row_visibility(frm);
            });
        }
    },

    before_save(frm) {
        snapshot_current_row_state(frm);
        update_row_checklist_submission_values(frm);
        update_checklist_submission_average(frm);
    },

    after_save(frm) {
        setTimeout(() => {
            frm.doc.__unsaved = 0;
            frm.page.clear_indicator();
            frm.reload_doc();
        }, 500);
    },

    site(frm) {
        update_register_live_title(frm);
        lock_header_fields(frm);

        frm.__row_state_cache = {};
        frm.set_value('machine_type_filter', '');
        frm.set_value('checklist_submission_average', '0.0%');

        populate_machine_type_options(frm).then(() => {
            return load_machine_rows(frm);
        });
    },

    month(frm) {
        update_register_live_title(frm);
        lock_header_fields(frm);
        refresh_checklist_submission_ui(frm, false);
    },

    year(frm) {
        update_register_live_title(frm);
        lock_header_fields(frm);
        refresh_checklist_submission_ui(frm, false);
    },

    machine_type_filter(frm) {
        const cleaned_value = normalize_machine_type(frm.doc.machine_type_filter);

        if (frm.doc.machine_type_filter && frm.doc.machine_type_filter !== cleaned_value) {
            frm.set_value('machine_type_filter', cleaned_value);
            return;
        }

        snapshot_current_row_state(frm);

        setTimeout(() => {
            refresh_checklist_submission_ui(frm, false);
            apply_machine_type_row_visibility(frm);
        }, 100);
    },

    onload_post_render(frm) {
        update_register_live_title(frm);
        lock_header_fields(frm);
        bind_checklist_checkbox_listener(frm);
        refresh_checklist_submission_ui(frm, false);
    }
});

frappe.ui.form.on(CHECKLIST_CHILD_DOCTYPE, {
    form_render(frm, cdt, cdn) {
        refresh_checklist_submission_ui(frm, false);
    }
});