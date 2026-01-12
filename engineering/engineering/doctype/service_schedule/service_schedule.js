function get_dashboard_wrapper(frm) {
    // Prefer the actual HTML field
    if (frm.fields_dict.service_schedule && frm.fields_dict.service_schedule.$wrapper) {
        return frm.fields_dict.service_schedule.$wrapper;
    }
    // Fallback (should not be needed, but safe)
    if (frm.fields_dict.service_schedule_dashboard && frm.fields_dict.service_schedule_dashboard.$wrapper) {
        return frm.fields_dict.service_schedule_dashboard.$wrapper;
    }
    return null;
}

frappe.ui.form.on("Service Schedule", {
    refresh(frm) {


// Hide Service Schedule Child table (UI only)
if (frm.fields_dict.service_schedule_child) {
    frm.fields_dict.service_schedule_child.$wrapper.show();
}


frm.add_custom_button("Rebuild (Current Code)", () => {
    frappe.call({
        method: "engineering.engineering.doctype.service_schedule.service_schedule.rebuild_service_schedule",
        args: { name: frm.doc.name },
        freeze: true,
        callback: () => frm.reload_doc()
    });
});


        render_month_selector(frm);
        frm.set_df_property("month", "read_only", 1);

frm.add_custom_button("Run Daily Update", () => {
    if (frm.__ss_updating) return;
    frm.__ss_updating = true;

    frappe.call({
        method: "engineering.engineering.doctype.service_schedule.service_schedule.queue_service_schedule_update",
        args: {
            schedule_name: frm.doc.name,
            daily_usage_default: 15
        },
        freeze: true,
        freeze_message: "Queueing Service Schedule Update...",
        callback: () => {
            frm.__ss_updating = false;

            // reload so MSRs + planned fields show without deleting
            frm.reload_doc().then(() => {
                const dashWrapper = get_dashboard_wrapper(frm);
                if (dashWrapper) render_service_board(frm);
                if (frm.fields_dict.dashboard_summary && frm.fields_dict.dashboard_summary.$wrapper) {
                    render_due_soon_summary(frm);
                }
            });

            frappe.msgprint("Update queued and refreshed.");
        },
        error: () => {
            frm.__ss_updating = false;
        }
    });
});


        // style history grid
        

        // render dashboard if the fields exist on the form
        const dashWrapper = get_dashboard_wrapper(frm);
        if (dashWrapper) {
            console.log("🧪 render_service_board called", {
                child_rows: (frm.doc.service_schedule_child || []).length,
                history_rows: (frm.doc.service_schedule_history || []).length,
                has_service_schedule_field: !!frm.fields_dict.service_schedule,
                has_service_schedule_dashboard_field: !!frm.fields_dict.service_schedule_dashboard
            });
            render_service_board(frm);
        }

        if (frm.fields_dict.dashboard_summary && frm.fields_dict.dashboard_summary.$wrapper) {
            render_due_soon_summary(frm);
        }
    },

    site(frm) {
        if (!frm.doc.site) return;
        if (!frm.doc.month) {
            frappe.msgprint("Please select a Month first.");
            return;
        }
        generate_service_schedule(frm);
    },

    month(frm) {
        if (frm.doc.month && frm.doc.site) generate_service_schedule(frm);
    },

    create_ss_dashboard(frm) {
        const dashWrapper = get_dashboard_wrapper(frm);
        if (dashWrapper) {
            render_service_board(frm);
        }

        if (frm.fields_dict.dashboard_summary && frm.fields_dict.dashboard_summary.$wrapper) {
            render_due_soon_summary(frm);
        }
    }
});





// ---------------------------------------------------------------------------
// AUTO SAVE BEFORE GENERATION
// ---------------------------------------------------------------------------
function generate_service_schedule(frm) {
    if (frm.is_new()) {
        frm.save().then(() => run_backend_generation(frm));
    } else {
        run_backend_generation(frm);
    }
}


function run_backend_generation(frm) {
    frappe.call({
        method: "engineering.engineering.doctype.service_schedule.service_schedule.generate_schedule_backend",
        args: { schedule_name: frm.doc.name, daily_usage_default: 15 },
        freeze: true,
        freeze_message: "Generating Schedule...",
        callback: () => {
            frappe.model.remove_from_locals(frm.doc.doctype, frm.doc.name);

            frm.reload_doc().then(() => {
                

                const dashWrapper = get_dashboard_wrapper(frm);
                if (dashWrapper) {
                    render_service_board(frm);
                }

                if (frm.fields_dict.dashboard_summary && frm.fields_dict.dashboard_summary.$wrapper) {
                    render_due_soon_summary(frm);
                }
            });
        }
    });
}



