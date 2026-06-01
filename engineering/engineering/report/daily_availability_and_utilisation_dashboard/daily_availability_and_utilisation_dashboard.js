frappe.query_reports["Daily Availability and Utilisation Dashboard"] = {
    filters: [
        {
            fieldname: "start_date",
            label: __("Start Date"),
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "end_date",
            label: __("End Date"),
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "location",
            label: __("Site"),
            fieldtype: "Link",
            options: "Location",
            reqd: 1
        },
        {
            fieldname: "summary_type",
            label: __("Summary Type"),
            fieldtype: "Select",
            options: "Daily Summary\nAverage Per Machine\nWeekly Summary\nMonthly Summary",
            default: "Daily Summary",
            reqd: 1,
            on_change: function() {
                frappe.query_report.refresh();
            }
        }
    ],

    onload(report) {
        const today = frappe.datetime.get_today();
        const yesterday = frappe.datetime.add_days(today, -1);

        if (!report.get_filter_value("start_date")) {
            report.set_filter_value("start_date", yesterday);
        }

        if (!report.get_filter_value("end_date")) {
            report.set_filter_value("end_date", yesterday);
        }

        inject_dashboard_table_hider();
        add_graph_buttons(report);
        freeze_percentage_axis_on_scroll(report);
    },

    refresh(report) {
        inject_dashboard_table_hider();
        hide_report_table(report);
        add_graph_buttons(report);
        freeze_percentage_axis_on_scroll(report);
    },

    after_datatable_render(report) {
        inject_dashboard_table_hider();
        hide_report_table(report);
        add_graph_buttons(report);
        freeze_percentage_axis_on_scroll(report);
    }
};

function add_graph_buttons(report) {
    if (!report || !report.page || report.__graph_buttons_added) {
        return;
    }

    report.__graph_buttons_added = true;

    report.page.add_inner_button(__("Download PDF"), function () {
        download_dashboard_as_exact_pdf(report);
    });

    report.page.add_inner_button(__("Preview Graphs"), function () {
        open_graph_print_preview(report);
    });
}

function inject_dashboard_table_hider() {
    if (document.getElementById("daily-availability-dashboard-table-hider")) {
        return;
    }

    const style = document.createElement("style");
    style.id = "daily-availability-dashboard-table-hider";
    style.innerHTML = `
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .datatable,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .dt-scrollable,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .dt-header,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .dt-cell,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .dt-row,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .dt-footer,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .dt-message,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .no-result {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            min-height: 0 !important;
            max-height: 0 !important;
            overflow: hidden !important;
            padding: 0 !important;
            margin: 0 !important;
            border: 0 !important;
        }

        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .result,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .result-container,
        .query-report[data-report-name="Daily Availability and Utilisation Dashboard"] .report-wrapper {
            display: block !important;
            visibility: visible !important;
            height: auto !important;
            min-height: 0 !important;
            max-height: none !important;
            overflow: visible !important;
        }
    `;

    document.head.appendChild(style);
}

function hide_report_table(report) {
    const hide = () => {
        inject_dashboard_table_hider();

        const wrapper = report.page.wrapper;

        wrapper.attr("data-report-name", "Daily Availability and Utilisation Dashboard");
        wrapper.find(".query-report").attr("data-report-name", "Daily Availability and Utilisation Dashboard");

        wrapper.find(".datatable, .dt-scrollable, .dt-header, .dt-cell, .dt-row, .dt-footer, .dt-message, .no-result").attr("style", function(i, current) {
            return (current || "") + ";display:none!important;visibility:hidden!important;height:0!important;max-height:0!important;overflow:hidden!important;padding:0!important;margin:0!important;border:0!important;";
        });

        wrapper.find(".result, .result-container, .report-wrapper").attr("style", function(i, current) {
            return (current || "") + ";display:block!important;visibility:visible!important;height:auto!important;max-height:none!important;overflow:visible!important;";
        });
    };

    setTimeout(hide, 0);
    setTimeout(hide, 100);
    setTimeout(hide, 300);
    setTimeout(hide, 800);
    setTimeout(hide, 1500);
}

