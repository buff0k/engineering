"""Shared calculations for the ADT tyre management reports.

Tyre placement is taken from each survey row. History is matched only by the
physical tyre serial number, so a tyre may move between ADTs and positions.
"""

from collections import defaultdict
from datetime import timedelta

import frappe
from frappe.utils import flt, getdate


SCRAP_LIMIT_MM = 14.0
MONTH_DAYS = 30.4375


def _average_rtd(row):
    readings = [
        flt(row.get("rtd_1")),
        flt(row.get("rtd_2")),
    ]
    readings = [reading for reading in readings if reading > 0]
    return round(sum(readings) / len(readings), 2) if readings else 0.0


def _pressure_variance(row):
    recommended = flt(row.get("recommended_pressure"))
    actual = flt(row.get("actual_pressure"))

    if not recommended:
        return 0.0

    return round(((actual - recommended) / recommended) * 100, 1)


def _has_damage(row):
    category = str(row.get("damage_category") or "").strip().lower()
    notes = str(row.get("condition_notes") or "").strip().lower()
    keywords = (
        "sidewall",
        "damage",
        "cut",
        "puncture",
        "separation",
        "bead",
        "impact",
    )

    if category and category not in {"none", "no damage", "normal"}:
        return 1

    return int(any(keyword in notes for keyword in keywords))


def _action_required(row):
    action = str(row.get("required_action") or "").strip().lower()
    return int(bool(action) and action not in {"none", "no action required"})


def _raw_readings(as_on_date=None, include_mock=True):
    survey_meta = frappe.get_meta("Tyre Survey")
    tyres_field = survey_meta.get_field("tyres")

    if not tyres_field or not tyres_field.options:
        frappe.throw(
            "Tyre Survey does not have a configured tyres child table."
        )

    child_doctype = tyres_field.options
    item_meta = frappe.get_meta(child_doctype)
    child_table = "tab{0}".format(child_doctype.replace("`", "``"))
    optional_fields = []

    if item_meta.has_field("damage_category"):
        optional_fields.append("tsi.damage_category")
    else:
        optional_fields.append("NULL AS damage_category")

    if item_meta.has_field("repair_count"):
        optional_fields.append("tsi.repair_count")
    else:
        optional_fields.append("0 AS repair_count")

    conditions = [
        "tsi.parenttype = 'Tyre Survey'",
        "COALESCE(ts.docstatus, 0) < 2",
        "COALESCE(TRIM(tsi.serial_number), '') != ''",
        "UPPER(TRIM(tsi.serial_number)) NOT IN "
        "('NSN', 'DEFACED', 'N/A', 'NA', 'UNKNOWN', 'NO SERIAL')",
    ]
    values = {}

    if as_on_date:
        conditions.append("ts.survey_date <= %(as_on_date)s")
        values["as_on_date"] = getdate(as_on_date)

    return frappe.db.sql(
        """
        SELECT
            tsi.name AS survey_item,
            tsi.parent AS survey,
            ts.survey_date,
            ts.site,
            ts.fleet_number,
            ts.supplier,
            tsi.position,
            UPPER(TRIM(tsi.serial_number)) AS serial_number,
            tsi.tyre_make,
            tsi.brand_number,
            tsi.tyre_size,
            tsi.tread_pattern,
            tsi.star_ply_rating,
            tsi.tra_code,
            tsi.compound_code,
            tsi.overall_diameter,
            tsi.otd,
            tsi.rtd_1,
            tsi.rtd_2,
            tsi.rtd_percent,
            tsi.recommended_pressure,
            tsi.actual_pressure,
            tsi.pressure_variance,
            tsi.condition_notes,
            tsi.required_action,
            {optional_fields}
        FROM `{child_table}` tsi
        INNER JOIN `tabTyre Survey` ts
            ON ts.name = tsi.parent
        WHERE {conditions}
        ORDER BY
            UPPER(TRIM(tsi.serial_number)),
            ts.survey_date DESC,
            ts.modified DESC,
            tsi.idx ASC
        """.format(
            optional_fields=",\n            ".join(optional_fields),
            child_table=child_table,
            conditions=" AND\n            ".join(conditions),
        ),
        values,
        as_dict=True,
    )


