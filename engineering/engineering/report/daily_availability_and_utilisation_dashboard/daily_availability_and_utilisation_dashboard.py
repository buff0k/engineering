import frappe
from urllib.parse import quote
from frappe.utils import flt, getdate, add_days, date_diff

from engineering.engineering.report.availability_and_utilisation_month_end_report import (
    availability_and_utilisation_month_end_report as month_end,
)


_ = frappe._

CATEGORY_MAP = {
    "ADT": "ADT",
    "ADT's": "ADT",
    "Dozer": "Dozer",
    "Dozer's": "Dozer",
    "Excavator": "Excavator",
    "Excavator's": "Excavator",
    "Grader": "Grader",
    "Service Truck": "Service Truck",
    "TLB": "TLB",
    "Water Bowser": "Water Bowser",
    "Diesel Bowsers": "Diesel Bowsers",
    "Drills": "Drills",
    "Loader": "Loader",
}

UI_CATEGORIES = [
    "ADT",
    "Dozer",
    "Excavator",
    "Grader",
    "Service Truck",
    "TLB",
    "Water Bowser",
    "Diesel Bowsers",
    "Drills",
    "Loader",
]

UI_TITLES = {
    "ADT": "ADT",
    "Dozer": "DOZER",
    "Excavator": "EXCAVATOR",
    "Grader": "GRADER",
    "Service Truck": "SERVICE TRUCK",
    "TLB": "TLB",
    "Water Bowser": "WATER BOWSER",
    "Diesel Bowsers": "DIESEL BOWSERS",
    "Drills": "DRILLS",
    "Loader": "LOADER",
}

SITE_HEADER_COLOURS = {
    "Klipfontein": "#EBF9FF",
    "Gwab": "#F7D8FF",
    "Kriel Rehabilitation": "#E6D3B1",
    "Koppie": "#FEFF8D",
    "Uitgevallen": "#FFD37F",
    "Bankfontein": "#E3E3E3",
}


CURRENT_SPARE_SWING_ASSET_MAP = {}
CURRENT_MACHINE_SCOPE = "Include Swing/Spare"

