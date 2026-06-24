// Copyright (c) 2026, BuFf0k and contributors
// For license information, please see license.txt

frappe.pages["weekly-availability-"].on_page_load = function (wrapper) {
  render_weekly_availability_dashboard_page(wrapper);
};

function render_weekly_availability_dashboard_page(wrapper) {
  const REPORT_NAME = "Weekly Availability and Utilisation Dashboard";
  const STORAGE_KEY = "weekly_availability_dashboard_filters";

  const UI_CATEGORIES = ["ADTs", "Excavators", "Dozers"];
  const ASSETS_PER_VISUAL_ROW = 24;

  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Weekly Availability and Utilisation Dashboard",
    single_column: true
  });

  let _refreshing = false;
  let _auto_load_timer = null;

  const site_group = page.add_field({
    fieldtype: "Select",
    label: __("Complex"),
    fieldname: "site_group",
    options: ["", "All", "Seriti Sites", "Other"],
    default: "All",
    change: () => {
      save_filters();
      auto_load();
    }
  });

  const from_date = page.add_field({
    fieldtype: "Date",
    label: __("From Date"),
    fieldname: "from_date",
    default: frappe.datetime.add_days(frappe.datetime.get_today(), -7),
    change: () => {
      save_filters();
      auto_load();
    }
  });

  const to_date = page.add_field({
    fieldtype: "Date",
    label: __("To Date"),
    fieldname: "to_date",
    default: frappe.datetime.add_days(frappe.datetime.get_today(), -1),
    change: () => {
      save_filters();
      auto_load();
    }
  });

  page.add_inner_button(__("Load Dashboard"), () => {
    save_filters();
    load_and_render(false);
  });

  const $wrap = $(`<div class="eng-dashboard eng-dashboard--weekly-availability"></div>`).appendTo(page.main);
  const $status = $(`<div class="eng-dashboard-status text-muted"></div>`).appendTo($wrap);
  const $dash = $(`<div class="eng-weekly-grid"></div>`).appendTo($wrap);

  function get_filters() {
    return {
      site_group: site_group.get_value(),
      from_date: from_date.get_value(),
      to_date: to_date.get_value()
    };
  }

  function has_required_filters(filters) {
    return !!(filters.from_date && filters.to_date);
  }

  function save_filters() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(get_filters()));
  }

  function restore_filters() {
    let saved = {};

    try {
      saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    } catch (e) {
      saved = {};
    }

    if (saved.site_group !== undefined) {
      site_group.set_value(saved.site_group);
    }

    if (saved.from_date) {
      from_date.set_value(saved.from_date);
    }

    if (saved.to_date) {
      to_date.set_value(saved.to_date);
    }
  }

  function auto_load() {
    clearTimeout(_auto_load_timer);

    _auto_load_timer = setTimeout(() => {
      const filters = get_filters();

      if (!has_required_filters(filters)) {
        $status.text("Select From Date and To Date to load the dashboard.");
        $dash.empty();
        return;
      }

      load_and_render(false);
    }, 400);
  }

  function run_report(filters) {
    return new Promise((resolve, reject) => {
      frappe.call({
        method: "frappe.desk.query_report.run",
        args: {
          report_name: REPORT_NAME,
          filters: filters
        },
        freeze: false,
        callback: function (r) {
          resolve(r);
        },
        error: function (r) {
          reject(r);
        }
      });
    });
  }

  function extract_rows_from_response(res) {
    const payload = res && res.message ? res.message : res;

    if (!payload) {
      return [];
    }

    if (Array.isArray(payload.result)) {
      return payload.result;
    }

    if (Array.isArray(payload.data)) {
      return payload.data;
    }

    if (Array.isArray(payload)) {
      return payload;
    }

    return [];
  }

  function parse_json_array(value, fallback) {
    fallback = fallback || [];

    if (Array.isArray(value)) {
      return value;
    }

    if (value == null || value === "") {
      return fallback;
    }

    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : fallback;
    } catch (e) {
      return fallback;
    }
  }

  function parse_json_object(value, fallback) {
    fallback = fallback || {};

    if (value && typeof value === "object" && !Array.isArray(value)) {
      return value;
    }

    if (value == null || value === "") {
      return fallback;
    }

    try {
      const parsed = JSON.parse(value);

      return parsed && typeof parsed === "object" && !Array.isArray(parsed)
        ? parsed
        : fallback;
    } catch (e) {
      return fallback;
    }
  }

  function escape_html(value) {
    return frappe.utils.escape_html(value == null ? "" : String(value));
  }

  function normalise_int(value) {
    const parsed = parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function slugify(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/&/g, "and")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function is_sunday(dateValue) {
    if (!dateValue) {
      return false;
    }

    const date = new Date(`${dateValue}T00:00:00`);
    return date.getDay() === 0;
  }

  function fmt_percent(value) {
    if (value === null || value === undefined || value === "") {
      return "";
    }

    const numberValue = Number(value);

    if (!Number.isFinite(numberValue)) {
      return "";
    }

    return `${numberValue.toFixed(1)}%`;
  }

  function metric_colour_class(metric, value) {
    if (value === null || value === undefined || value === "") {
      return "";
    }

    const v = Number(value);

    if (!Number.isFinite(v)) {
      return "";
    }

    if (metric === "avail") {
      if (v >= 85) {
        return "eng-bubble--green";
      }

      if (v >= 75) {
        return "eng-bubble--blue";
      }

      return "eng-bubble--red";
    }

    if (v >= 80) {
      return "eng-bubble--green";
    }

    if (v >= 70) {
      return "eng-bubble--blue";
    }

    return "eng-bubble--red";
  }

  function trend_state(seriesMap, metric) {
    const points = [];

    for (let i = 0; i < 7; i++) {
      const bucketValues = [];
      let pointDate = null;

      UI_CATEGORIES.forEach((label) => {
        let items = seriesMap[label] || [];

        if (items.length < 7) {
          const padding = Array.from({ length: 7 - items.length }, () => ({
            date: "",
            avail: null,
            util: null
          }));

          items = padding.concat(items);
        } else {
          items = items.slice(-7);
        }

        pointDate = items[i].date || pointDate;

        const v = items[i][metric];

        if (v !== null && v !== undefined && v !== "") {
          const numberValue = Number(v);

          if (Number.isFinite(numberValue)) {
            bucketValues.push(numberValue);
          }
        }
      });

      if (is_sunday(pointDate)) {
        points.push(null);
      } else {
        points.push(
          bucketValues.length
            ? bucketValues.reduce((total, value) => total + value, 0) / bucketValues.length
            : null
        );
      }
    }

    const clean = points.filter((point) => point !== null && point !== undefined);

    if (clean.length < 2) {
      return "neutral";
    }

    const delta = clean[clean.length - 1] - clean[0];

    if (delta > 0.0001) {
      return "up";
    }

    if (delta < -0.0001) {
      return "down";
    }

    return "neutral";
  }

  function trend_word(state) {
    if (state === "down") {
      return "Downtrend";
    }

    if (state === "up") {
      return "Uptrend";
    }

    return "Neutral";
  }

  function circle_class(state) {
    if (state === "down") {
      return "eng-circle eng-circle--red";
    }

    if (state === "up") {
      return "eng-circle eng-circle--green";
    }

    return "eng-circle eng-circle--blue";
  }

  function bar_height(value) {
    if (value === null || value === undefined || value === "") {
      return 2;
    }

    const numberValue = Math.max(0, Math.min(100, Number(value)));

    if (!Number.isFinite(numberValue)) {
      return 2;
    }

    return Math.max(2, Math.round(numberValue * 1.2));
  }

  function report_url(site, fromDate, toDate) {
    const route = "Avail%20and%20Util%20summary";

    return `/app/query-report/${route}`
      + `?start_date=${encodeURIComponent(fromDate)}`
      + `&end_date=${encodeURIComponent(toDate)}`
      + `&location=${encodeURIComponent(site)}`;
  }

  function normalise_assets(items) {
    items = Array.isArray(items) ? items : [];

    return items.filter((item) => {
      return item && item.plant_no;
    });
  }

  function chunk_array(items, chunkSize) {
    const chunks = [];

    for (let i = 0; i < items.length; i += chunkSize) {
      chunks.push(items.slice(i, i + chunkSize));
    }

    return chunks;
  }

  function render_metric_pills(averages) {
    return UI_CATEGORIES.map((category) => {
      const average = averages[category] || {};
      const avValue = average.avail;
      const utValue = average.util;

      return `
        <div class="eng-metric">
          <div class="eng-metric-title">${escape_html(category)} (Avg)</div>

          <div class="eng-pill-row">
            <div class="eng-bubble ${metric_colour_class("avail", avValue)}">
              <div class="eng-bubble-label">Availability</div>
              <div class="eng-bubble-value">${escape_html(fmt_percent(avValue))}</div>
            </div>

            <div class="eng-bubble ${metric_colour_class("util", utValue)}">
              <div class="eng-bubble-label">Utilisation</div>
              <div class="eng-bubble-value">${escape_html(fmt_percent(utValue))}</div>
            </div>
          </div>
        </div>
      `;
    }).join("");
  }

  function render_asset_tile(item) {
    const availabilityText = fmt_percent(item.avail) || "No Availability Data";
    const utilisationText = fmt_percent(item.util) || "No Utilisation Data";

    return `
      <div class="eng-asset-tile">
        <div class="eng-asset-bars">
          <div
            class="eng-bar eng-bar--availability"
            title="${escape_html(item.plant_no)} Availability: ${escape_html(availabilityText)}"
            style="height:${bar_height(item.avail)}px"
          ></div>
          <div
            class="eng-bar eng-bar--utilisation"
            title="${escape_html(item.plant_no)} Utilisation: ${escape_html(utilisationText)}"
            style="height:${bar_height(item.util)}px"
          ></div>
        </div>

        <div
          class="eng-asset-label"
          title="${escape_html(item.plant_no)}"
        >
          ${escape_html(item.plant_no)}
        </div>
      </div>
    `;
  }

  function render_asset_visual_row(items, rowIndex) {
    const count = Math.max(items.length, 1);

    return `
      <div class="eng-asset-visual-row" data-row-index="${rowIndex}">
        <div class="eng-yaxis eng-yaxis--asset-row">
          <div>100%</div>
          <div>80%</div>
          <div>60%</div>
          <div>40%</div>
          <div>20%</div>
          <div>0%</div>
        </div>

        <div class="eng-asset-line-scroll">
          <div class="eng-asset-line-inner" style="--eng-asset-count:${count};">
            <div class="eng-asset-line-grid">
              ${items.map(render_asset_tile).join("")}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function render_asset_group(category, assetSeriesMap) {
    const items = normalise_assets(assetSeriesMap[category] || []);

    if (!items.length) {
      return `
        <div class="eng-asset-row">
          <div class="eng-asset-row-head">
            <div class="eng-asset-row-title">${escape_html(category)}</div>
            <div class="eng-asset-row-subtitle">Availability / Utilisation by plant no.</div>
          </div>

          <div class="eng-asset-row-body">
            <div class="eng-asset-empty">
              No asset data
            </div>
          </div>
        </div>
      `;
    }

    const chunks = chunk_array(items, ASSETS_PER_VISUAL_ROW);

    return `
      <div class="eng-asset-row">
        <div class="eng-asset-row-head">
          <div class="eng-asset-row-title">${escape_html(category)}</div>
          <div class="eng-asset-row-subtitle">Availability / Utilisation by plant no.</div>
        </div>

        <div class="eng-asset-row-body">
          ${chunks.map((chunk, index) => {
            return render_asset_visual_row(chunk, index);
          }).join("")}
        </div>
      </div>
    `;
  }

  function render_chart(assetSeriesMap) {
    return `
      <div class="eng-category-chart">
        ${UI_CATEGORIES.map((category) => {
          return render_asset_group(category, assetSeriesMap);
        }).join("")}
      </div>
    `;
  }

  function render_trend_summary(site, fromDate, toDate, seriesMap) {
    const availabilityState = trend_state(seriesMap, "avail");
    const utilisationState = trend_state(seriesMap, "util");
    const href = report_url(site, fromDate, toDate);

    return `
      <div class="eng-trend-summary">
        <div class="eng-trend-bubbles">
          <a class="eng-trend-link" target="_blank" rel="noopener" href="${escape_html(href)}">
            <div class="${circle_class(availabilityState)} eng-circle--heading">
              <span class="eng-circle-kicker">Availability</span>
              <span class="eng-circle-main">${escape_html(trend_word(availabilityState))}</span>
            </div>
          </a>

          <a class="eng-trend-link" target="_blank" rel="noopener" href="${escape_html(href)}">
            <div class="${circle_class(utilisationState)} eng-circle--heading">
              <span class="eng-circle-kicker">Utilisation</span>
              <span class="eng-circle-main">${escape_html(trend_word(utilisationState))}</span>
            </div>
          </a>
        </div>

        <div class="eng-legend eng-legend--heading">
          <span class="eng-legend-item">
            <i class="eng-legend-swatch eng-legend-swatch--availability"></i>
            Availability
          </span>
          <span class="eng-legend-item">
            <i class="eng-legend-swatch eng-legend-swatch--utilisation"></i>
            Utilisation
          </span>
        </div>
      </div>
    `;
  }

  function render_site(row) {
    const site = row.site || "";
    const fromDate = row.from_date || "";
    const toDate = row.to_date || "";

    const averages = parse_json_object(row.averages_json, {});
    const seriesMap = parse_json_object(row.series_json, {});
    const assetSeriesMap = parse_json_object(row.asset_series_json, {});
    const dateList = parse_json_array(row.date_list_json, []);

    const startLabel = dateList.length ? dateList[0] : fromDate;
    const endLabel = dateList.length ? dateList[dateList.length - 1] : toDate;

    return `
      <div class="eng-site eng-site--${escape_html(slugify(site))}">
        <div class="eng-site-heading">
          <div class="eng-site-title">
            ${escape_html(site)} • ${escape_html(startLabel)} → ${escape_html(endLabel)}
          </div>

          ${render_trend_summary(site, fromDate, toDate, seriesMap)}
        </div>

        <div class="eng-band">
          <div class="eng-metrics">
            ${render_metric_pills(averages)}
          </div>
        </div>

        <div class="eng-site-main">
          ${render_chart(assetSeriesMap)}
        </div>
      </div>
    `;
  }

  function render_dashboard(rows) {
    if (!rows.length) {
      $dash.html(`
        <div class="eng-empty">
          No availability and utilisation data found for the selected filters.
        </div>
      `);
      return;
    }

    const sorted = [...rows].sort((a, b) => {
      const aOrder = normalise_int(a.site_order);
      const bOrder = normalise_int(b.site_order);

      if (aOrder !== bOrder) {
        return aOrder - bOrder;
      }

      return String(a.site || "").localeCompare(String(b.site || ""));
    });

    $dash.html(sorted.map(render_site).join(""));
  }

  function load_and_render(isAuto) {
    const filters = get_filters();

    if (!has_required_filters(filters)) {
      $status.text("Select From Date and To Date to load the dashboard.");
      $dash.empty();
      return;
    }

    if (_refreshing) {
      return;
    }

    _refreshing = true;
    $status.text(isAuto ? "Refreshing..." : "Loading...");

    run_report(filters)
      .then((res) => {
        const rows = extract_rows_from_response(res);

        render_dashboard(rows);

        const time = new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit"
        });

        $status.text(`Last updated: ${time}`);

        if (isAuto) {
          frappe.show_alert(
            {
              message: `Weekly Availability Dashboard updated at ${time}`,
              indicator: "green"
            },
            5
          );
        }

        _refreshing = false;
      })
      .catch((e) => {
        console.error(e);

        $status.text("Error loading Weekly Availability and Utilisation Dashboard.");
        $dash.html(`
          <div class="eng-error">
            Could not load dashboard. Check console / server logs.
          </div>
        `);

        _refreshing = false;
      });
  }

  restore_filters();

  setTimeout(() => {
    const filters = get_filters();

    if (has_required_filters(filters)) {
      load_and_render(false);
    } else {
      $status.text("Select From Date and To Date to load the dashboard.");
    }
  }, 0);

  frappe.pages["weekly-availability-"].on_page_unload = function () {
    if (_auto_load_timer) {
      clearTimeout(_auto_load_timer);
      _auto_load_timer = null;
    }

    _refreshing = false;
  };
}