// ---------------------------------------------------------------------------
// MONTH + YEAR PICKER (HTML field: month_picker)
// ---------------------------------------------------------------------------
function render_month_selector(frm) {
    // we need the HTML field to exist
    if (!frm.fields_dict.month_picker) return;

    const wrapper = frm.fields_dict.month_picker.$wrapper;
    wrapper.empty();

    const months = [
        "January","February","March","April","May","June",
        "July","August","September","October","November","December"
    ];

    // default year and selection
    let now = new Date();
    let currentYear = now.getFullYear();
    let selectedMonthIndex = null;

    // if month already has a value like "January 2025", use that
    if (frm.doc.month) {
        const parts = String(frm.doc.month).split(" ");
        if (parts.length === 2) {
            const name = parts[0];
            const yr = parseInt(parts[1], 10);
            if (!isNaN(yr)) {
                currentYear = yr;
            }
            const idx = months.indexOf(name);
            if (idx >= 0) {
                selectedMonthIndex = idx;
            }
        }
    }

    let html = `
        <style>
            .ss-month-selector {
                margin-bottom: 6px;
            }
            .ss-year-row {
                display: flex;
                align-items: center;
                gap: 6px;
                margin-bottom: 4px;
            }
            .ss-year-label {
                font-weight: bold;
                min-width: 60px;
                text-align: center;
            }
            .ss-month-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 4px;
            }
            .ss-month-btn {
                width: 100%;
                padding: 4px 2px;
                font-size: 11px;
                text-align: center;
            }
            .ss-month-btn.ss-selected {
                background-color: #4c6ef5;
                color: #fff;
            }
        </style>
        <div class="ss-month-selector">
            <div class="ss-year-row">
                <button type="button" class="btn btn-xs btn-default ss-year-prev">&lt;</button>
                <span class="ss-year-label">${currentYear}</span>
                <button type="button" class="btn btn-xs btn-default ss-year-next">&gt;</button>
            </div>
            <div class="ss-month-grid">
    `;

    months.forEach((m, idx) => {
        const shortName = m.substring(0, 3);
        const selClass = (selectedMonthIndex === idx) ? "ss-selected" : "";
        html += `
            <button type="button"
                    class="btn btn-default btn-xs ss-month-btn ${selClass}"
                    data-idx="${idx}">
                ${shortName}
            </button>
        `;
    });

    html += `
            </div>
        </div>
    `;

    wrapper.html(html);

    const yearLabel = wrapper.find(".ss-year-label");

    // year change buttons
    wrapper.find(".ss-year-prev").on("click", function() {
        currentYear -= 1;
        yearLabel.text(currentYear);
    });

    wrapper.find(".ss-year-next").on("click", function() {
        currentYear += 1;
        yearLabel.text(currentYear);
    });

    // month click: set Month field and optionally generate schedule
    wrapper.find(".ss-month-btn").on("click", function() {
        const idx = parseInt($(this).data("idx"), 10);
        selectedMonthIndex = idx;

        // highlight selected month
        wrapper.find(".ss-month-btn").removeClass("ss-selected");
        $(this).addClass("ss-selected");

        // set the hidden month field, e.g. "October 2025"
        const label = months[idx] + " " + currentYear;
        frm.set_value("month", label);

        // if site is already chosen, generate the schedule now
        if (frm.doc.site) {
            generate_service_schedule(frm);
        }
    });
}


// ----------------------------
// OVERDUE (50 hours AFTER the interval cell) - recomputed every render (NO localStorage)
// Rule:
//  - Find each interval cell (interval-250/500/750/1000/2000)
//  - Read that cell's Est (serviceEst)
//  - Overdue threshold = serviceEst + 50
//  - Mark the FIRST later cell where Est >= threshold as .overdue
// ----------------------------
function apply_overdue_highlights(frm, assets) {

    assets.forEach(a => {
        const fleet = a.fleet_number;

        // All day cells for this fleet, sorted by date
        const cells = $(`.day-cell[data-asset="${fleet}"]`)
            .toArray()
            .sort((x, y) => String($(x).data("date")).localeCompare(String($(y).data("date"))))
            .map(el => $(el));

        if (!cells.length) return;

        // Clear previous overdue marks (because we recompute every time)
        cells.forEach(c => c.removeClass("overdue"));

        // Helper: is this an interval cell?
        const isIntervalCell = (cell) => {
            const cls = cell.attr("class") || "";
            return (
                cls.includes("interval-250") ||
                cls.includes("interval-500") ||
                cls.includes("interval-750") ||
                cls.includes("interval-1000") ||
                cls.includes("interval-2000")
            );
        };

        // For each interval cell, mark the first cell 50 hours after it
        for (let i = 0; i < cells.length; i++) {
            const intervalCell = cells[i];
            if (!isIntervalCell(intervalCell)) continue;

            const estText = (intervalCell.find(".est-val").text() || "").trim();
            const serviceEst = estText ? parseFloat(estText) : NaN;
            if (isNaN(serviceEst)) continue;

            const threshold = serviceEst + 50;


            // Window end = next interval anchor (or end of cells)
            let endIdx = cells.length;
            for (let k = i + 1; k < cells.length; k++) {
                if (isIntervalCell(cells[k])) {
                    endIdx = k;
                    break;
                }
            }

            // If serviced (green border) anywhere in this interval window, suppress overdue for this interval
            const servicedInWindow = cells.slice(i, endIdx).some(c => c.hasClass("ss-green-border"));
            if (servicedInWindow) {
                continue; // skip overdue marking for THIS interval anchor
            }
           


            // Find first later cell where Est >= threshold
            for (let j = i + 1; j < endIdx; j++) {
                const nextCell = cells[j];
                const nextEstText = (nextCell.find(".est-val").text() || "").trim();
                const nextEst = nextEstText ? parseFloat(nextEstText) : NaN;
                if (isNaN(nextEst)) continue;

                if (nextEst >= threshold) {
                    nextCell.addClass("overdue");
                    break; // only the first overdue cell after THIS interval cell
                }
            }
        }
    });
}