DASH_CSS = """
<style>
.isd-hourly-dashboard {
    padding: 8px 6px 24px;
    font-family: Arial, sans-serif;
    color: #222;
}

.isd-note {
    margin: 0 0 10px;
    padding: 8px 10px;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background: #fafafa;
    font-size: 12px;
    font-weight: 700;
}

.isd-site {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    overflow: hidden;
}

.isd-site-title {
    padding: 10px 12px 8px;
    font-weight: 900;
    font-size: 13px;
}

.isd-band {
    padding: 10px 12px 12px;
    background: var(--site-colour);
    border-top: 1px solid #e8e8e8;
    border-bottom: 1px solid #e8e8e8;
}

.isd-metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
    gap: 8px;
}

.isd-metric {
    background: rgba(255,255,255,0.72);
    border: 1px solid rgba(0,0,0,0.12);
    border-radius: 10px;
    padding: 8px;
}

.isd-metric-title {
    font-size: 11px;
    font-weight: 900;
    text-transform: uppercase;
    text-align: center;
    margin-bottom: 7px;
}

.isd-pill-row {
    display: flex;
    gap: 7px;
    justify-content: center;
}

.isd-mbubble {
    width: 70px;
    min-height: 58px;
    border-radius: 999px;
    color: #fff;
    display: grid;
    place-items: center;
    text-align: center;
    padding: 7px;
    box-shadow: inset 0 0 0 2px rgba(255,255,255,0.35), 0 4px 10px rgba(0,0,0,0.10);
}

.isd-mbubble-green {
    background: rgba(30, 142, 62, 0.96);
}

.isd-mbubble-yellow {
    background: rgba(245, 166, 35, 0.96);
}

.isd-mbubble-red {
    background: rgba(217, 48, 37, 0.96);
}

.isd-mbubble-label {
    font-size: 9px;
    font-weight: 900;
    letter-spacing: 0.2px;
    line-height: 1;
    white-space: nowrap;
}

.isd-mbubble-value {
    font-size: 12px;
    font-weight: 900;
    line-height: 1.05;
    color: #fff;
}

.isd-contentrow {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 150px;
    gap: 10px;
    align-items: start;
    border-top: 1px solid #e8e8e8;
}

.isd-chart-stack {
    display: grid;
    gap: 16px;
    padding: 10px;
    overflow-x: auto;
    overflow-y: visible;
}

.isd-chart-section {
    border: 1px solid #2f2f2f;
    border-radius: 0;
    background: linear-gradient(135deg, #2b2b2b 0%, #555 48%, #2b2b2b 100%);
    overflow-x: auto;
    overflow-y: hidden;
    margin-bottom: 16px;
}

.isd-chart-section-title {
    padding: 10px;
    font-size: 22px;
    font-weight: 900;
    letter-spacing: 0.8px;
    text-align: center;
    color: #f2f2f2;
    background: transparent;
    border-bottom: 0;
    text-transform: uppercase;
    text-shadow: 0 1px 2px rgba(0,0,0,0.65);
}

.isd-chart {
    padding: 18px 18px 16px;
    position: relative;
    background: transparent;
}

.isd-yaxis {
    position: absolute;
    left: 16px;
    top: 18px;
    bottom: 56px;
    width: 34px;
    font-size: 11px;
    font-weight: 600;
    color: #ffffff;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    pointer-events: none;
}

.isd-chart-grid {
    display: grid;
    align-items: end;
    gap: 4px;
    margin-left: 42px;
    height: 270px;
    position: relative;
    border-bottom: 1px solid rgba(255,255,255,0.65);
    background:
        linear-gradient(to top, rgba(255,255,255,0.13) 1px, transparent 1px);
    background-size: 100% 27px;
}

.isd-bar {
    width: 100%;
    border-radius: 0;
    min-height: 2px;
}

.isd-bar.avail {
    background: #f4b000;
}

.isd-bar.util {
    background: #2f75b5;
}

.isd-bar.nodata {
    opacity: 0.18;
}

.isd-avgline {
    position: absolute;
    left: 60px;
    right: 18px;
    height: 4px;
    opacity: 1;
    pointer-events: none;
    z-index: 5;
}

.isd-avgline.isd-avg-85 {
    background: #ff0000;
    top: calc(18px + 270px * 0.15);
}

.isd-avgline.isd-avg-80 {
    background: #92d050;
    top: calc(18px + 270px * 0.20);
}

.isd-machinelabels {
    display: grid;
    gap: 4px;
    margin-left: 42px;
    margin-top: 8px;
    font-size: 11px;
    font-weight: 600;
    color: #ffffff;
}

.isd-machinelab {
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transform: none;
    min-height: 16px;
    padding-top: 0;
}

.isd-no-machine-data {
    padding: 18px;
    font-size: 12px;
    font-weight: 700;
    color: #ffffff;
}

.isd-side {
    display: grid;
    gap: 8px;
    padding: 10px 10px 12px;
    border-left: 1px solid #e8e8e8;
}

.isd-cards {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
}

.isd-circle {
    width: 74px;
    height: 74px;
    border-radius: 999px;
    display: grid;
    place-items: center;
    font-size: 10.5px;
    font-weight: 900;
    text-align: center;
    line-height: 1.05;
    padding: 10px 8px;
    letter-spacing: 0.2px;
    border: 2px solid rgba(0,0,0,0.22);
    box-shadow: inset 0 0 0 3px rgba(255,255,255,0.35), 0 6px 14px rgba(0,0,0,0.08);
}

.isd-open-report {
    text-decoration: none !important;
    color: #000 !important;
    cursor: pointer;
}

.isd-open-report:hover {
    transform: scale(1.03);
}

.isd-circle-green {
    border-color: rgba(30, 142, 62, 0.85);
    background: rgba(30, 142, 62, 0.18);
}

.isd-legend {
    display: grid;
    gap: 6px;
    font-size: 10px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    opacity: 0.75;
}

.isd-legitem {
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.isd-legswatch {
    width: 12px;
    height: 12px;
    border-radius: 3px;
    display: inline-block;
}

.isd-leg-avail {
    background: #f4b000;
}

.isd-leg-util {
    background: #2f75b5;
}


.isd-targets {
    display: grid;
    gap: 10px;
    margin-top: 6px;
}

.isd-target-box {
    width: 100%;
    background: #ffffff;
    border: 2px solid #222;
    border-radius: 2px;
    overflow: hidden;
}

.isd-target-title {
    background: #f1f1f1;
    color: #000;
    text-align: center;
    font-size: 12px;
    font-weight: 900;
    line-height: 1.15;
    padding: 6px 4px;
    border-bottom: 2px solid #222;
}


.isd-target-line {
    width: 58px;
    height: 5px;
    margin: 10px auto;
    border-radius: 2px;
}

.isd-target-line-red {
    background: #ff0000;
}

.isd-target-line-green {
    background: #92d050;
}

.isd-target-value {
    color: #000;
    text-align: center;
    font-size: 16px;
    font-weight: 900;
    line-height: 1;
    padding: 8px 4px;
}

.isd-open-report-wrap {
    display: flex;
    justify-content: center;
    margin-bottom: 8px;
}

@media (max-width: 900px) {
    .isd-contentrow {
        grid-template-columns: 1fr;
    }

    .isd-side {
        border-left: none;
        border-top: 1px solid #e8e8e8;
    }
}



/* Main dashboard graph alignment to match preview */
.isd-chart-section {
    width: 100% !important;
    max-width: none !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    margin: 0 0 10px 0 !important;
    border: 1px solid #222 !important;
    background: linear-gradient(135deg, #2b2b2b 0%, #555 48%, #2b2b2b 100%) !important;
}

.isd-chart-section-title {
    font-size: 22px !important;
    font-weight: 900 !important;
    color: #ffffff !important;
    text-align: center !important;
    padding: 12px 8px 8px 8px !important;
    letter-spacing: 0.5px !important;
    text-shadow: 1px 1px 2px #000000 !important;
}

.isd-chart {
    width: max-content !important;
    min-width: 100% !important;
    overflow: visible !important;
    box-sizing: border-box !important;
    padding: 14px 14px 24px 14px !important;
    background: transparent !important;
}

.isd-yaxis {
    left: 14px !important;
    top: 14px !important;
    bottom: 32px !important;
    width: 62px !important;
    height: 260px !important;
    font-size: 18px !important;
    font-weight: 900 !important;
    line-height: 1 !important;
    text-align: right !important;
    color: #ffffff !important;
    text-shadow: 1px 1px 3px #000000 !important;
    justify-content: space-between !important;
}

.isd-yaxis div {
    height: auto !important;
    line-height: 1 !important;
}

.isd-yaxis div:first-child {
    transform: translateY(-1px) !important;
}

.isd-yaxis div:last-child {
    transform: translateY(5px) !important;
}

.isd-chart-grid {
    margin-left: 84px !important;
    height: 260px !important;
    gap: 8px !important;
    border-bottom: 3px solid rgba(255,255,255,0.95) !important;
    align-items: end !important;
    padding-bottom: 0 !important;
    background:
        linear-gradient(to top, rgba(255,255,255,0.13) 1px, transparent 1px) !important;
    background-size: 100% 26px !important;
}

.isd-bar {
    border-radius: 0 !important;
    min-height: 2px !important;
    margin-bottom: 0 !important;
    align-self: end !important;
}

.isd-bar.avail {
    background: #f4b000 !important;
}

.isd-bar.util {
    background: #2f75b5 !important;
}

.isd-machinelabels {
    margin-left: 84px !important;
    margin-top: 9px !important;
    min-height: 38px !important;
    align-items: start !important;
    gap: 8px !important;
}

.isd-machinelab {
    font-size: 14px !important;
    font-weight: 900 !important;
    line-height: 1.1 !important;
    min-height: 28px !important;
    padding-top: 6px !important;
    color: #ffffff !important;
    text-shadow: 1px 1px 3px #000000 !important;
    overflow: visible !important;
    white-space: nowrap !important;
    text-overflow: clip !important;
    transform: none !important;
}

.isd-avgline {
    left: 98px !important;
    right: 14px !important;
    height: 4px !important;
    z-index: 5 !important;
}

.isd-avgline.isd-avg-85 {
    background: #ff0000 !important;
    top: calc(14px + 260px * 0.15) !important;
}

.isd-avgline.isd-avg-80 {
    background: #92d050 !important;
    top: calc(14px + 260px * 0.20) !important;
}


.isd-summary-group-label {
    text-align: center;
    color: #ffffff;
    font-size: 14px;
    font-weight: 900;
    text-shadow: 1px 1px 3px #000000;
    padding-top: 8px;
    border-top: 1px solid rgba(255,255,255,0.28);
}

.isd-summary-day-label {
    text-align: center;
    color: #ffffff;
    font-size: 11px;
    font-weight: 900;
    text-shadow: 1px 1px 3px #000000;
    padding-top: 6px;
    white-space: nowrap;
}

.isd-monthly-chart-grid {
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)) !important;
    gap: 0 !important;
}

.isd-monthly-labels {
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)) !important;
    gap: 0 !important;
}







/* Percentage axis freeze support - JS controls horizontal position */
.isd-chart-section {
    position: relative !important;
}

.isd-chart-section-title {
    position: static !important;
}

.isd-chart {
    position: relative !important;
    padding-top: 14px !important;
}

.isd-yaxis {
    position: absolute !important;
    left: 14px !important;
    top: 14px !important;
    bottom: auto !important;
    width: 62px !important;
    height: 260px !important;
    z-index: 35 !important;
    background: linear-gradient(135deg, #2b2b2b 0%, #444 55%, #2b2b2b 100%) !important;
    padding-right: 10px !important;
    box-sizing: border-box !important;
    pointer-events: none !important;
    will-change: transform !important;
}

.isd-chart-grid {
    margin-left: 92px !important;
    height: 260px !important;
    margin-top: 0 !important;
}

.isd-machinelabels {
    margin-left: 92px !important;
}

.isd-avgline {
    left: 106px !important;
    z-index: 8 !important;
}

.isd-avgline.isd-avg-85 {
    top: calc(14px + 260px * 0.15) !important;
}

.isd-avgline.isd-avg-80 {
    top: calc(14px + 260px * 0.20) !important;
}







/* DAILY AXIS FIX - SHOW SELECTED DATE AND CATEGORY */

/* Graph panel must allow scrolling to other dates/machines */
.isd-chart-section {
    overflow-x: auto !important;
    overflow-y: hidden !important;
}

/* Keep chart compact, but leave enough bottom space for 2-line axis labels */
.isd-chart {
    position: relative !important;
    box-sizing: border-box !important;
    padding-bottom: 72px !important;
    overflow: visible !important;
}

/* Plot area: bars start from 0% white baseline */
.isd-chart-grid {
    height: 220px !important;
    min-height: 220px !important;
    max-height: 220px !important;
    align-items: flex-end !important;
    padding-bottom: 0 !important;
    margin-bottom: 0 !important;
    border-bottom: 3px solid rgba(255,255,255,0.95) !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
}

/* Bars use real percentages and cannot exceed 100% */
.isd-bar,
.isd-bar.avail,
.isd-bar.util {
    align-self: flex-end !important;
    margin-bottom: 0 !important;
    max-height: 100% !important;
    box-sizing: border-box !important;
    transform: none !important;
}

/* Axis labels must show both lines: selected date/day and category */
.isd-machinelabels {
    margin-top: 8px !important;
    min-height: 58px !important;
    max-height: none !important;
    overflow: visible !important;
    align-items: flex-start !important;
}

/* Allow category name to display below the date */
.isd-machinelab {
    font-size: 11px !important;
    font-weight: 900 !important;
    line-height: 1.15 !important;
    padding-top: 4px !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    transform: none !important;
    text-align: center !important;
    min-height: 48px !important;
}

.isd-machinelab-swing {
    color: #d291ff !important;
    text-shadow: 1px 1px 3px #000000 !important;
}

/* If labels contain spans/divs, show them as separate lines */
.isd-machinelab span,
.isd-machinelab div {
    display: block !important;
    white-space: normal !important;
    overflow: visible !important;
    text-align: center !important;
}

/* Y-axis aligns with plot height */
.isd-yaxis {
    height: 220px !important;
    min-height: 220px !important;
    max-height: 220px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
}

/* 0% aligns with white baseline */
.isd-yaxis div:last-child {
    transform: translateY(5px) !important;
}

/* Target lines use same plot height */
.isd-avgline.isd-avg-85 {
    top: calc(10px + 220px * 0.15) !important;
}

.isd-avgline.isd-avg-80 {
    top: calc(10px + 220px * 0.20) !important;
}

/* Scrollbar visible for other dates */
.isd-chart-section::-webkit-scrollbar {
    height: 10px !important;
}

.isd-chart-section::-webkit-scrollbar-thumb {
    background: #999 !important;
    border-radius: 8px !important;
}

.isd-chart-section::-webkit-scrollbar-track {
    background: #333 !important;
}

@media print {
    .isd-chart-section {
        overflow-x: visible !important;
        overflow-y: hidden !important;
    }

    .isd-chart {
        padding-bottom: 72px !important;
        overflow: visible !important;
    }

    .isd-chart-grid {
        height: 220px !important;
        min-height: 220px !important;
        max-height: 220px !important;
        align-items: flex-end !important;
        overflow: hidden !important;
    }

    .isd-bar,
    .isd-bar.avail,
    .isd-bar.util {
        align-self: flex-end !important;
        max-height: 100% !important;
        margin-bottom: 0 !important;
        transform: none !important;
    }

    .isd-machinelabels {
        min-height: 58px !important;
        max-height: none !important;
        overflow: visible !important;
    }

    .isd-machinelab {
        white-space: normal !important;
        overflow: visible !important;
        min-height: 48px !important;
    }

    .isd-yaxis {
        height: 220px !important;
        min-height: 220px !important;
        max-height: 220px !important;
    }

    .isd-avgline.isd-avg-85 {
        top: calc(10px + 220px * 0.15) !important;
    }

    .isd-avgline.isd-avg-80 {
        top: calc(10px + 220px * 0.20) !important;
    }
}


/* DAILY DASHBOARD SWING SPARE PURPLE AXIS */
.isd-machinelab-swing,
.isd-machinelab-swing span,
.isd-machinelab-swing div {
    color: #d291ff !important;
    font-weight: 900 !important;
    text-shadow: 1px 1px 3px #000000 !important;
}

</style>
"""



