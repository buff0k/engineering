frappe.pages["tyre-dashboard"].on_page_load = function (wrapper) {
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
            .tyre-panel.wide { grid-column: 1 / -1; }
            .tyre-panel h4 { margin: 0 0 12px; font-size: 15px; font-weight: 600; }
            .tyre-chart { min-height: 270px; }
            .adt-view { margin-bottom: 18px; }
            .adt-layout { display: grid; grid-template-columns: minmax(245px, 1fr) minmax(240px, 0.8fr) minmax(245px, 1fr); gap: 18px; align-items: center; }
            .adt-layout-image { width: 100%; max-height: 620px; object-fit: contain; }
            .adt-card-column { display: flex; flex-direction: column; gap: 10px; }
            .adt-tyre-card { border: 1px solid var(--border-color); border-left: 5px solid #1565c0; border-radius: 8px; padding: 11px; background: var(--fg-color); }
            .adt-tyre-card.critical { border-left-color: #d32f2f; }
            .adt-tyre-card.warning { border-left-color: #f57c00; }
            .adt-tyre-card.check { border-left-color: #fbc02d; }
            .adt-tyre-card.good { border-left-color: #2e7d32; }
            .adt-tyre-card .title { font-weight: 700; margin-bottom: 5px; }
            .adt-tyre-card .spec-list { color: var(--text-muted); font-size: 12px; line-height: 1.55; margin: 7px 0 0; padding-left: 19px; }
            .adt-tyre-card .spec-list li { margin: 1px 0; }
            .adt-tyre-card .spec-list strong { color: var(--text-color); font-weight: 600; }
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
            <div class="tyre-panel wide">
                <h4>${__("Mock Grader Utilisation vs Mock Tyre Damage")}</h4>
                <div class="dashboard-note">${__("Development-only synthetic comparison. This panel does not use or alter actual Availability and Utilisation records.")}</div>
                <div id="mock-grader-damage-chart" class="tyre-chart"></div>
            </div>
        </div>
        <div class="tyre-panel">
            <h4>${__("Top 10 Urgent Tyres")}</h4>
            <div id="urgent-list"></div>
        </div>
    `);

    asOnDate.$input.on("change", loadDashboard);
    site.$input.on("change", loadDashboard);
    fleetNumber.$input.attr(
        "placeholder",
        __("Type or select an ADT fleet number, then press Enter")
    );
    fleetNumber.$input.on("keyup.tyre-dashboard-enter", event => {
        if (event.key !== "Enter" && event.keyCode !== 13) {
            return;
        }

        // Enter selects the highlighted Link result on keydown. Waiting until
        // keyup lets Frappe commit and validate the Asset before we read it.
        window.setTimeout(loadDashboard, 0);
    });

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

    function renderMockGraderDamage(items) {
        const selector = "#mock-grader-damage-chart";
        $(selector).empty();

        if (!items.length) {
            $(selector).html(`<div class="dashboard-empty">${__("Mock comparison data has not been installed.")}</div>`);
            return;
        }

        new frappe.Chart(selector, {
            data: {
                labels: items.map(item => item.label),
                datasets: [
                    {
                        name: __("Mock damaged tyres"),
                        chartType: "bar",
                        values: items.map(item => item.damaged_tyres),
                    },
                    {
                        name: __("Mock grader utilisation %"),
                        chartType: "line",
                        values: items.map(item => item.grader_utilisation),
                    },
                ],
            },
            type: "axis-mixed",
            height: 280,
            colors: ["#d32f2f", "#1565c0"],
            axisOptions: { xIsSeries: true },
            barOptions: { spaceRatio: 0.4 },
            lineOptions: { regionFill: 0, hideDots: 0 },
        });
    }

    function tyreCard(tyre) {
        const brand = [tyre.tyre_make, tyre.tread_pattern].filter(Boolean).join(" · ") || "—";
        const remainingLife = tyre.remaining_months === null || tyre.remaining_months === undefined
            ? "—"
            : `${tyre.remaining_months} months`;
        const pressure = tyre.actual_pressure || tyre.recommended_pressure
            ? `${tyre.actual_pressure ?? "—"} / ${tyre.recommended_pressure ?? "—"}`
            : "—";

        return `
            <div class="adt-tyre-card ${bandClass(tyre.urgency_band)}">
                <div class="title">${escape(tyre.position)} — ${escape(tyre.urgency_band)}</div>
                <ul class="spec-list">
                    <li><strong>${__("Serial")}:</strong> ${escape(tyre.serial_number || "—")}</li>
                    <li><strong>${__("Brand & pattern")}:</strong> ${escape(brand)}</li>
                    <li><strong>${__("OTD")}:</strong> ${escape(tyre.otd ?? "—")} mm</li>
                    <li><strong>${__("RTD")}:</strong> ${escape(tyre.average_rtd ?? "—")} mm (${escape(tyre.rtd_percent ?? "—")}%)</li>
                    <li><strong>${__("Wear rate")}:</strong> ${escape(tyre.wear_rate ?? "—")} mm/month</li>
                    <li><strong>${__("Pressure actual / recommended")}:</strong> ${escape(pressure)}</li>
                    <li><strong>${__("Scrap limit")}:</strong> ${escape(tyre.scrap_limit_mm)} mm</li>
                    <li><strong>${__("Replace by")}:</strong> ${escape(displayDate(tyre.replacement_date))}</li>
                    <li><strong>${__("Remaining life")}:</strong> ${escape(remainingLife)}</li>
                </ul>
            </div>
        `;
    }

    function renderAdt(view) {
        if (!view.fleet_number) {
            $("#adt-layout").html(`<div class="dashboard-empty">${__("Select an ADT above to display its tyre layout and latest readings.")}</div>`);
            return;
        }

        const special = view.tyre_layout === "b60e" || view.tyres.some(tyre => ["RRO", "RRI", "LRI", "LRO"].includes(String(tyre.position).toUpperCase()));
        const leftOrder = special ? ["LF", "LRO", "LRI"] : ["LF", "LM", "LR"];
        const rightOrder = special ? ["RF", "RRI", "RRO"] : ["RF", "RM", "RR"];
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
                    <div style="text-align:center;font-weight:700;margin-bottom:8px;">
                        ${escape(view.fleet_number)} · ${escape(view.vehicle_make)} ${escape(view.model)} · ${escape(view.site)}
                    </div>
                    <img class="adt-layout-image" src="${escape(view.layout_image)}" alt="ADT tyre layout">
                    ${view.tyres.length ? "" : `<div class="dashboard-empty">${__("No latest tyre survey was found for this ADT.")}</div>`}
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
        renderMockGraderDamage(data.mock_grader_damage || []);
        renderUrgent(data.urgent_tyres);
    }

    function loadDashboard() {
        frappe.call({
            method: "engineering.engineering.page.tyre_dashboard.tyre_dashboard.get_dashboard_data",
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