// ---------------------------------------------------------------------------
// GRID RENDERER
// ---------------------------------------------------------------------------
function render_service_board(frm) {

    let rows = frm.doc.service_schedule_child || [];




    if (!rows.length) {
        const dashWrapper = get_dashboard_wrapper(frm);
        if (dashWrapper) dashWrapper.html("<p>No data.</p>");
        return;
    }

let assetMap = {};

// NEW: collect MSR info per fleet from anywhere in the child rows
const msrInfoByFleet = {};
rows.forEach(r => {
    const fleet = r.fleet_number;
    if (!fleet) return;
    if (!msrInfoByFleet[fleet]) msrInfoByFleet[fleet] = [];

    if (r.msr_record_name || r.msr_reference_number) {
        msrInfoByFleet[fleet].push({
            msr_reference_number: r.msr_reference_number || "",
            msr_record_name: r.msr_record_name || "",
            row_date: r.date ? String(r.date).slice(0, 10) : ""
        });
    }
});

rows.forEach(r => {
    if (!assetMap[r.fleet_number]) {
    assetMap[r.fleet_number] = {
        fleet_number: r.fleet_number,
        model: r.model,
        asset_category: r.asset_category,
        daily_estimated_hours_usage: r.daily_estimated_hours_usage,

        service_date: null,   // ✅ start blank, we’ll fill it from the correct rows
        hours_previous_service: r.hours_previous_service,
        last_service_interval: r.last_service_interval,

        date_of_next_service_1: null,
        planned_hours_next_service_1: null,
        next_service_interval_1: null,
        date_of_next_service_2: null,
        planned_hours_next_service_2: null,
        next_service_interval_2: null,
        date_of_next_service_3: null,
        planned_hours_of_service_3: null,
        next_service_interval_3: null,

        msr_reference_number: r.msr_reference_number,
        msr_record_name: r.msr_record_name,

        // NEW: actual MSR events keyed by dateStr ("YYYY-MM-DD")
        msr_events: {},

        days: {}


    };
}

// Track the latest previous service date (for display if you still want it)
if (r.date_of_previous_service) {
    const newDate = String(r.date_of_previous_service).slice(0, 10);
    const oldDate = assetMap[r.fleet_number].service_date
        ? String(assetMap[r.fleet_number].service_date).slice(0, 10)
        : null;

    if (!oldDate || newDate > oldDate) {
        assetMap[r.fleet_number].service_date = newDate;

        // ✅ keep MSR link details aligned to the latest MSR
        assetMap[r.fleet_number].msr_reference_number = r.msr_reference_number || "";
        assetMap[r.fleet_number].msr_record_name = r.msr_record_name || "";

        // ✅ IMPORTANT: keep these aligned to the latest MSR too
        if (r.hours_previous_service != null) {
            assetMap[r.fleet_number].hours_previous_service = r.hours_previous_service;
        }
        if (r.last_service_interval != null) {
            assetMap[r.fleet_number].last_service_interval = r.last_service_interval;
        }
    }
}

// NEW: record MSR events by the MSR date itself (date_of_previous_service),
// not by relying on rowDate matching.
const msrDate = r.date_of_previous_service ? String(r.date_of_previous_service).slice(0, 10) : "";

if (msrDate) {
    // Prefer MSR info on the same row, otherwise fallback to any MSR info found for this fleet
    const directRef = r.msr_reference_number || "";
    const directName = r.msr_record_name || "";

    let ref = directRef;
    let name = directName;

    if ((!ref || !name) && msrInfoByFleet[r.fleet_number] && msrInfoByFleet[r.fleet_number].length) {
        // Pick the latest MSR info we saw (last one in list)
        const last = msrInfoByFleet[r.fleet_number][msrInfoByFleet[r.fleet_number].length - 1];
        ref = ref || last.msr_reference_number || "";
        name = name || last.msr_record_name || "";
    }

    // Store event if we have EITHER ref or name
    if (ref || name) {
        assetMap[r.fleet_number].msr_events[msrDate] = {
            msr_reference_number: ref,
            msr_record_name: name
        };
    }

}



assetMap[r.fleet_number].days[r.date] = {
    start: r.start_hours,
    est: r.estimate_hours,
};


// Capture next service markers (these fields are only set on the specific day that crosses the threshold)
if (r.date_of_next_service_1) {
    assetMap[r.fleet_number].date_of_next_service_1 = String(r.date_of_next_service_1).slice(0, 10);
    assetMap[r.fleet_number].planned_hours_next_service_1 = r.planned_hours_next_service_1;
    assetMap[r.fleet_number].next_service_interval_1 = r.next_service_interval_1;
}
if (r.date_of_next_service_2) {
    assetMap[r.fleet_number].date_of_next_service_2 = String(r.date_of_next_service_2).slice(0, 10);
    assetMap[r.fleet_number].planned_hours_next_service_2 = r.planned_hours_next_service_2;
    assetMap[r.fleet_number].next_service_interval_2 = r.next_service_interval_2;
}
if (r.date_of_next_service_3) {
    assetMap[r.fleet_number].date_of_next_service_3 = String(r.date_of_next_service_3).slice(0, 10);
    assetMap[r.fleet_number].planned_hours_of_service_3 = r.planned_hours_of_service_3;
    assetMap[r.fleet_number].next_service_interval_3 = r.next_service_interval_3;
}


});


    let assets = Object.values(assetMap);
    

    // Order in which Plant Types (asset_category) should appear
    const categoryOrder = {
        "ADT": 1,
        "Dozer": 2,
        "Excavator": 3,
        "Service Truck": 4,
        "Diesel Bowsers": 5
    };

    assets.sort((a, b) => {
        const ca = categoryOrder[a.asset_category] || 999;
        const cb = categoryOrder[b.asset_category] || 999;

        // First sort by Plant Type order
        if (ca !== cb) return ca - cb;

        // Then sort by fleet number within the same Plant Type
        return String(a.fleet_number).localeCompare(String(b.fleet_number));
    });


    // Month parsing
    let year, month_index, month_name;
    let m = frm.doc.month || "";

    if (m.includes("-")) {
        let d = new Date(m);
        year = d.getFullYear();
        month_index = d.getMonth() + 1;
        month_name = d.toLocaleString('default', { month: 'long' });
    } else {
        let [mn, ys] = m.split(" ");
        year = parseInt(ys);
        month_name = mn;
        month_index = {
            January: 1, February: 2, March: 3,
            April: 4, May: 5, June: 6,
            July: 7, August: 8, September: 9,
            October: 10, November: 11, December: 12
        }[mn];
    }

    let days = new Date(year, month_index, 0).getDate();

    
// Build a quick lookup: (fleet_number + date) -> interval (250/500/750/1000/2000)
// We only care about the rows where the backend marked the "next_service_interval_*" on that specific date.
const intervalByFleetDate = {};
(rows || []).forEach(r => {
    const fleet = r.fleet_number;
    const date  = r.date;
    if (!fleet || !date) return;

    const iv =
    (r.next_service_interval_1 || null) ||
    (r.next_service_interval_2 || null) ||
    (r.next_service_interval_3 || null);


    const ivNum = iv != null ? parseInt(iv, 10) : NaN;
    if (![250, 500, 750, 1000, 2000].includes(ivNum)) return;

    intervalByFleetDate[`${fleet}__${date}`] = ivNum;
});

    // helper: decide colour class per asset
    function getAssetClass(a) {
        let cat = a.asset_category || "";
        let model = a.model || "";
        let cls = "";

        // base on Plant Type
        if (cat === "ADT") cls = "adt-orange";
        else if (cat === "Excavator") cls = "excavator-red";
        else if (cat === "Diesel Bowsers") cls = "bowser-blue";
        else if (cat === "Dozer") cls = "dozer-green";
        else if (cat === "Service Truck") cls = "service-truck-brown";

        // special override: Merc diesel bowser
        if (model.includes("2006 Merc Benz Actros MP2") && cat === "Diesel Bowsers") {
            cls = "merc-orchid";
        }

        return cls;
    }

    // -----------------------------------------------------------------------
    // STYLES + GRID
    // -----------------------------------------------------------------------
    let html = `
    <style>
       



        /* Highlight for today's date row */
        .today-row {
            background: #93b5f0ff !important;   /* very light blue */
            box-shadow: inset 0 0 4px rgba(0,0,0,0.15);
            font-weight: bold;
        }

/* =============================
   DASHBOARD STRUCTURE (REQUIRED)
   ============================= */

.board-container {
    max-height: 650px;
}

/* THIS makes the grid exist */
.service-grid {
    display: grid;
    grid-template-columns: 180px repeat(${assets.length}, 160px);
    overflow-x: auto;
    overflow-y: auto;
    max-height: 650px;
}

/* Every dashboard cell */
.cell {
    border: 1px solid #ccc;
    padding: 5px;
    font-size: 11px;
    background: #fff;
}

/* =============================
   INTERVAL CELL BACKGROUNDS
   (250/500/750/1000/2000)
   ============================= */
.day-cell.interval-250  { background: #4c6ef5 !important; color: #fff; }
.day-cell.interval-500  { background: #ff8c12ff !important; color: #000; }
.day-cell.interval-750  { background: #e9e624ff !important; color: #000; }
.day-cell.interval-1000 { background: #ff3eb8ff !important; color: #fff; }
.day-cell.interval-2000 { background: #2c1862ff !important; color: #fff; }


/* =============================
   HISTORY ROW: Last Service Interval COLOURS
   (250/500/750/1000/2000)
   ============================= */
.cell.history-interval-250  { background: #4c6ef5 !important; color: #fff !important; }
.cell.history-interval-500  { background: #ff8c12ff !important; color: #000 !important; }
.cell.history-interval-750  { background: #e9e624ff !important; color: #000 !important; }
.cell.history-interval-1000 { background: #ff3eb8ff !important; color: #fff !important; }
.cell.history-interval-2000 { background: #2c1862ff !important; color: #fff !important; }


/* =============================
   60-HOUR PRE-WINDOW (RED BORDER)
   ============================= */
.day-cell.ss-red-border {
    border: 2px solid red !important;
}

/* =============================
   50 HOURS OVER PLANNED (OVERDUE)
   ============================= */
.day-cell.overdue {
    background: #ff4d4d !important;
    border: 2px solid #990000 !important;
}



/* =============================
   PREV SERVICE DATE (GREEN BORDER)
   ============================= */
.day-cell.ss-green-border {
    border: 4px solid #00a651 !important;      /* thicker + stronger green */
    box-sizing: border-box;
    box-shadow: inset 0 0 0 1px #ffffff;       /* makes it visible on red/orange/blue cells */
}

/* Header cells */
.header {
    font-weight: bold;
    background: #eee;
}

/* History rows visual separation */
.history-border {
    border-left: 4px solid #000 !important;
}




        .adt-orange { color: #00cc44ff !important; font-weight: bold; }        /* dark orange */
        .excavator-red { color: #910000ff !important; font-weight: bold; }    /* dark red */
        .bowser-blue { color: #1800b4ff !important; font-weight: bold; }      /* dark slate blue */
        .dozer-green { color: #c7007bff !important; font-weight: bold; }    /* your custom */
        .merc-orchid { color: #9e9c05ff !important; font-weight: bold; }    /* your custom */
        .service-truck-brown { color: #003a03ff !important; font-weight: bold; } /* Service Truck */


        


        .freeze-col {
            position: sticky;
            left: 0px;
            background: #ddd;
            z-index: 10;
        }

        .freeze-row { position: sticky; top: 0; z-index: 11; }
        .freeze-row-2 { position: sticky; top: 30px; z-index: 11; }
        .freeze-row-3 { position: sticky; top: 60px; z-index: 11; }


       


        /* --- Small legend styles --- */
        .legend-row {
            display: flex;
            gap: 12px;
            margin: 4px 0;
            font-size: 11px;
            align-items: center;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .legend-swatch {
            width: 12px;
            height: 12px;
            border: 1px solid #333;
        }

/* =============================
   LEGEND COLOURS ONLY
   ============================= */

/* Service intervals */
.legend-swatch.blue   { background: #4c6ef5; }   /* 250 */
.legend-swatch.orange { background: #ff8c12ff; } /* 500 */
.legend-swatch.yellow { background: #e9e624ff; } /* 750 */
.legend-swatch.pink   { background: #ff3eb8ff; } /* 1000 */
.legend-swatch.purple { background: #2c1862ff; } /* 2000 */

/* Status indicators */
.legend-swatch-overdue {
    background: #ff4d4d;
}

.legend-swatch-red-border {
    background: #ffffff;
    border: 2px solid red;
}

.legend-swatch-green-border {
    background: #ffffff;
    border: 4px solid #00a651;
    box-sizing: border-box;
}





                /* NEW INPUT STYLE */
        .daily-usage-input {
            width: 100%;
            font-size: 10px;
            padding: 2px;
            box-sizing: border-box;
        }





        /* ---------------------------- */

        .split-block {
            text-align:left;
            line-height:1.1em;
            padding-left:2px;
        }

       </style>

        <!-- Small colour legend (outside scroll area) -->
    <div class="legend-row">
        <div class="legend-item">
            <div class="legend-swatch blue"></div>250-hour service
        </div>
        <div class="legend-item">
    <div class="legend-swatch orange"></div>500-hour service
        </div>
        <div class="legend-item">
            <div class="legend-swatch yellow"></div>750-hour service
        </div>
       <div class="legend-item">
        <div class="legend-swatch pink"></div>1000-hour service
        </div>
        <div class="legend-item">
    <div class="legend-swatch purple"></div>2000-hour service
</div>

        <div class="legend-item">
            <div class="legend-swatch legend-swatch-overdue"></div>50 Hours over service
        </div>



        <div class="legend-item">
            <div class="legend-swatch legend-swatch-red-border"></div>50 Hours due service
        </div>
<div class="legend-item">
    <div class="legend-swatch legend-swatch-green-border"></div>Serviced date
</div>

    </div>


    <div class="board-container">
        <div class="service-grid">
    `;




    // -----------------------------------------------------------------------
    // HEADERS (3 rows)
    // -----------------------------------------------------------------------
        html += `<div class="cell header freeze-col freeze-row">Plant Name</div>`;
    assets.forEach(a => {
        let cls = getAssetClass(a);
        html += `<div class="cell header freeze-row ${cls}">${a.model}</div>`;
    });


        html += `<div class="cell header freeze-col freeze-row-2">Plant Type</div>`;
    assets.forEach(a => {
        let cls = getAssetClass(a);
        html += `<div class="cell header freeze-row-2 ${cls}">${a.asset_category}</div>`;
    });


    html += `<div class="cell header freeze-col freeze-row-3">Plant No.</div>`;
    assets.forEach(a => html += `<div class="cell header freeze-row-3">${a.fleet_number}</div>`);



    // -----------------------------------------------------------------------
    // HISTORY ROWS
    // -----------------------------------------------------------------------
    const historyRows = [
    { label: "Prev Service Date", key: "service_date" },
    { label: "Last Service Interval", key: "last_service_interval" },
];

        historyRows.forEach(row => {
        html += `<div class="cell header freeze-col history-border">${row.label}</div>`;


        assets.forEach(a => {
            let value = a[row.key] ?? "";
            let cls = "";

            // Pretty formatting for numeric interval fields
            if (String(row.key).startsWith("next_service_interval_") && value) {
                value = `${value} Hours`;
            }



// ONLY colour these history rows:
// - Last Service Interval (exact match 250/500/750/1000/2000)
// - Prev Service Hours (floor to nearest 250, then map to 250/500/750/1000/2000)
if (row.key === "last_service_interval" || row.key === "hours_previous_service") {

    // Pull a number out of the displayed value (handles "250", "250 Hours", "1013", etc.)
    const rawNum = parseFloat(String(value || "").replace(/[^\d.]/g, ""));
    let iv = isNaN(rawNum) ? NaN : rawNum;

    if (row.key === "last_service_interval") {
        // exact interval
        iv = parseInt(String(value || "").replace(/[^\d]/g, ""), 10);
    } else {
        // Prev Service Hours: floor to nearest 250
        iv = Math.floor(iv / 250) * 250;

        // cap anything >= 2000 to 2000 (so 2050, 2600 etc still become purple)
        if (iv >= 2000) iv = 2000;
    }

    if ([250, 500, 750, 1000, 2000].includes(iv)) {
        cls = ` history-interval-${iv}`;
    }
}


html += `<div class="cell history-border${cls}">${value}</div>`;

        });
    });

    // -----------------------------------------------------------------------
    // NEW ROW: Daily Estimated hours usage (editable, default = 15)
    // -----------------------------------------------------------------------
    html += `<div class="cell header freeze-col history-border">Daily Estimated hours usage</div>`;
    assets.forEach(a => {
        html += `
    <div class="cell history-border">
        <input type="number"
       class="daily-usage-input"
       data-asset="${a.fleet_number}"
       value="${(a.daily_estimated_hours_usage ?? 15)}"
       min="0"
       max="24"
       step="1" />

    </div>
`;

    });


    // -----------------------------------------------------------------------
    // DAILY GRID (SPLIT + ORANGE + RED BORDER)
    // -----------------------------------------------------------------------

    // Track, per asset, if we've already coloured
    // the first Start >= Planned Hours Next Service (background only)

// ============================
// ENGINE 5 (Dashboard Colouring)
// ============================
// Later: Engine 1..5 will apply all colouring to dashboard cells.
// For now: NO dashboard colouring applied (reset state).
// Only allowed visuals right now:
//  - Asset header colours (getAssetClass used in header rows)
//  - Today row highlight (.today-row)
//  - Legend HTML (top of board)
// ============================


    for (let d = 1; d <= days; d++) {
        // Build display label for the left "date" column
        const dateObj = new Date(year, month_index - 1, d);
        const weekday = dateObj.toLocaleString("default", { weekday: "long" });
        const display = `${d} ${month_name} – ${weekday}`;

        // Identify today so we can highlight that row
        const today = frappe.datetime.get_today();  // "YYYY-MM-DD"
        const loopDate = `${year}-${String(month_index).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
        const isToday = (today === loopDate);

        html += `<div class="cell header freeze-col ${isToday ? "today-row" : ""}">${display}</div>`;

        // One column per asset
        assets.forEach(a => {
            const dateStr = `${year}-${String(month_index).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
            const info = a.days[dateStr] || {};

            const start = info.start;
            const est   = info.est;
            

        
        // service_date might be "YYYY-MM-DD", "YYYY-MM-DD 00:00:00", Date object, or null
let serviceDate = "";

if (a.service_date) {
    if (a.service_date instanceof Date) {
        serviceDate = frappe.datetime.obj_to_str(a.service_date);
    } else {
        // force string, then take first 10 chars ("YYYY-MM-DD")
        serviceDate = String(a.service_date).slice(0, 10);
    }
}



// GREEN BORDER: only when an actual MSR exists on this date for this asset
const msrEvent = (a.msr_events && a.msr_events[dateStr]) ? a.msr_events[dateStr] : null;
if (a.fleet_number === "IS609" && dateStr === "2025-09-17") {
    console.log("🧪 IS609 2025-09-17 msrEvent", msrEvent, "all events:", a.msr_events);
}
const greenBorderClass = msrEvent ? " ss-green-border" : "";


if (a.fleet_number === "IS609") {
    console.log("🧪 IS609 BORDER CHECK", {
        dateStr,
        service_date_raw: a.service_date,
        serviceDate_normalized: serviceDate,
        match: (dateStr === serviceDate)
    });
}




if (greenBorderClass) {
    console.log("✅ GREEN BORDER HIT", {
        fleet: a.fleet_number,
        dateStr,
        service_date_raw: a.service_date,
        serviceDate_normalized: serviceDate,
        msr_ref: a.msr_reference_number,
        msr_record_name: a.msr_record_name
    });
}



const msrRef = msrEvent ? msrEvent.msr_reference_number : "";
const msrName = msrEvent ? msrEvent.msr_record_name : "";

let msrLinkHtml = "";

if (msrRef) {
    const label = `MSR:${frappe.utils.escape_html(String(msrRef))}`;

    if (msrName) {
        // clickable when we have the docname
        const route = frappe.utils.get_form_link("Mechanical Service Report", msrName);
        msrLinkHtml = `
            <br>
            <a href="${route}"
               target="_blank"
               style="color:#00cc44; font-weight:bold; text-decoration:none;">
                ${label}
            </a>
        `;
    } else {
        // text only when docname is missing
        msrLinkHtml = `
            <br>
            <span style="color:#00cc44; font-weight:bold;">
                ${label}
            </span>
        `;
    }
}



// Final cell
const iv = intervalByFleetDate[`${a.fleet_number}__${dateStr}`];
const intervalClass = iv ? ` interval-${iv}` : "";

html += `
    <div class="cell day-cell${intervalClass}${greenBorderClass}"
         data-asset="${a.fleet_number}"
         data-date="${dateStr}">
        <div class="split-block">
            Start: <span class="start-val">${start ?? ""}</span>
            <br>
            Est:   <span class="est-val">${est ?? ""}</span>
            ${msrLinkHtml}
        </div>
    </div>
`;


        }); // end assets.forEach
    } // end for d



    html += `</div></div>`;
    // ✅ Always render into an actual HTML field wrapper
    const dashField =
        frm.fields_dict.service_schedule || frm.fields_dict.service_schedule_dashboard;

    if (!dashField || !dashField.$wrapper) {
        console.warn("❌ No dashboard wrapper found (service_schedule HTML field missing)");
        return;
    }

    dashField.$wrapper.html(html);