def get_spare_swing_asset_map(filters):
    filters = filters or {}

    start_date = filters.get("start_date") or filters.get("from_date")
    end_date = filters.get("end_date") or filters.get("to_date")
    location = filters.get("location") or filters.get("site")

    if not start_date or not end_date:
        return {}

    args = {
        "start_date": start_date,
        "end_date": end_date,
    }

    conditions = [
        "mpp.docstatus < 2",
        "mpp.prod_month_start_date <= %(end_date)s",
        "mpp.prod_month_end_date >= %(start_date)s",
    ]

    if location:
        conditions.append("mpp.location = %(location)s")
        args["location"] = location

    condition_sql = " AND ".join(conditions)
    spare_map = {}

    def add_reason(asset_name, reason):
        if not asset_name:
            return

        asset_name = str(asset_name).strip()

        if not asset_name:
            return

        spare_map.setdefault(asset_name, set()).add(reason)

    try:
        truck_rows = frappe.db.sql(f"""
            SELECT DISTINCT etl.truck AS asset_name
            FROM `tabMonthly Production Planning` mpp
            INNER JOIN `tabExcavator Truck Link` etl
                ON etl.parent = mpp.name
               AND etl.parenttype = 'Monthly Production Planning'
            WHERE {condition_sql}
              AND IFNULL(etl.truck, '') != ''
              AND IFNULL(etl.excavator, '') = ''
        """, args, as_dict=True)

        for row in truck_rows:
            add_reason(row.get("asset_name"), "Spare/Swing unit Truck")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Daily Dashboard Spare/Swing Trucks")
        frappe.clear_messages()

    try:
        excavator_rows = frappe.db.sql(f"""
            SELECT DISTINCT etl.excavator AS asset_name
            FROM `tabMonthly Production Planning` mpp
            INNER JOIN `tabExcavator Truck Link` etl
                ON etl.parent = mpp.name
               AND etl.parenttype = 'Monthly Production Planning'
            WHERE {condition_sql}
              AND IFNULL(etl.excavator, '') != ''
              AND IFNULL(etl.truck, '') = ''
              AND NOT EXISTS (
                  SELECT 1
                  FROM `tabExcavator Truck Link` assigned_etl
                  WHERE assigned_etl.parent = etl.parent
                    AND assigned_etl.parenttype = etl.parenttype
                    AND assigned_etl.excavator = etl.excavator
                    AND IFNULL(assigned_etl.truck, '') != ''
              )
        """, args, as_dict=True)

        for row in excavator_rows:
            add_reason(row.get("asset_name"), "Spare/Swing unit Excavator")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Daily Dashboard Spare/Swing Excavators")
        frappe.clear_messages()

    try:
        dozer_meta = frappe.get_meta("Dozers Planned")

        dozer_asset_field = None

        for fieldname in ("asset_name", "dozer", "asset"):
            if dozer_meta.has_field(fieldname):
                dozer_asset_field = fieldname
                break

        dozer_type_field = "dozing_type" if dozer_meta.has_field("dozing_type") else None

        if dozer_asset_field and dozer_type_field:
            dozer_rows = frappe.db.sql(f"""
                SELECT DISTINCT dp.`{dozer_asset_field}` AS asset_name
                FROM `tabMonthly Production Planning` mpp
                INNER JOIN `tabDozers Planned` dp
                    ON dp.parent = mpp.name
                   AND dp.parenttype = 'Monthly Production Planning'
                WHERE {condition_sql}
                  AND IFNULL(dp.`{dozer_asset_field}`, '') != ''
                  AND IFNULL(dp.`{dozer_type_field}`, '') = ''
            """, args, as_dict=True)

            for row in dozer_rows:
                add_reason(row.get("asset_name"), "Spare/Swing unit Dozer")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Daily Dashboard Spare/Swing Dozers")
        frappe.clear_messages()

    return {
        asset_name: ", ".join(sorted(reasons))
        for asset_name, reasons in spare_map.items()
    }


