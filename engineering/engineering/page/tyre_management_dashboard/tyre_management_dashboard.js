frappe.pages["tyre-management-dashboard"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __("Tyre Management Dashboard"),
        single_column: true,
    });

    const asOnDate = page.add_field({
        fieldname: "as_on_date",
        label: __("As On Date"),
        fieldtype: "Date",
        default: frappe.datetime.get_today(),
    });
    const site = page.add_field({
        fieldname: "site",
        label: __("Site"),
        fieldtype: "Link",
        options: "Location",
    });
    const fleetNumber = page.add_field({
        fieldname: "fleet_number",
        label: __("ADT Six-Wheel View"),
        fieldtype: "Link",
        options: "Asset",
        get_query() {
            return { filters: { asset_category: "ADT" } };
        },
    });

    page.set_primary_action(__("Refresh"), loadDashboard, "refresh");
    page.add_inner_button(__("Urgency Report"), () => {
        frappe.set_route("query-report", "Tyre Urgency Report");
    });
    page.add_inner_button(__("Replacement Forecast"), () => {
        frappe.set_route("query-report", "Tyre Replacement Forecast");
    });
    page.add_inner_button(__("ADT Detail Report"), () => {
        frappe.set_route("query-report", "ADT Six Wheel Status");
    });

    const $container = $("<div class='tyre-dashboard'></div>").appendTo(page.main);

    $container.html(`
        <style>
            .tyre-dashboard { padding: 18px 4px 40px; }
            .tyre-dashboard .dashboard-note { color: var(--text-muted); margin-bottom: 14px; }
            .tyre-kpis { display: grid; grid-template-columns: repeat(6, minmax(130px, 1fr)); gap: 12px; margin-bottom: 18px; }
            .tyre-kpi { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; padding: 14px; min-height: 92px; }
            .tyre-kpi .value { font-size: 28px; font-weight: 700; line-height: 1.1; }
            .tyre-kpi .label { color: var(--text-muted); margin-top: 8px; font-size: 12px; }
            .tyre-kpi.red { border-top: 4px solid #d32f2f; }
            .tyre-kpi.orange { border-top: 4px solid #f57c00; }
            .tyre-kpi.blue { border-top: 4px solid #1565c0; }
            .tyre-kpi.green { border-top: 4px solid #2e7d32; }
            .tyre-chart-grid { display: grid; grid-template-columns: repeat(2, minmax(360px, 1fr)); gap: 14px; margin-bottom: 18px; }
            .tyre-panel { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; padding: 16px; }
            .tyre-panel h4 { margin: 0 0 12px; font-size: 15px; font-weight: 600; }
            .tyre-chart { min-height: 270px; }
            .adt-view { margin-bottom: 18px; }
            .adt-layout { display: grid; grid-template-columns: minmax(245px, 1fr) minmax(240px, 0.8fr) minmax(245px, 1fr); gap: 18px; align-items: center; }
            .adt-layout-image { width: 100%; max-height: 420px; object-fit: contain; }
            .adt-card-column { display: flex; flex-direction: column; gap: 10px; }
            .adt-tyre-card { border: 1px solid var(--border-color); border-left: 5px solid #1565c0; border-radius: 8px; padding: 11px; background: var(--fg-color); }
            .adt-tyre-card.critical { border-left-color: #d32f2f; }
            .adt-tyre-card.warning { border-left-color: #f57c00; }
            .adt-tyre-card.check { border-left-color: #fbc02d; }
            .adt-tyre-card.good { border-left-color: #2e7d32; }
            .adt-tyre-card .title { font-weight: 700; margin-bottom: 5px; }
            .adt-tyre-card .serial { font-family: monospace; margin-bottom: 5px; }
            .adt-tyre-card .spec { color: var(--text-muted); font-size: 12px; line-height: 1.55; }
            .urgent-table { width: 100%; border-collapse: collapse; }
            .urgent-table th, .urgent-table td { border-bottom: 1px solid var(--border-color); padding: 8px; text-align: left; font-size: 12px; }
            .urgent-table th { color: var(--text-muted); font-weight: 600; }
            .band { font-weight: 700; }
            .band.critical { color: #d32f2f; }
            .band.warning { color: #f57c00; }
            .band.check { color: #b8860b; }
            .dashboard-empty { padding: 30px; text-align: center; color: var(--text-muted); }
            @media (max-width: 1100px) {
                .tyre-kpis { grid-template-columns: repeat(3, 1fr); }
                .adt-layout { grid-template-columns: 1fr; }
                .adt-layout-image { max-height: 300px; order: -1; }
            }
            @media (max-width: 760px) {
                .tyre-kpis, .tyre-chart-grid { grid-template-columns: 1fr; }
            }
        </style>
        <div class="dashboard-note">${__("Latest survey condition and forecast using a 14 mm scrap limit.")}</div>
        <div class="tyre-kpis" id="tyre-kpis"></div>
        <div class="tyre-panel adt-view">
            <h4>${__("ADT Six-Wheel Condition")}</h4>
            <div id="adt-layout"></div>
        </div>
        <div class="tyre-chart-grid">
            <div class="tyre-panel"><h4>${__("Five-Month Replacement Forecast")}</h4><div id="forecast-chart" class="tyre-chart"></div></div>
            <div class="tyre-panel"><h4>${__("Urgency Distribution")}</h4><div id="urgency-chart" class="tyre-chart"></div></div>
            <div class="tyre-panel"><h4>${__("Average Wear by Site")}</h4><div id="site-wear-chart" class="tyre-chart"></div></div>
            <div class="tyre-panel"><h4>${__("Average Wear by Brand")}</h4><div id="brand-wear-chart" class="tyre-chart"></div></div>
            <div class="tyre-panel"><h4>${__("Pressure Compliance by Site")}</h4><div id="pressure-chart" class="tyre-chart"></div></div>
        </div>
        <div class="tyre-panel">
            <h4>${__("Top 10 Urgent Tyres")}</h4>
            <div id="urgent-list"></div>
        </div>
    `);

    asOnDate.$input.on("change", loadDashboard);
    site.$input.on("change", loadDashboard);
    fleetNumber.$input.on("change", loadDashboard);

    function escape(value) {
        return frappe.utils.escape_html(String(value ?? ""));
    }

    function displayDate(value) {
        return value ? frappe.datetime.str_to_user(value) : "—";
    }

    function bandClass(value) {
        return String(value || "normal").toLowerCase();
    }

    function renderKpis(kpis) {
        const cards = [
            [kpis.tyres_analysed, __("Tyres Analysed"), "blue"],
            [kpis.critical, __("Critical"), "red"],
            [kpis.warning, __("Warning"), "orange"],
            [kpis.due_within_30_days, __("Due Within 30 Days"), "red"],
            [kpis.below_25_percent, __("Below 25% Tread"), "orange"],
            [kpis.underinflated, __("Underinflated >10%"), "orange"],
        ];
        $("#tyre-kpis").html(cards.map(([value, label, colour]) => `
            <div class="tyre-kpi ${colour}">
                <div class="value">${escape(value)}</div>
                <div class="label">${escape(label)}</div>
            </div>
        `).join(""));
    }

    function chart(selector, items, type, colour, datasetName) {
        $(selector).empty();
        new frappe.Chart(selector, {
            data: {
                labels: items.map(item => item.label),
                datasets: [{ name: datasetName, values: items.map(item => item.value) }],
            },
            type,
            height: 250,
            colors: colour,
            axisOptions: { xIsSeries: true },
            barOptions: { spaceRatio: 0.35 },
        });
    }

    function tyreCard(tyre) {
        return `
            <div class="adt-tyre-card ${bandClass(tyre.urgency_band)}">
                <div class="title">${escape(tyre.position)} — ${escape(tyre.urgency_band)}</div>
                <div class="serial">${escape(tyre.serial_number)}</div>
                <div class="spec">
                    ${escape(tyre.tyre_make)} ${escape(tyre.tread_pattern)}<br>
                    RTD: ${escape(tyre.average_rtd)} mm (${escape(tyre.rtd_percent)}%)<br>
                    Wear: ${escape(tyre.wear_rate)} mm/month<br>
                    Pressure variance: ${escape(tyre.pressure_variance)}%<br>
                    Replace by: ${escape(displayDate(tyre.replacement_date))}
                </div>
            </div>
        `;
    }

    function renderAdt(view) {
        if (!view.fleet_number) {
            $("#adt-layout").html(`<div class="dashboard-empty">${__("Select an ADT above to display its six tyres.")}</div>`);
            return;
        }

        if (!view.tyres.length) {
            $("#adt-layout").html(`<div class="dashboard-empty">${__("No latest tyre survey was found for this ADT.")}</div>`);
            return;
        }

        const special = view.tyres.some(tyre => ["RRO", "RRI", "LRI", "LRO"].includes(String(tyre.position).toUpperCase()));
        const leftOrder = special ? ["LF", "LRI", "LRO"] : ["LF", "LR", "LM"];
        const rightOrder = special ? ["RF", "RRO", "RRI"] : ["RF", "RR", "RM"];
        const order = positions => positions.map(position => view.tyres.find(tyre => String(tyre.position).toUpperCase() === position)).filter(Boolean);
        const left = order(leftOrder);
        const right = order(rightOrder);
        const assigned = new Set([...left, ...right].map(tyre => tyre.serial_number));
        const extras = view.tyres.filter(tyre => !assigned.has(tyre.serial_number));
        extras.forEach((tyre, index) => (index % 2 ? right : left).push(tyre));

        $("#adt-layout").html(`
            <div class="adt-layout">
                <div class="adt-card-column">${left.map(tyreCard).join("")}</div>
                <div>
                    <div style="text-align:center;font-weight:700;margin-bottom:8px;">${escape(view.fleet_number)} · ${escape(view.site)}</div>
                    <img class="adt-layout-image" src="${escape(view.layout_image)}" alt="ADT tyre layout">
                </div>
                <div class="adt-card-column">${right.map(tyreCard).join("")}</div>
            </div>
        `);
    }

    function renderUrgent(rows) {
        if (!rows.length) {
            $("#urgent-list").html(`<div class="dashboard-empty">${__("No tyre records were found.")}</div>`);
            return;
        }

        $("#urgent-list").html(`
            <div style="overflow:auto;">
                <table class="urgent-table">
                    <thead><tr>
                        <th>#</th><th>${__("ADT")}</th><th>${__("Site")}</th><th>${__("Position")}</th>
                        <th>${__("Serial")}</th><th>${__("RTD")}</th><th>${__("Wear")}</th>
                        <th>${__("Months Left")}</th><th>${__("Replace By")}</th><th>${__("Band")}</th>
                    </tr></thead>
                    <tbody>${rows.map((row, index) => `
                        <tr>
                            <td>${index + 1}</td><td>${escape(row.fleet_number)}</td><td>${escape(row.site)}</td>
                            <td>${escape(row.position)}</td><td>${escape(row.serial_number)}</td>
                            <td>${escape(row.average_rtd)} mm</td><td>${escape(row.wear_rate)}</td>
                            <td>${escape(row.remaining_months ?? "—")}</td><td>${escape(displayDate(row.replacement_date))}</td>
                            <td class="band ${bandClass(row.urgency_band)}">${escape(row.urgency_band)}</td>
                        </tr>
                    `).join("")}</tbody>
                </table>
            </div>
        `);
    }

    function render(data) {
        renderKpis(data.kpis);
        renderAdt(data.adt_view);
        chart("#forecast-chart", data.replacement_forecast, "bar", ["#e0a800"], __("Tyres"));
        chart("#urgency-chart", data.urgency_bands, "bar", ["#d32f2f"], __("Tyres"));
        chart("#site-wear-chart", data.site_wear, "bar", ["#1565c0"], __("mm/month"));
        chart("#brand-wear-chart", data.brand_wear, "bar", ["#00897b"], __("mm/month"));
        chart("#pressure-chart", data.pressure_compliance, "bar", ["#2e7d32"], __("Compliance %"));
        renderUrgent(data.urgent_tyres);
    }

    function loadDashboard() {
        frappe.call({
            method: "engineering.engineering.page.tyre_management_dashboard.tyre_management_dashboard.get_dashboard_data",
            args: {
                as_on_date: asOnDate.get_value(),
                site: site.get_value(),
                fleet_number: fleetNumber.get_value(),
            },
            freeze: true,
            freeze_message: __("Loading tyre dashboard..."),
        }).then(response => render(response.message));
    }

    loadDashboard();
};