// ---------------------------------------------------------------------------
// APPLY 60-HOUR RED BORDER WINDOW (per asset, before each interval cell)
// ---------------------------------------------------------------------------
setTimeout(() => {
    // For each asset column
    assets.forEach(a => {
        const asset = a.fleet_number;

        // Get all day cells for this asset sorted by date
        const cells = $(`.day-cell[data-asset="${asset}"]`)
            .toArray()
            .sort((x, y) => String($(x).data("date")).localeCompare(String($(y).data("date"))))
            .map(el => $(el));

        if (!cells.length) return;

        // Clear any previous red-border class before re-applying
        cells.forEach(c => c.removeClass("ss-red-border"));

        // For each interval cell, mark the previous 60-hour window
        for (let i = 0; i < cells.length; i++) {
            const cell = cells[i];

            // Is this a "service interval" cell? (has interval-250/500/750/1000/2000)
            const cls = cell.attr("class") || "";
            const isInterval =
                cls.includes("interval-250") ||
                cls.includes("interval-500") ||
                cls.includes("interval-750") ||
                cls.includes("interval-1000") ||
                cls.includes("interval-2000");

            if (!isInterval) continue;

            // Read Est from this interval cell
            const estText = (cell.find(".est-val").text() || "").trim();
            const serviceEst = estText ? parseFloat(estText) : NaN;
            if (isNaN(serviceEst)) continue;

            const lower = serviceEst - 60;

            // Walk backwards and mark cells that are within [lower, serviceEst)
            for (let j = i - 1; j >= 0; j--) {
                const prevCell = cells[j];

                const prevEstText = (prevCell.find(".est-val").text() || "").trim();
                const prevEst = prevEstText ? parseFloat(prevEstText) : NaN;
                if (isNaN(prevEst)) continue;

                if (prevEst >= lower && prevEst < serviceEst) {
                    prevCell.addClass("ss-red-border");
                } else if (prevEst < lower) {
                    // Once we are below the window, stop going further back
                    break;
                }
            }
        }
    });
}, 50);