def apply_machine_scope_filter_to_dashboard_rows(rows, filters, spare_swing_asset_map):
    filters = filters or {}
    machine_scope = filters.get("machine_scope") or "Include Swing/Spare"

    if machine_scope == "Include Swing/Spare":
        return rows

    filtered_rows = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        machine = get_machine(row)

        if not machine:
            continue

        is_spare = bool(machine in (spare_swing_asset_map or {}))

        if machine_scope == "Production Machines" and not is_spare:
            filtered_rows.append(row)

        elif machine_scope == "Swing/Spare Machines" and is_spare:
            filtered_rows.append(row)

    return filtered_rows


def build_summary_averages_from_machine_series(machine_series):
    out = {category: {"avail": None, "util": None} for category in UI_CATEGORIES}

    for category in UI_CATEGORIES:
        machines = machine_series.get(category) or []

        avail_values = [
            float(row.get("avail"))
            for row in machines
            if isinstance(row, dict) and row.get("avail") is not None
        ]

        util_values = [
            float(row.get("util"))
            for row in machines
            if isinstance(row, dict) and row.get("util") is not None
        ]

        out[category] = {
            "avail": (sum(avail_values) / len(avail_values)) if avail_values else None,
            "util": (sum(util_values) / len(util_values)) if util_values else None,
        }

    return out

def execute(filters=None):
    global CURRENT_MACHINE_SCOPE
    filters = frappe._dict(filters or {})

    if filters.get("site") and not filters.get("location"):
        filters["location"] = filters.get("site")

    if filters.get("location") and not filters.get("site"):
        filters["site"] = filters.get("location")

    summary_type = filters.get("summary_type") or "Daily Summary"
    start_date = filters.get("start_date") or filters.get("from_date")
    end_date = filters.get("end_date") or filters.get("to_date")
    location = filters.get("location") or filters.get("site")

    if not start_date:
        frappe.throw("Please select Start Date.")

    if not end_date:
        frappe.throw("Please select End Date.")

    if not location:
        frappe.throw("Please select Site.")

    source_rows = fetch_grouped_data(location, start_date, end_date)

    spare_swing_asset_map = get_spare_swing_asset_map(filters)
    source_rows = apply_machine_scope_filter_to_dashboard_rows(source_rows, filters, spare_swing_asset_map)

    machine_series = build_machine_series_from_source_rows(source_rows)
    avgs = build_summary_averages_from_machine_series(machine_series)

    global CURRENT_SPARE_SWING_ASSET_MAP

    CURRENT_SPARE_SWING_ASSET_MAP = spare_swing_asset_map or {}
    CURRENT_MACHINE_SCOPE = filters.get("machine_scope") or "Include Swing/Spare"

    dashboard_html = build_dashboard_html(
        location,
        start_date,
        end_date,
        avgs,
        machine_series,
        source_rows,
        summary_type
    )

    columns = [{"label": "", "fieldname": "noop", "fieldtype": "Data", "width": 1}]
    data = [{"noop": ""}]

    return columns, data, dashboard_html


def fetch_grouped_data(location, start_date, end_date):
    result = month_end.execute(
        frappe._dict({
            "from_date": start_date,
            "to_date": end_date,
            "location": location,
            "include_excluded_asset_categories": 1,
        })
    )

    if isinstance(result, (list, tuple)) and len(result) > 1:
        return result[1] or []

    return []