function load_script_once(id, src) {
    return new Promise((resolve, reject) => {
        if (document.getElementById(id)) {
            resolve();
            return;
        }

        const script = document.createElement("script");
        script.id = id;
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

async function ensure_pdf_libraries() {
    await load_script_once(
        "html2canvas-lib",
        "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"
    );

    await load_script_once(
        "jspdf-lib",
        "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"
    );
}

function get_dashboard_element(report) {
    const wrapper = report.page.wrapper;
    const dashboard = wrapper.find(".isd-hourly-dashboard").first();

    if (!dashboard.length) {
        frappe.msgprint(__("Please run the report first, then download the PDF."));
        return null;
    }

    return dashboard[0];
}

async function download_dashboard_as_exact_pdf(report) {
    const dashboard = get_dashboard_element(report);

    if (!dashboard) {
        return;
    }

    frappe.show_alert({
        message: __("Preparing PDF. Please wait..."),
        indicator: "blue"
    });

    try {
        await ensure_pdf_libraries();

        const jsPDF = window.jspdf.jsPDF;
        const pdf = new jsPDF("l", "mm", "a4");

        const page_width = pdf.internal.pageSize.getWidth();
        const page_height = pdf.internal.pageSize.getHeight();

        const margin = 4;
        const usable_width = page_width - margin * 2;
        const usable_height = page_height - margin * 2;

        const start_date = report.get_filter_value("start_date") || "";
        const end_date = report.get_filter_value("end_date") || "";
        const location = report.get_filter_value("location") || "";
        const summary_type = report.get_filter_value("summary_type") || "Daily Summary";

        const dashboard_el = $(dashboard);

        const title_text = `Daily Availability and Utilisation Dashboard | ${summary_type} | ${location} | ${start_date} to ${end_date}`;

        const sections = dashboard_el.find(".isd-chart-section").toArray().filter((section) => {
            return $(section).find(".isd-bar").length > 0;
        });

        if (!sections.length) {
            frappe.msgprint(__("No graph sections found. Please run the report first."));
            return;
        }

        const original_scroll_x = window.scrollX;
        const original_scroll_y = window.scrollY;
        window.scrollTo(0, 0);

        for (let index = 0; index < sections.length; index++) {
            const section = sections[index];

            section.scrollLeft = 0;

            const original_width = section.style.width;
            const original_max_width = section.style.maxWidth;
            const original_overflow = section.style.overflow;
            const original_transform = section.style.transform;

            const capture_width = Math.min(section.scrollWidth, 1800);
            section.style.width = capture_width + "px";
            section.style.maxWidth = "none";
            section.style.overflow = "visible";
            section.style.transform = "none";

            const canvas = await html2canvas(section, {
                scale: 0.75,
                useCORS: true,
                allowTaint: true,
                backgroundColor: "#ffffff",
                width: Math.min(section.scrollWidth, 1800),
                height: section.scrollHeight,
                windowWidth: Math.min(section.scrollWidth, 1800),
                windowHeight: section.scrollHeight,
                scrollX: 0,
                scrollY: 0
            });

            section.style.width = original_width;
            section.style.maxWidth = original_max_width;
            section.style.overflow = original_overflow;
            section.style.transform = original_transform;

            if (index > 0) {
                pdf.addPage();
            }

            pdf.setFontSize(10);
            pdf.setFont(undefined, "bold");
            pdf.text(title_text, margin, margin + 3);

            const img_data = canvas.toDataURL("image/jpeg", 0.72);

            const img_width_px = canvas.width;
            const img_height_px = canvas.height;
            const img_ratio = img_height_px / img_width_px;

            let img_width = usable_width;
            let img_height = img_width * img_ratio;

            const title_space = 8;
            const available_graph_height = usable_height - title_space;

            if (img_height > available_graph_height) {
                img_height = available_graph_height;
                img_width = img_height / img_ratio;
            }

            const x = margin + (usable_width - img_width) / 2;
            const y = margin + title_space;

            pdf.addImage(img_data, "JPEG", x, y, img_width, img_height, undefined, "FAST");
        }

        window.scrollTo(original_scroll_x, original_scroll_y);

        const filename = `Daily Availability and Utilisation Dashboard - ${location} - ${start_date} to ${end_date}.pdf`;

        pdf.save(filename);

        frappe.show_alert({
            message: __("PDF downloaded."),
            indicator: "green"
        });
    } catch (error) {
        console.error(error);

        frappe.msgprint(
            __("Could not create the direct PDF download. Use Preview Graphs and choose Save as PDF.")
        );
    }
}

function collect_dashboard_css(dashboard) {
    let copied_styles = "";

    document.querySelectorAll("style").forEach((style) => {
        const css = style.innerHTML || "";

        if (
            css.includes("isd-hourly-dashboard") ||
            css.includes("isd-chart-section") ||
            css.includes("isd-chart-grid") ||
            css.includes("isd-mbubble") ||
            css.includes("isd-avgline")
        ) {
            copied_styles += "\n" + css;
        }
    });

    $(dashboard).find("style").each(function () {
        copied_styles += "\n" + (this.innerHTML || "");
    });

    return copied_styles;
}

function open_graph_print_preview(report) {
    const dashboard = get_dashboard_element(report);

    if (!dashboard) {
        return;
    }

    const dashboard_clone = $(dashboard).clone();

    const html = dashboard_clone.prop("outerHTML");
    const copied_styles = collect_dashboard_css(dashboard);
    const print_window = window.open("", "_blank");

    if (!print_window) {
        frappe.msgprint(__("Popup blocked. Please allow popups for this site and try again."));
        return;
    }

    print_window.document.open();
    print_window.document.write(`
<!doctype html>
<html>
<head>
    <title>Daily Availability and Utilisation Dashboard</title>

    <style>
        ${copied_styles}

        html,
        body {
            margin: 0;
            padding: 0;
            background: #ffffff;
            font-family: Arial, sans-serif;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }

        * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }

        .print-actions {
            position: sticky;
            top: 0;
            z-index: 9999;
            display: flex;
            gap: 8px;
            align-items: center;
            padding: 10px;
            background: #ffffff;
            border-bottom: 1px solid #ddd;
        }

        .print-actions button {
            border: 1px solid #444;
            background: #111;
            color: #fff;
            padding: 8px 12px;
            border-radius: 6px;
            font-weight: 700;
            cursor: pointer;
        }

        .print-help {
            font-weight: 700;
            font-size: 12px;
        }

        .isd-hourly-dashboard {
            width: 100% !important;
            max-width: none !important;
            padding: 8px !important;
            box-sizing: border-box !important;
        }

        .isd-contentrow {
            display: block !important;
        }

        .isd-side {
            display: none !important;
        }

        .isd-note {
            font-size: 12px !important;
            font-weight: 700 !important;
            margin-bottom: 8px !important;
            padding: 6px 8px !important;
        }

        .isd-site-title {
            font-size: 13px !important;
            font-weight: 900 !important;
            padding: 8px !important;
        }

        .isd-band {
            padding: 8px !important;
        }

        .isd-metrics {
            grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)) !important;
            gap: 8px !important;
        }

        .isd-metric {
            padding: 7px !important;
        }

        .isd-metric-title {
            font-size: 10px !important;
            margin-bottom: 5px !important;
        }

        .isd-mbubble {
            width: 58px !important;
            min-height: 52px !important;
            padding: 5px !important;
        }

        .isd-mbubble-label {
            font-size: 8px !important;
            line-height: 1 !important;
        }

        .isd-mbubble-value {
            font-size: 11px !important;
        }

        .isd-chart-stack {
            display: block !important;
            overflow: visible !important;
            padding: 0 !important;
        }

        .isd-chart-section {
            width: 100% !important;
            max-width: 1320px !important;
            overflow: hidden !important;
            margin: 0 auto 14px auto !important;
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }

        .isd-chart {
            min-width: 0 !important;
            width: 100% !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
            padding: 10px 12px 12px !important;
        }

        .isd-chart-section-title {
            font-size: 21px !important;
            padding: 8px !important;
            letter-spacing: 0.5px !important;
        }

        .isd-chart-grid {
            height: 255px !important;
            gap: 2px !important;
            margin-left: 42px !important;
        }

        .isd-yaxis {
            top: 10px !important;
            bottom: 42px !important;
            width: 36px !important;
            font-size: 10px !important;
            font-weight: 700 !important;
            color: #ffffff !important;
        }

        .isd-machinelabels {
            font-size: 9px !important;
            gap: 2px !important;
            margin-left: 42px !important;
            margin-top: 5px !important;
        }

        .isd-machinelab {
            font-size: 9px !important;
            font-weight: 700 !important;
            min-height: 20px !important;
            overflow: hidden !important;
            text-overflow: clip !important;
            color: #ffffff !important;
        }

        .isd-avgline {
            left: 54px !important;
            right: 12px !important;
        }

        .isd-avgline.isd-avg-85 {
            top: calc(10px + 255px * 0.15) !important;
        }

        .isd-avgline.isd-avg-80 {
            top: calc(10px + 255px * 0.20) !important;
        }

        


/* Clean full-width graph preview like requested screenshot */
.isd-hourly-dashboard {
    width: 100% !important;
    max-width: none !important;
    padding: 0 !important;
    box-sizing: border-box !important;
}

.isd-contentrow {
    display: block !important;
}

.isd-side {
    display: none !important;
}

.isd-note,
.isd-band,
.isd-metrics,
.isd-site-title {
    display: none !important;
}

.isd-chart-stack {
    display: block !important;
    overflow: visible !important;
    padding: 0 !important;
}

.isd-chart-section {
    width: 100% !important;
    max-width: none !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    margin: 0 0 8px 0 !important;
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
    text-shadow: 1px 1px 2px #000 !important;
}

.isd-chart {
    width: max-content !important;
    min-width: 100% !important;
    overflow: visible !important;
    box-sizing: border-box !important;
    padding: 14px 14px 20px 14px !important;
    background: transparent !important;
}

.isd-yaxis {
    left: 14px !important;
    top: 14px !important;
    bottom: 34px !important;
    width: 38px !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    line-height: 1 !important;
    text-align: right !important;
    color: #ffffff !important;
}

.isd-chart-grid {
    margin-left: 50px !important;
    height: 260px !important;
    gap: 8px !important;
    border-bottom: 2px solid rgba(255,255,255,0.85) !important;
    align-items: end !important;
    background:
        linear-gradient(to top, rgba(255,255,255,0.13) 1px, transparent 1px) !important;
    background-size: 100% 26px !important;
}

.isd-bar {
    border-radius: 0 !important;
    min-height: 2px !important;
}

.isd-bar.avail {
    background: #f4b000 !important;
}

.isd-bar.util {
    background: #2f75b5 !important;
}

.isd-machinelabels {
    margin-left: 50px !important;
    margin-top: 8px !important;
    min-height: 18px !important;
    align-items: start !important;
    gap: 8px !important;
}

.isd-machinelab {
    font-size: 9px !important;
    font-weight: 700 !important;
    line-height: 1.1 !important;
    min-height: 14px !important;
    padding-top: 2px !important;
    color: #ffffff !important;
    overflow: hidden !important;
    white-space: nowrap !important;
    text-overflow: clip !important;
    transform: none !important;
}

.isd-avgline {
    left: 64px !important;
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


        
/* Make graph numbers and labels readable */
.isd-yaxis {
    font-size: 12px !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    text-shadow: 1px 1px 2px #000000 !important;
}

.isd-machinelab {
    font-size: 11px !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    text-shadow: 1px 1px 2px #000000 !important;
}

.isd-chart-section-title {
    font-size: 24px !important;
    font-weight: 900 !important;
    color: #ffffff !important;
    text-shadow: 2px 2px 3px #000000 !important;
}

.isd-chart-grid {
    margin-left: 56px !important;
}

.isd-machinelabels {
    margin-left: 56px !important;
}

.isd-avgline {
    left: 70px !important;
}


        
/* Slightly bigger percentage and axis numbers */
.isd-yaxis {
    font-size: 14px !important;
    font-weight: 900 !important;
}

.isd-machinelab {
    font-size: 12px !important;
    font-weight: 900 !important;
}

.isd-mbubble-value {
    font-size: 12px !important;
    font-weight: 900 !important;
}

.isd-mbubble-label {
    font-size: 8px !important;
    font-weight: 900 !important;
}

.isd-chart-grid {
    margin-left: 64px !important;
}

.isd-machinelabels {
    margin-left: 64px !important;
}

.isd-avgline {
    left: 78px !important;
}


        
/* Make preview graph numbers visible again */
.isd-yaxis {
    width: 48px !important;
    font-size: 13px !important;
    font-weight: 900 !important;
    color: #ffffff !important;
    text-shadow: 1px 1px 3px #000000 !important;
    text-align: right !important;
}

.isd-chart-grid {
    margin-left: 64px !important;
}

.isd-machinelabels {
    margin-left: 64px !important;
    min-height: 24px !important;
}

.isd-machinelab {
    font-size: 10px !important;
    font-weight: 900 !important;
    color: #ffffff !important;
    text-shadow: 1px 1px 3px #000000 !important;
    line-height: 1.1 !important;
    min-height: 18px !important;
    padding-top: 4px !important;
    overflow: visible !important;
}

.isd-avgline {
    left: 78px !important;
}


        
/* Increase preview axis percentages and machine labels */
.isd-yaxis {
    width: 54px !important;
    font-size: 15px !important;
    font-weight: 900 !important;
}

.isd-chart-grid {
    margin-left: 72px !important;
}

.isd-machinelabels {
    margin-left: 72px !important;
    min-height: 30px !important;
}

.isd-machinelab {
    font-size: 12px !important;
    font-weight: 900 !important;
    min-height: 22px !important;
    padding-top: 5px !important;
}

.isd-avgline {
    left: 86px !important;
}


        
/* Increase preview axis and machine labels again */
.isd-yaxis {
    width: 62px !important;
    font-size: 18px !important;
    font-weight: 900 !important;
}

.isd-chart-grid {
    margin-left: 84px !important;
}

.isd-machinelabels {
    margin-left: 84px !important;
    min-height: 38px !important;
}

.isd-machinelab {
    font-size: 14px !important;
    font-weight: 900 !important;
    min-height: 28px !important;
    padding-top: 6px !important;
}

.isd-avgline {
    left: 98px !important;
}


        
/* Make graph bars start exactly from 0 percent baseline */
.isd-chart-grid {
    align-items: end !important;
    border-bottom: 3px solid rgba(255,255,255,0.9) !important;
    padding-bottom: 0 !important;
}

.isd-bar {
    margin-bottom: 0 !important;
    align-self: end !important;
}

.isd-yaxis {
    justify-content: space-between !important;
}

.isd-yaxis div:last-child {
    transform: translateY(3px) !important;
}

.isd-machinelabels {
    margin-top: 10px !important;
}


        
/* Align Y axis labels exactly to the graph baseline */
.isd-chart {
    position: relative !important;
}

.isd-yaxis {
    top: 14px !important;
    bottom: 32px !important;
    height: 260px !important;
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
    height: 260px !important;
    margin-top: 0 !important;
    align-items: end !important;
    border-bottom: 3px solid rgba(255,255,255,0.95) !important;
}

.isd-machinelabels {
    margin-top: 9px !important;
}



/* Preview Graphs freeze heading and percentage axis */
.isd-chart-section {
    position: relative !important;
}

.isd-chart-section-title {
    position: sticky !important;
    left: 0 !important;
    top: 0 !important;
    z-index: 50 !important;
    background: linear-gradient(135deg, #2b2b2b 0%, #555 48%, #2b2b2b 100%) !important;
}

.isd-yaxis {
    position: absolute !important;
    left: 14px !important;
    top: 14px !important;
    bottom: auto !important;
    width: 62px !important;
    height: 260px !important;
    z-index: 45 !important;
    background: linear-gradient(135deg, #2b2b2b 0%, #444 55%, #2b2b2b 100%) !important;
    padding-right: 10px !important;
    box-sizing: border-box !important;
    pointer-events: none !important;
    will-change: transform !important;
}

.isd-chart {
    position: relative !important;
    padding-top: 14px !important;
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

@media print {
    .isd-chart-section-title {
        position: static !important;
        left: auto !important;
        top: auto !important;
    }

    .isd-yaxis {
        transform: none !important;
        background: transparent !important;
    }
}


        @media print {

            /* Align printed/PDF Y axis labels exactly to the graph baseline */
            .isd-chart {
                position: relative !important;
            }

            .isd-yaxis {
                top: 10px !important;
                bottom: 28px !important;
                height: 220px !important;
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
                transform: translateY(4px) !important;
            }

            .isd-chart-grid {
                height: 220px !important;
                margin-top: 0 !important;
                align-items: end !important;
                border-bottom: 3px solid rgba(255,255,255,0.95) !important;
            }

            .isd-machinelabels {
                margin-top: 8px !important;
            }


            /* Make printed/PDF graph bars start exactly from 0 percent baseline */
            .isd-chart-grid {
                align-items: end !important;
                border-bottom: 3px solid rgba(255,255,255,0.9) !important;
                padding-bottom: 0 !important;
            }

            .isd-bar {
                margin-bottom: 0 !important;
                align-self: end !important;
            }

            .isd-yaxis {
                justify-content: space-between !important;
            }

            .isd-yaxis div:last-child {
                transform: translateY(3px) !important;
            }

            .isd-machinelabels {
                margin-top: 8px !important;
            }


            /* Increase print/PDF axis and machine labels again */
            .isd-yaxis {
                width: 54px !important;
                font-size: 14px !important;
                font-weight: 900 !important;
            }

            .isd-chart-grid {
                margin-left: 74px !important;
            }

            .isd-machinelabels {
                margin-left: 74px !important;
                min-height: 32px !important;
            }

            .isd-machinelab {
                font-size: 11px !important;
                font-weight: 900 !important;
                min-height: 24px !important;
                padding-top: 5px !important;
            }

            .isd-avgline {
                left: 88px !important;
            }


            /* Increase print/PDF axis percentages and machine labels */
            .isd-yaxis {
                width: 48px !important;
                font-size: 12px !important;
                font-weight: 900 !important;
            }

            .isd-chart-grid {
                margin-left: 64px !important;
            }

            .isd-machinelabels {
                margin-left: 64px !important;
                min-height: 26px !important;
            }

            .isd-machinelab {
                font-size: 9px !important;
                font-weight: 900 !important;
                min-height: 18px !important;
                padding-top: 4px !important;
            }

            .isd-avgline {
                left: 76px !important;
            }


            /* Make printed/downloaded PDF graph numbers visible */
            .isd-yaxis {
                width: 44px !important;
                font-size: 10px !important;
                font-weight: 900 !important;
                color: #ffffff !important;
                text-shadow: 1px 1px 3px #000000 !important;
                text-align: right !important;
            }

            .isd-chart-grid {
                margin-left: 58px !important;
            }

            .isd-machinelabels {
                margin-left: 58px !important;
                min-height: 22px !important;
            }

            .isd-machinelab {
                font-size: 8px !important;
                font-weight: 900 !important;
                color: #ffffff !important;
                text-shadow: 1px 1px 3px #000000 !important;
                line-height: 1.1 !important;
                min-height: 16px !important;
                padding-top: 3px !important;
                overflow: visible !important;
            }

            .isd-avgline {
                left: 70px !important;
            }


            .isd-yaxis {
                font-size: 11px !important;
                font-weight: 900 !important;
            }

            .isd-machinelab {
                font-size: 9px !important;
                font-weight: 900 !important;
            }

            .isd-mbubble-value {
                font-size: 9px !important;
                font-weight: 900 !important;
            }

            .isd-mbubble-label {
                font-size: 6px !important;
                font-weight: 900 !important;
            }

            .isd-chart-grid {
                margin-left: 56px !important;
            }

            .isd-machinelabels {
                margin-left: 56px !important;
            }

            .isd-avgline {
                left: 66px !important;
            }


            .isd-note,
            .isd-band,
            .isd-metrics,
            .isd-site-title {
                display: none !important;
            }

            .isd-chart-section {
                width: 100% !important;
                overflow-x: hidden !important;
                overflow-y: hidden !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
                margin-bottom: 6px !important;
            }

            .isd-chart-section-title {
                font-size: 18px !important;
                padding: 8px 6px 6px 6px !important;
            }

            .isd-chart {
                width: 100% !important;
                min-width: 100% !important;
                padding: 10px 10px 18px 10px !important;
            }

            .isd-yaxis {
                left: 10px !important;
                top: 10px !important;
                bottom: 32px !important;
                width: 34px !important;
                font-size: 8px !important;
                text-align: right !important;
            }

            .isd-chart-grid {
                margin-left: 44px !important;
                height: 210px !important;
                gap: 5px !important;
                border-bottom: 2px solid rgba(255,255,255,0.85) !important;
            }

            .isd-machinelabels {
                margin-left: 44px !important;
                margin-top: 6px !important;
                min-height: 14px !important;
                gap: 5px !important;
            }

            .isd-machinelab {
                font-size: 7px !important;
                font-weight: 700 !important;
                min-height: 12px !important;
                padding-top: 1px !important;
                overflow: hidden !important;
                white-space: nowrap !important;
                transform: none !important;
            }

            .isd-avgline {
                left: 54px !important;
                right: 10px !important;
            }

            .isd-avgline.isd-avg-85 {
                top: calc(10px + 210px * 0.15) !important;
            }

            .isd-avgline.isd-avg-80 {
                top: calc(10px + 210px * 0.20) !important;
            }


            .isd-chart-section {
                overflow-x: visible !important;
                overflow-y: hidden !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }

            .isd-chart {
                width: max-content !important;
                min-width: max-content !important;
                padding: 10px 10px 40px 10px !important;
                overflow: visible !important;
            }

            .isd-yaxis {
                left: 10px !important;
                top: 10px !important;
                bottom: 62px !important;
                width: 36px !important;
                font-size: 8px !important;
                text-align: right !important;
            }

            .isd-chart-grid {
                margin-left: 46px !important;
                height: 220px !important;
                gap: 3px !important;
                border-bottom: 2px solid rgba(255,255,255,0.85) !important;
            }

            .isd-machinelabels {
                margin-left: 46px !important;
                margin-top: 8px !important;
                min-height: 44px !important;
                gap: 3px !important;
            }

            .isd-machinelab {
                font-size: 7px !important;
                line-height: 1.1 !important;
                min-height: 40px !important;
                padding-top: 3px !important;
                overflow: visible !important;
                white-space: nowrap !important;
                transform: rotate(-45deg) !important;
                transform-origin: top center !important;
            }

            .isd-avgline {
                left: 56px !important;
                right: 10px !important;
            }

            .isd-avgline.isd-avg-85 {
                top: calc(10px + 220px * 0.15) !important;
            }

            .isd-avgline.isd-avg-80 {
                top: calc(10px + 220px * 0.20) !important;
            }

            @page {
                size: A4 landscape;
                margin: 4mm;
            }

            .print-actions {
                display: none !important;
            }

            .isd-note {
                font-size: 9px !important;
                margin-bottom: 4px !important;
                padding: 4px !important;
            }

            .isd-site-title {
                font-size: 10px !important;
                padding: 5px !important;
            }

            .isd-band {
                padding: 5px !important;
            }

            .isd-metrics {
                grid-template-columns: repeat(10, 1fr) !important;
                gap: 4px !important;
            }

            .isd-metric {
                padding: 4px !important;
            }

            .isd-metric-title {
                font-size: 7px !important;
                margin-bottom: 3px !important;
            }

            .isd-mbubble {
                width: 36px !important;
                min-height: 36px !important;
                padding: 3px !important;
            }

            .isd-mbubble-label {
                font-size: 5px !important;
            }

            .isd-mbubble-value {
                font-size: 7px !important;
            }

            .isd-chart-section-title {
                font-size: 15px !important;
                padding: 5px !important;
            }

            .isd-chart {
                padding: 6px 8px 8px !important;
            }

            .isd-chart-grid {
                height: 210px !important;
            }

            .isd-yaxis {
                font-size: 8px !important;
                top: 6px !important;
                bottom: 36px !important;
            }

            .isd-avgline {
                left: 50px !important;
                right: 8px !important;
            }

            .isd-avgline.isd-avg-85 {
                top: calc(6px + 210px * 0.15) !important;
            }

            .isd-avgline.isd-avg-80 {
                top: calc(6px + 210px * 0.20) !important;
            }

            .isd-chart {
                padding: 12px 12px 30px 12px !important;
            }

            .isd-yaxis {
                left: 12px !important;
                top: 12px !important;
                bottom: 52px !important;
                width: 36px !important;
                text-align: right !important;
            }

            .isd-chart-grid {
                margin-left: 46px !important;
                height: 220px !important;
                border-bottom: 2px solid rgba(255,255,255,0.75) !important;
            }

            .isd-machinelabels {
                margin-left: 46px !important;
                margin-top: 7px !important;
                min-height: 26px !important;
            }

            .isd-machinelab {
                font-size: 7px !important;
                line-height: 1.1 !important;
                min-height: 20px !important;
                padding-top: 3px !important;
                overflow: visible !important;
                white-space: nowrap !important;
            }

            .isd-avgline {
                left: 58px !important;
                right: 12px !important;
            }

            .isd-avgline.isd-avg-85 {
                top: calc(12px + 220px * 0.15) !important;
            }

            .isd-avgline.isd-avg-80 {
                top: calc(12px + 220px * 0.20) !important;
            }

        }
    </style>
</head>

<body>
    <div class="print-actions">
        <button onclick="window.print()">Print / Save as PDF</button>
        <button onclick="window.close()">Close</button>
        <span class="print-help">Preview is readable. To save: Print / Save as PDF, Landscape, Background graphics. Use browser zoom if needed.</span>
    </div>

    ${html}

<script>
function freezePreviewAxes() {
    document.querySelectorAll(".isd-chart-section").forEach(function(section) {
        var axis = section.querySelector(".isd-yaxis");
        if (!axis) return;

        function moveAxis() {
            axis.style.transform = "translateX(" + section.scrollLeft + "px)";
        }

        if (!section.__isdPreviewAxisFreezeBound) {
            section.addEventListener("scroll", moveAxis, { passive: true });
            section.__isdPreviewAxisFreezeBound = true;
        }

        moveAxis();
    });
}

window.addEventListener("load", function() {
    freezePreviewAxes();
    setTimeout(freezePreviewAxes, 200);
    setTimeout(freezePreviewAxes, 600);
    setTimeout(freezePreviewAxes, 1200);
});
</script>

</body>
</html>
    `);

    print_window.document.close();
}


function freeze_percentage_axis_on_scroll(report) {
    const apply_freeze = () => {
        if (!report || !report.page || !report.page.wrapper) {
            return;
        }

        const wrapper = report.page.wrapper;

        wrapper.find(".isd-chart-section").each(function () {
            const section = this;
            const axis = $(section).find(".isd-yaxis").first();

            if (!axis.length) {
                return;
            }

            const move_axis = () => {
                axis.css("transform", "translateX(" + section.scrollLeft + "px)");
            };

            if (!section.__isd_axis_freeze_bound) {
                section.addEventListener("scroll", move_axis, { passive: true });
                section.__isd_axis_freeze_bound = true;
            }

            move_axis();
        });
    };

    setTimeout(apply_freeze, 0);
    setTimeout(apply_freeze, 200);
    setTimeout(apply_freeze, 600);
    setTimeout(apply_freeze, 1200);
}