def get_latest_analytics(as_on_date=None, include_mock=True):
    """Return the latest condition and previous-survey trend per serial."""

    history = defaultdict(list)

    for row in _raw_readings(as_on_date, include_mock):
        history[row.serial_number].append(row)

    analytics = []

    for serial_number, rows in history.items():
        current = rows[0]
        current_date = getdate(current.survey_date)
        previous = next(
            (
                row
                for row in rows[1:]
                if getdate(row.survey_date) < current_date
            ),
            None,
        )

        average_rtd = _average_rtd(current)
        otd = flt(current.otd)
        rtd_percent = round((average_rtd / otd) * 100, 1) if otd else 0.0
        previous_rtd = _average_rtd(previous) if previous else 0.0
        interval_months = 0.0
        wear_rate = 0.0

        if previous:
            previous_date = getdate(previous.survey_date)
            interval_days = max((current_date - previous_date).days, 1)
            interval_months = interval_days / MONTH_DAYS
            wear_rate = max(
                0.0,
                (previous_rtd - average_rtd) / interval_months,
            )

        remaining_months = None
        replacement_date = None

        if average_rtd <= SCRAP_LIMIT_MM:
            remaining_months = 0.0
            replacement_date = current_date
        elif wear_rate > 0:
            remaining_months = max(
                0.0,
                (average_rtd - SCRAP_LIMIT_MM) / wear_rate,
            )
            replacement_date = current_date + timedelta(
                days=round(remaining_months * MONTH_DAYS)
            )

        pressure_variance = _pressure_variance(current)

        analytics.append(
            frappe._dict(
                current,
                average_rtd=average_rtd,
                rtd_percent=rtd_percent,
                previous_rtd=previous_rtd,
                interval_months=round(interval_months, 2),
                wear_rate=round(wear_rate, 2),
                remaining_months=(
                    round(remaining_months, 1)
                    if remaining_months is not None
                    else None
                ),
                replacement_date=replacement_date,
                pressure_variance=pressure_variance,
                pressure_compliant=int(abs(pressure_variance) <= 10),
                low_tread=int(rtd_percent < 25),
                damage_incident=_has_damage(current),
                action_required=_action_required(current),
            )
        )

    valid_wear_rates = [row.wear_rate for row in analytics if row.wear_rate > 0]
    fleet_average_wear = (
        sum(valid_wear_rates) / len(valid_wear_rates)
        if valid_wear_rates
        else 0.0
    )

    for row in analytics:
        score = 0

        if row.rtd_percent < 25:
            score += 50

        if row.pressure_variance < -10:
            score += 20

        if fleet_average_wear and row.wear_rate > fleet_average_wear:
            score += 15

        notes = str(row.condition_notes or "").lower()
        category = str(row.damage_category or "").lower()

        if "sidewall" in notes or "sidewall" in category:
            score += 30

        if flt(row.repair_count) >= 2:
            score += 15

        row.urgency_score = score
        row.urgency_band = urgency_band(score)
        row.fleet_average_wear = round(fleet_average_wear, 2)

    return analytics


def urgency_band(score):
    score = flt(score)

    if score >= 100:
        return "Critical"
    if score >= 80:
        return "Warning"
    if score >= 60:
        return "Check"
    if score >= 40:
        return "Good"
    return "Normal"


def apply_common_filters(rows, filters=None):
    filters = frappe._dict(filters or {})
    output = []

    for row in rows:
        if filters.get("site") and row.site != filters.site:
            continue
        if filters.get("fleet_number") and row.fleet_number != filters.fleet_number:
            continue
        if filters.get("tyre_make") and row.tyre_make != filters.tyre_make:
            continue
        if filters.get("urgency_band") and row.urgency_band != filters.urgency_band:
            continue
        output.append(row)

    return output


def include_mock_value(filters):
    value = (filters or {}).get("include_mock", 1)

    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no"}

    return bool(value)