def to_float(value):
    if value in (None, ""):
        return None

    if isinstance(value, str):
        value = value.replace("%", "").replace(",", "").strip()

    try:
        return float(value)
    except Exception:
        return None


def get_any(row, keys):
    for key in keys:
        if isinstance(row, dict) and row.get(key) not in (None, ""):
            return row.get(key)
    return None


def get_category(row):
    value = get_any(row, [
        "asset_category",
        "Asset Category",
        "category",
        "Category",
    ])

    if value in CATEGORY_MAP:
        return CATEGORY_MAP[value]

    return value


def get_indent(row):
    try:
        return int(row.get("indent") or 0)
    except Exception:
        return 0


def get_machine(row):
    machine = get_any(row, [
        "asset_name",
        "Asset Name",
        "asset",
        "Asset",
        "machine",
        "Machine",
        "plant_no",
        "Plant No",
    ])

    if not machine:
        return ""

    machine = str(machine).strip()

    if machine in CATEGORY_MAP:
        return ""

    return machine


def get_avail(row):
    return to_float(get_any(row, [
        "plant_shift_availability",
        "avail_percent",
        "Avail",
        "availability",
        "Availability",
    ]))


def get_util(row):
    return to_float(get_any(row, [
        "plant_shift_utilisation",
        "util_percent",
        "Util",
        "utilisation",
        "Utilisation",
    ]))


def build_summary_averages_from_source_rows(rows):
    out = {category: {"avail": None, "util": None} for category in UI_CATEGORIES}

    for row in rows:
        if not isinstance(row, dict):
            continue

        category = get_category(row)

        if category not in out:
            continue

        machine = get_machine(row)

        if machine:
            continue

        out[category] = {
            "avail": get_avail(row),
            "util": get_util(row),
        }

    for category in UI_CATEGORIES:
        if out[category]["avail"] is not None or out[category]["util"] is not None:
            continue

        category_rows = [
            row for row in rows
            if isinstance(row, dict) and get_category(row) == category
        ]

        if not category_rows:
            continue

        min_indent = min(get_indent(row) for row in category_rows)
        parent_rows = [row for row in category_rows if get_indent(row) == min_indent]

        if parent_rows:
            row = parent_rows[0]
            out[category] = {
                "avail": get_avail(row),
                "util": get_util(row),
            }

    return out


def build_machine_series_from_source_rows(rows):
    buckets = {category: {} for category in UI_CATEGORIES}

    for row in rows:
        if not isinstance(row, dict):
            continue

        category = get_category(row)

        if category not in buckets:
            continue

        machine = get_machine(row)

        if not machine:
            continue

        if machine not in buckets[category]:
            buckets[category][machine] = {
                "avail_values": [],
                "util_values": [],
            }

        av = get_avail(row)
        ut = get_util(row)

        if av is not None:
            buckets[category][machine]["avail_values"].append(av)

        if ut is not None:
            buckets[category][machine]["util_values"].append(ut)

    output = {}

    for category in UI_CATEGORIES:
        output[category] = []

        for machine, vals in sorted(buckets[category].items()):
            av_values = vals["avail_values"]
            ut_values = vals["util_values"]

            output[category].append({
                "machine": machine,
                "avail": (sum(av_values) / len(av_values)) if av_values else None,
                "util": (sum(ut_values) / len(ut_values)) if ut_values else None,
            })

    return output


def bubble_colour(metric, value):
    if value is None:
        return "isd-mbubble-red"

    value = float(value)

    if metric == "avail":
        if value >= 85:
            return "isd-mbubble-green"
        if value >= 75:
            return "isd-mbubble-yellow"
        return "isd-mbubble-red"

    if value >= 80:
        return "isd-mbubble-green"
    if value >= 70:
        return "isd-mbubble-yellow"
    return "isd-mbubble-red"


def fmt_percent(value):
    if value is None:
        return "0.0%"
    return f"{float(value):.1f}%"


def esc(value):
    return frappe.utils.escape_html(str(value or ""))


def build_dashboard_html(location, start_date, end_date, avgs, machine_series, source_rows=None, summary_type="Daily Summary"):
    site_safe = esc(location)
    summary_type_safe = esc(summary_type or "Daily Summary")
    header_colour = SITE_HEADER_COLOURS.get(location, "#f7f7f7")

    metric_cards = []

    for category in UI_CATEGORIES:
        values = avgs.get(category) or {}
        av = values.get("avail")
        ut = values.get("util")

        metric_cards.append(f"""
<div class="isd-metric">
    <div class="isd-metric-title">{esc(category)} Avg</div>

    <div class="isd-pill-row">
        <div class="isd-mbubble {bubble_colour("avail", av)}">
            <div class="isd-mbubble-label">Availability</div>
            <div class="isd-mbubble-value">{fmt_percent(av)}</div>
        </div>

        <div class="isd-mbubble {bubble_colour("util", ut)}">
            <div class="isd-mbubble-label">Utilisation</div>
            <div class="isd-mbubble-value">{fmt_percent(ut)}</div>
        </div>
    </div>
</div>
""")

    chart_html = build_selected_summary_chart_html(
        summary_type,
        location,
        source_rows or [],
        avgs,
        machine_series,
        start_date,
        end_date
    )
    trend_html = build_trend_html(location, start_date, end_date)

    return f"""
{DASH_CSS}

<div class="isd-hourly-dashboard">
    <div class="isd-note">
        Showing: {summary_type_safe} | {site_safe} | {start_date} to {end_date}. Averages and graphs are read from Availability and Utilisation Month End Report.
    </div>

    <div class="isd-site">
        <div class="isd-site-title">{summary_type_safe} | {site_safe} | {start_date} to {end_date}</div>

        <div class="isd-band" style="--site-colour:{header_colour}">
            <div class="isd-metrics">
                {''.join(metric_cards)}
            </div>
        </div>

        <div class="isd-contentrow">
            {chart_html}
            {trend_html}
        </div>
    </div>
</div>
"""




def get_row_date(row):
    value = get_any(row, [
        "date",
        "Date",
        "posting_date",
        "Posting Date",
        "transaction_date",
        "Transaction Date",
        "shift_date",
        "Shift Date",
        "work_date",
        "Work Date",
        "from_date",
        "From Date",
    ])

    if not value:
        return ""

    return str(value)[:10]


def avg_or_none(values):
    values = [float(v) for v in values if v is not None]
    if not values:
        return None
    return sum(values) / len(values)