// ---------------------------------------------------------------------------
// APPLY OVERDUE HIGHLIGHT (first cell where Est >= intervalEst + 50), recomputed every render
// ---------------------------------------------------------------------------
setTimeout(() => {
    apply_overdue_highlights(frm, assets);
}, 60);



    // Attach change handlers AFTER HTML is inserted
    setTimeout(() => {
    $(".daily-usage-input").off("input.ss").on("input.ss", function () {
    const asset = $(this).data("asset");

    // Clamp typed/spinner values to 0..24 (prevents -1 / 25 deadlocks)
    let dailyUse = parseFloat($(this).val());
    if (isNaN(dailyUse)) dailyUse = 0;
    if (dailyUse < 0) dailyUse = 0;
    if (dailyUse > 24) dailyUse = 24;

    // push the corrected value back into the input so UI matches backend
    $(this).val(dailyUse);


        const cells = $(`.day-cell[data-asset="${asset}"]`)
            .toArray()
            .sort((a, b) => String($(a).data("date")).localeCompare(String($(b).data("date"))));

        let prevStart = null;

        cells.forEach((elem, idx) => {
            const cell = $(elem);

            // start hours displayed in the grid; treat missing as 0
            const startText = cell.find(".start-val").text().trim();
            const startVal = startText ? (parseFloat(startText) || 0) : 0;

            // Task 1 estimate rule:
            // - if start_hours > 0: estimate_hours = start_hours
            // - if start_hours = 0: estimate_hours = prev day start_hours + daily_estimated_hours_usage
            let estVal = 0;
            if (startVal > 0) {
                estVal = startVal;
            } else {
                const prev = (prevStart != null ? prevStart : 0);
                estVal = prev + dailyUse;
            }

            cell.find(".est-val").text(estVal);
            prevStart = startVal; // prev day start_hours
        });

        // Persist the edited daily usage to child rows and recompute next-service markers server-side (debounced)
        window._ss_usage_timers = window._ss_usage_timers || {};
        clearTimeout(window._ss_usage_timers[asset]);
        window._ss_usage_timers[asset] = setTimeout(() => {
            frappe.call({
                method: "engineering.engineering.doctype.service_schedule.service_schedule.set_daily_usage_and_recompute",
                args: {
                    schedule_name: frm.doc.name,
                    fleet_number: asset,
                    daily_usage: dailyUse
                },
                callback: () => {
                    frm.reload_doc().then(() => {
                        render_service_board(frm);
                        if (frm.fields_dict.dashboard_summary && frm.fields_dict.dashboard_summary.$wrapper) {
                            render_due_soon_summary(frm);
                        }
                    });
                }
            });
        }, 600);
    });
}, 50);





} // end render_service_board