def daily_height(value):
    if value is None:
        return 2

    try:
        value = float(value)
    except Exception:
        return 2

    value = max(0.0, min(100.0, value))

    if value <= 0:
        return 2

    # Align bars with Y-axis percentage scale.
    # Chart plot height is 220px:
    # 100% = 220px
    # 75%  = 165px
    # 62.5% = 138px
    return max(2, int(round((value / 100.0) * 220)))



def dashboard_bar_height(value):
    if value is None:
        return 2

    try:
        value = float(value)
    except Exception:
        return 2

    value = max(0.0, min(100.0, value))

    if value <= 0:
        return 2

    return max(2, int(round((value / 100.0) * 220)))

def build_selected_summary_chart_html(summary_type, location, source_rows, avgs, machine_series, start_date, end_date):
    summary_type = summary_type or "Daily Summary"

    if summary_type == "Daily Summary":
        return build_daily_summary_chart_html(location, start_date, end_date)

    if summary_type == "Weekly Summary":
        return build_weekly_summary_chart_html(avgs)

    if summary_type == "Monthly Summary":
        return build_monthly_summary_chart_html(avgs)

    return build_chart_html(machine_series)


def build_daily_summary_chart_html(location, start_date, end_date):
    all_dates = []

    try:
        start = getdate(start_date)
        end = getdate(end_date)
        total_days = date_diff(end, start) + 1

        for i in range(max(total_days, 0)):
            all_dates.append(str(add_days(start, i)))
    except Exception:
        all_dates = []

    if not all_dates:
        return """
<div class="isd-chart-stack">
    <div class="isd-chart-section">
        <div class="isd-chart-section-title">FULL DAY AVERAGE AVAILABILITY &amp; UTILISATION - {esc(CURRENT_MACHINE_SCOPE or "Include Swing/Spare").upper()}</div>
        <div class="isd-no-machine-data">No daily summary data found for the selected date range.</div>
    </div>
</div>
"""

    daily_category_values = {}

    for date_value in all_dates:
        day_rows = fetch_grouped_data(location, date_value, date_value)
        day_avgs = build_summary_averages_from_source_rows(day_rows)

        for category in UI_CATEGORIES:
            values = day_avgs.get(category) or {}

            daily_category_values[(category, date_value)] = {
                "avail": values.get("avail") if values.get("avail") is not None else 0.0,
                "util": values.get("util") if values.get("util") is not None else 0.0,
            }

    bars = []
    day_labels = []
    group_labels = []
    total_day_count = 0

    for category in UI_CATEGORIES:
        for date_value in all_dates:
            day = str(date_value)[8:10]
            values = daily_category_values.get((category, date_value)) or {}

            av = values.get("avail")
            ut = values.get("util")

            if av is None:
                av = 0.0

            if ut is None:
                ut = 0.0

            bars.append(
                f"<div class='isd-bar avail' title='{esc(category)} {day} Availability: {fmt_percent(av)}' style='height:{daily_height(av)}px'></div>"
            )

            bars.append(
                f"<div class='isd-bar util' title='{esc(category)} {day} Utilisation: {fmt_percent(ut)}' style='height:{daily_height(ut)}px'></div>"
            )

            day_labels.append(f"<div class='isd-machinelab'>{esc(day)}</div>")

        group_labels.append(
            f"<div class='isd-summary-group-label' style='grid-column: span {len(all_dates)};'>{esc(UI_TITLES.get(category, category))}</div>"
        )

        total_day_count += len(all_dates)

    grid_template = f"repeat({total_day_count * 2}, minmax(18px, 1fr))"
    day_template = f"repeat({total_day_count}, minmax(44px, 1fr))"
    min_width = max(1200, total_day_count * 58)

    return f"""
<div class="isd-chart-stack">
    <div class="isd-chart-section">
        <div class="isd-chart-section-title">FULL DAY AVERAGE AVAILABILITY &amp; UTILISATION - {esc(CURRENT_MACHINE_SCOPE or "Include Swing/Spare").upper()}</div>

        <div class="isd-chart" style="min-width:{min_width}px;">
            <div class="isd-yaxis">
                <div>100%</div>
                <div>90%</div>
                <div>80%</div>
                <div>70%</div>
                <div>60%</div>
                <div>50%</div>
                <div>40%</div>
                <div>30%</div>
                <div>20%</div>
                <div>10%</div>
                <div>0%</div>
            </div>

            <div class="isd-avgline isd-avg-85"></div>
            <div class="isd-avgline isd-avg-80"></div>

            <div class="isd-chart-grid" style="grid-template-columns:{grid_template};">
                {''.join(bars)}
            </div>

            <div class="isd-machinelabels" style="grid-template-columns:{day_template};">
                {''.join(day_labels)}
                {''.join(group_labels)}
            </div>
        </div>
    </div>
</div>
"""



def build_weekly_summary_chart_html(avgs):
    top_categories = ["ADT", "Excavator", "Dozer"]
    bottom_categories = ["Grader", "Service Truck", "TLB", "Water Bowser", "Diesel Bowsers", "Drills", "Loader"]

    machine_scope_safe = esc(CURRENT_MACHINE_SCOPE or "Include Swing/Spare")

    top_title = f"Weekly Summary- ADT / EXCAVATOR / DOZER- {machine_scope_safe}"
    bottom_title = f"Weekly Summary- SUPPORT EQUIPMENT & DRILLS- {machine_scope_safe}"

    return f"""
<div class="isd-chart-stack">
    {build_monthly_summary_section(top_title, top_categories, avgs)}
    {build_monthly_summary_section(bottom_title, bottom_categories, avgs)}
</div>
"""

def build_monthly_summary_chart_html(avgs):
    top_categories = ["ADT", "Excavator", "Dozer"]
    bottom_categories = ["Grader", "Service Truck", "TLB", "Water Bowser", "Diesel Bowsers", "Drills", "Loader"]

    machine_scope_safe = esc(CURRENT_MACHINE_SCOPE or "Include Swing/Spare")

    top_title = f"Monthly Summary - ADT / EXCAVATOR / DOZER- {machine_scope_safe}"
    bottom_title = f"Monthly Summary - SUPPORT EQUIPMENT & DRILLS- {machine_scope_safe}"

    return f"""
<div class="isd-chart-stack">
    {build_monthly_summary_section(top_title, top_categories, avgs)}
    {build_monthly_summary_section(bottom_title, bottom_categories, avgs)}
</div>
"""

def build_monthly_summary_section(title, categories, avgs):
    bars = []
    labels = []

    for category in categories:
        values = avgs.get(category) or {}
        av = values.get("avail")
        ut = values.get("util")

        av_class = "isd-bar avail" + (" nodata" if av is None else "")
        ut_class = "isd-bar util" + (" nodata" if ut is None else "")

        bars.append(f"<div class='{av_class}' title='{esc(category)} Availability: {fmt_percent(av)}' style='height:{daily_height(av)}px'></div>")
        bars.append(f"<div class='{ut_class}' title='{esc(category)} Utilisation: {fmt_percent(ut)}' style='height:{daily_height(ut)}px'></div>")

        labels.append(f"<div class='isd-machinelab'>{esc(UI_TITLES.get(category, category))}</div>")

    grid_template = f"repeat({len(categories) * 2}, minmax(90px, 1fr))"
    label_template = f"repeat({len(categories)}, minmax(180px, 1fr))"

    return f"""
<div class="isd-chart-section">
    <div class="isd-chart-section-title">{esc(title)}</div>

    <div class="isd-chart" style="min-width:100%;">
        <div class="isd-yaxis">
            <div>100%</div><div>90%</div><div>80%</div><div>70%</div><div>60%</div>
            <div>50%</div><div>40%</div><div>30%</div><div>20%</div><div>10%</div><div>0%</div>
        </div>

        <div class="isd-avgline isd-avg-85"></div>
        <div class="isd-avgline isd-avg-80"></div>

        <div class="isd-chart-grid" style="grid-template-columns:{grid_template};">
            {''.join(bars)}
        </div>

        <div class="isd-machinelabels" style="grid-template-columns:{label_template};">
            {''.join(labels)}
        </div>
    </div>
</div>
"""


def build_trend_html(location, start_date, end_date):
    machine_scope = CURRENT_MACHINE_SCOPE or "Include Swing/Spare"

    avail_util_url = (
        "/app/query-report/Avail%20and%20Util%20report"
        f"?start_date={quote(str(start_date or ''))}"
        f"&end_date={quote(str(end_date or ''))}"
        f"&location={quote(str(location or ''))}"
        f"&machine_scope={quote(str(machine_scope or 'Include Swing/Spare'))}"
    )

    return f"""
<div class="isd-side">

    <div class="isd-targets">
        <div class="isd-target-box">


            <div id="open-avail-util-only-button"
                 onclick="window.open('{avail_util_url}', '_blank')"
                 style="
                    width: 120px;
                    min-height: 34px;
                    border: 2px solid #0d6efd;
                    border-radius: 6px;
                    background: #dbeafe;
                    color: #000000;
                    font-size: 12px;
                    font-weight: 800;
                    line-height: 1.05;
                    text-align: center;
                    margin: 0 auto 8px auto;
                    padding: 7px 4px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    box-shadow: 0 1px 4px rgba(0,0,0,0.20);
                 ">
                Open Avail Util
            </div>

<div class="isd-target-title">Availability<br>Target</div>
            <div class="isd-target-line isd-target-line-red"></div>
        </div>

        <div class="isd-target-box">
            <div class="isd-target-title">Utilization<br>Target</div>
            <div class="isd-target-line isd-target-line-green"></div>
        </div>
    </div>

    <div class="isd-legend">
        <span class="isd-legitem"><i class="isd-legswatch isd-leg-avail"></i>Availability</span>
        <span class="isd-legitem"><i class="isd-legswatch isd-leg-util"></i>Utilisation</span>
    </div>
</div>
"""


def build_chart_html(machine_series):
    spare_swing_asset_map = CURRENT_SPARE_SWING_ASSET_MAP or {}
    machine_scope = CURRENT_MACHINE_SCOPE or "Include Swing/Spare"

    def height(value):
        if value is None:
            return 2

        value = max(0.0, min(100.0, float(value)))
        return max(2, int(round(value * 2.7)))

    def chart_section(category):
        title = UI_TITLES.get(category, category)
        items = machine_series.get(category) or []

        if not items:
            return f"""
<div class="isd-chart-section">
    <div class="isd-chart-section-title">{esc(title)} AVAILABILITY &amp; UTILISATION - {esc(CURRENT_MACHINE_SCOPE or "Include Swing/Spare")}{esc(CURRENT_MACHINE_SCOPE or "Include Swing/Spare")}</div>
    <div class="isd-no-machine-data">No machines found for {esc(title)} in the selected date range.</div>
</div>
"""

        count = max(len(items), 1)
        grid_template = f"repeat({count * 2}, minmax(18px, 1fr))"
        label_template = f"repeat({count}, minmax(54px, 2fr))"
        min_width = max(820, count * 70)

        bars = []
        labels = []

        for item in items:
            machine_raw = str(item.get("machine") or "").strip()
            machine = esc(machine_raw)
            av = item.get("avail")
            ut = item.get("util")

            # If user selects Swing/Spare Machines, all shown machines are swing/spare.
            # If user selects Include Swing/Spare, only machines found in Monthly Planning spare map are purple.
            is_spare_swing = (
                machine_scope == "Swing/Spare Machines"
                or bool(machine_raw and machine_raw in spare_swing_asset_map)
            )

            av_class = "isd-bar avail" + (" nodata" if av is None else "")
            ut_class = "isd-bar util" + (" nodata" if ut is None else "")

            label_style = ""
            label_class = "isd-machinelab"

            if is_spare_swing:
                label_class = "isd-machinelab isd-machinelab-swing"
                label_style = "color:#d291ff !important;font-weight:900 !important;text-shadow:1px 1px 3px #000000 !important;"

            bars.append(
                f"<div class='{av_class}' title='{machine} Availability: {fmt_percent(av)}' style='height:{height(av)}px'></div>"
            )

            bars.append(
                f"<div class='{ut_class}' title='{machine} Utilisation: {fmt_percent(ut)}' style='height:{height(ut)}px'></div>"
            )

            labels.append(
                f"<div class='{label_class}' title='{machine}' style='{label_style}'><span style='{label_style}'>{machine}</span></div>"
            )

        return f"""
<div class="isd-chart-section">
    <div class="isd-chart-section-title">{esc(title)} AVAILABILITY &amp; UTILISATION - {esc(CURRENT_MACHINE_SCOPE or "Include Swing/Spare")}{esc(CURRENT_MACHINE_SCOPE or "Include Swing/Spare")}</div>

    <div class="isd-chart" style="min-width:{min_width}px;">
        <div class="isd-yaxis">
            <div>100%</div>
            <div>90%</div>
            <div>80%</div>
            <div>70%</div>
            <div>60%</div>
            <div>50%</div>
            <div>40%</div>
            <div>30%</div>
            <div>20%</div>
            <div>10%</div>
            <div>0%</div>
        </div>

        <div class="isd-avgline isd-avg-85"></div>
        <div class="isd-avgline isd-avg-80"></div>

        <div class="isd-chart-grid" style="grid-template-columns:{grid_template};">
            {''.join(bars)}
        </div>

        <div class="isd-machinelabels" style="grid-template-columns:{label_template};">
            {''.join(labels)}
        </div>
    </div>
</div>
"""

    return f"""
<div class="isd-chart-stack">
    {''.join(chart_section(category) for category in UI_CATEGORIES)}
</div>
"""