// ---------------------------------------------------------------------------
// "Assets almost due for service (50 hours)" SUMMARY TABLE
// ---------------------------------------------------------------------------
function render_due_soon_summary(frm) {
    let rows = frm.doc.service_schedule_child || [];
    console.log("SS child sample row:", rows && rows.length ? rows[0] : null);

    if (!rows.length) {
        frm.fields_dict.dashboard_summary.$wrapper.html("<p>No data.</p>");
        return;
    }

// Filter rows where Est Hours is within 50 hours before Planned Hours Next Service
let dueRows = rows.filter(r => {
    const plannedVal = (r.planned_hours_next_service_1 ?? r.planned_hours_next_service_2 ?? r.planned_hours_of_service_3 ?? r.planned_hours_next_service);
    const planned = plannedVal != null ? parseFloat(plannedVal) : NaN;
    const est = r.estimate_hours != null
        ? parseFloat(r.estimate_hours) : NaN;

    // Need valid values
    if (isNaN(planned) || isNaN(est) || planned <= 0) return false;

    // INCLUDE if Est is >= (planned - 50) AND < planned
    return est >= (planned - 50) && est < planned;
});


    if (!dueRows.length) {
        frm.fields_dict.dashboard_summary.$wrapper.html(
            "<p>No assets are within 50 hours of the next service.</p>"
        );
        return;
    }

    // Sort by date ascending
    dueRows.sort((a, b) => String(a.date).localeCompare(String(b.date)));



    // Format date like "1 October – Wednesday"
    function formatDisplayDate(isoDate) {
        if (!isoDate) return "";
        const d = new Date(isoDate);
        if (isNaN(d)) return isoDate;   // fallback

        const day = d.getDate();
        const monthName = d.toLocaleString("default", { month: "long" });
        const weekday = d.toLocaleString("default", { weekday: "long" });

        return `${day} ${monthName} – ${weekday}`;
    }


    let html = `
    <style>
        .due-summary-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }
        .due-summary-table th,
        .due-summary-table td {
            border: 1px solid #ccc;
            padding: 4px;
            text-align: left;
        }
        .due-summary-table th {
            background: #eee;
            font-weight: bold;
        }
        .due-summary-date { width: 120px; }
        .due-summary-interval { width: 130px; }
    </style>

       <table class="due-summary-table">
        <thead>
            <tr>
                <th class="due-summary-date">Service Date</th>
                <th class="due-summary-interval">Next Service Interval</th>
                <th>Plant No.</th>
                <th>Plant Type</th>
                <th>Model</th>
                <th>Start Hours</th>
                <th>Est Hours</th>
                <th>Planned Hours Next Service</th>
            </tr>
        </thead>
        <tbody>
    `;


    
dueRows.forEach(r => {
    // planned must be calculated HERE (was causing "planned is not defined")
    const plannedVal = (
        r.planned_hours_next_service_1 ??
        r.planned_hours_next_service_2 ??
        r.planned_hours_of_service_3 ??
        r.planned_hours_next_service
    );
    const planned = plannedVal != null ? (parseFloat(plannedVal) || 0) : 0;

    // Use interval colour on the whole row
    let colourClass = "";
    const intervalVal = (
        r.next_service_interval_1 ??
        r.next_service_interval_2 ??
        r.next_service_interval_3 ??
        r.next_service_interval
    );
    const iv = parseInt(intervalVal, 10);

    if (iv === 250) colourClass = "blue";
    else if (iv === 500) colourClass = "orange";
    else if (iv === 750) colourClass = "yellow";
    else if (iv === 1000) colourClass = "pink";
    else if (iv === 2000) colourClass = "purple";

    html += `
        <tr class="${colourClass}">
            <td>${formatDisplayDate(r.date)}</td>
            <td>${intervalVal ? (intervalVal + ' Hours') : ''}</td>
            <td><strong>${r.fleet_number || ""}</strong></td>
            <td>${r.asset_category || ""}</td>
            <td>${r.model || ""}</td>
            <td>${r.start_hours ?? ""}</td>
            <td>${r.estimate_hours ?? ""}</td>
            <td>${planned ? planned : ''}</td>
        </tr>
    `;
});

    html += `</tbody></table>`;

    frm.fields_dict.dashboard_summary.$wrapper.html(html);

    
}