@frappe.whitelist()
def download_daily_dashboard_pdf(start_date=None, end_date=None, location=None, site=None):
    location = location or site

    if not start_date:
        frappe.throw("Please select Start Date.")

    if not end_date:
        frappe.throw("Please select End Date.")

    if not location:
        frappe.throw("Please select Site.")

    source_rows = fetch_grouped_data(location, start_date, end_date)
    avgs = build_summary_averages_from_source_rows(source_rows)
    machine_series = build_machine_series_from_source_rows(source_rows)

    dashboard_html = build_dashboard_html(location, start_date, end_date, avgs, machine_series, source_rows, summary_type)

    html = f"""
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @page {{
            size: A4 landscape;
            margin: 6mm;
        }}

        body {{
            margin: 0;
            padding: 0;
            background: #ffffff;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}

        * {{
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}

        .isd-contentrow {{
            display: block !important;
        }}

        .isd-side {{
            display: none !important;
        }}

        .isd-chart-stack {{
            display: block !important;
            overflow: visible !important;
            padding: 0 !important;
        }}

        .isd-chart-section {{
            page-break-inside: avoid;
            break-inside: avoid;
            overflow: visible !important;
            margin-bottom: 18px !important;
        }}

        .isd-chart {{
            overflow: visible !important;
        }}
    </style>
</head>
<body>
    {dashboard_html}
</body>
</html>
"""

    pdf = frappe.utils.pdf.get_pdf(html)

    filename = f"Daily Availability and Utilisation Dashboard - {location} - {start_date} to {end_date}.pdf"

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"



def build_pdf_dashboard_html(location, start_date, end_date, avgs, machine_series):
    sections = []

    for category in UI_CATEGORIES:
        items = machine_series.get(category) or []

        if not items:
            continue

        rows = []
        for item in items:
            machine = esc(item.get("machine") or "")
            avail = max(0, min(100, flt(item.get("avail"))))
            util = max(0, min(100, flt(item.get("util"))))

            rows.append(f"""
<tr>
    <td class="machine-label">{machine}</td>
    <td>
        <div class="bar-wrap">
            <div class="target-line avail-target"></div>
            <div class="target-line util-target"></div>
            <div class="bar availability" style="width:{avail}%;">{avail:.1f}%</div>
            <div class="bar utilisation" style="width:{util}%;">{util:.1f}%</div>
        </div>
    </td>
</tr>
""")

        sections.append(f"""
<div class="pdf-section">
    <h2>{esc(category)} AVAILABILITY &amp; UTILISATION</h2>
    <table class="pdf-chart">
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
</div>
""")

    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
    size: A4 landscape;
    margin: 7mm;
}}

body {{
    font-family: Arial, sans-serif;
    color: #111;
    margin: 0;
    padding: 0;
}}

.header {{
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 8px;
}}

.summary {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 12px;
}}

.summary td {{
    border: 1px solid #333;
    padding: 4px 6px;
    font-size: 11px;
    font-weight: bold;
}}

.legend-line {{
    display: inline-block;
    width: 42px;
    height: 4px;
    vertical-align: middle;
    margin-left: 6px;
}}

.red {{
    background: #ff0000;
}}

.green {{
    background: #92d050;
}}

.pdf-section {{
    page-break-inside: avoid;
    margin-bottom: 14px;
    border: 1px solid #222;
    padding: 8px;
}}

h2 {{
    text-align: center;
    font-size: 18px;
    margin: 0 0 8px 0;
}}

.pdf-chart {{
    width: 100%;
    border-collapse: collapse;
}}

.pdf-chart td {{
    padding: 3px 4px;
    vertical-align: middle;
}}

.machine-label {{
    width: 90px;
    font-size: 10px;
    font-weight: bold;
    white-space: nowrap;
}}

.bar-wrap {{
    position: relative;
    height: 34px;
    border-left: 1px solid #333;
    border-bottom: 1px solid #bbb;
    background: #eeeeee;
}}

.target-line {{
    position: absolute;
    left: 0;
    right: 0;
    height: 3px;
    z-index: 5;
}}

.avail-target {{
    top: 5px;
    background: #ff0000;
}}

.util-target {{
    top: 9px;
    background: #92d050;
}}

.bar {{
    position: relative;
    height: 13px;
    line-height: 13px;
    font-size: 9px;
    font-weight: bold;
    color: #000;
    padding-left: 4px;
    box-sizing: border-box;
    white-space: nowrap;
}}

.availability {{
    background: #f4b000;
    margin-top: 3px;
}}

.utilisation {{
    background: #2f75b5;
    color: #fff;
    margin-top: 2px;
}}
</style>
</head>
<body>
    <div class="header">
        Daily Availability and Utilisation Dashboard | {esc(location)} | {esc(start_date)} to {esc(end_date)}
    </div>

    <table class="summary">
        <tr>
            <td>Availability Target <span class="legend-line red"></span></td>
            <td>85%</td>
            <td>Utilization Target <span class="legend-line green"></span></td>
            <td>80%</td>
        </tr>
    </table>

    {''.join(sections)}
</body>
</html>
"""


@frappe.whitelist()
def download_daily_dashboard_pdf_v2(start_date=None, end_date=None, location=None, site=None):
    location = location or site

    if not start_date:
        frappe.throw("Please select Start Date.")

    if not end_date:
        frappe.throw("Please select End Date.")

    if not location:
        frappe.throw("Please select Site.")

    source_rows = fetch_grouped_data(location, start_date, end_date)
    avgs = build_summary_averages_from_source_rows(source_rows)
    machine_series = build_machine_series_from_source_rows(source_rows)

    html = build_pdf_dashboard_html(location, start_date, end_date, avgs, machine_series)

    pdf = frappe.utils.pdf.get_pdf(html)

    filename = f"Daily Availability and Utilisation Dashboard - {location} - {start_date} to {end_date}.pdf"

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"

