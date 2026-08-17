import json
from collections import defaultdict
from datetime import timedelta

import frappe
from frappe.utils import (
    add_days,
    flt,
    get_datetime,
    getdate,
)


ALLOWED_ASSET_CATEGORIES = {
    "ADT",
    "Dozer",
    "Excavator",
    "Drills",
    "Water Bowser",
    "Diesel Bowsers",
    "Grader",
    "Service Truck",
    "TLB",
    "Loader",
}


def execute(filters=None):
    filters = frappe._dict(filters or {})

    validate_filters(filters)

    return (
        get_columns(),
        get_data(filters),
    )


def validate_filters(filters):
    if not filters.get("from_date"):
        frappe.throw("From Date is required.")

    if not filters.get("to_date"):
        frappe.throw("To Date is required.")

    if getdate(filters.from_date) > getdate(filters.to_date):
        frappe.throw(
            "From Date cannot be after To Date."
        )


def get_columns():
    return [
        {
            "label": "Asset Category",
            "fieldname": "asset_category",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": "Shift Date",
            "fieldname": "shift_date",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": "Asset Name",
            "fieldname": "asset_name",
            "fieldtype": "Data",
            "width": 115,
        },
        {
            "label": "Shift",
            "fieldname": "shift",
            "fieldtype": "Data",
            "width": 85,
        },
        {
            "label": "Invalid Pre-Use",
            "fieldname": "invalid_pre_use_status",
            "fieldtype": "Data",
            "width": 135,
        },
        {
            "label": "Location",
            "fieldname": "location",
            "fieldtype": "Link",
            "options": "Location",
            "width": 120,
        },
        {
            "label": "Company",
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 150,
        },
        {
            "label": "Actual Hours",
            "fieldname": "actual_hours",
            "fieldtype": "Float",
            "precision": 3,
            "width": 110,
        },
        {
            "label": "Planned Downtime",
            "fieldname": "planned_downtime",
            "fieldtype": "Float",
            "precision": 3,
            "width": 135,
        },
        {
            "label": "Req Hrs",
            "fieldname": "required_hours",
            "fieldtype": "Float",
            "precision": 3,
            "width": 90,
        },
        {
            "label": "Work Hrs",
            "fieldname": "work_hours",
            "fieldtype": "Float",
            "precision": 3,
            "width": 90,
        },
        {
            "label": "PBM Elapsed Time",
            "fieldname": "pbm_elapsed_time",
            "fieldtype": "Float",
            "precision": 3,
            "width": 145,
        },
        {
            "label": "PBM Start-up + Fatigue",
            "fieldname": "pbm_startup_fatigue_time",
            "fieldtype": "Float",
            "precision": 3,
            "width": 190,
        },
        {
            "label": "PBM Sunday Time",
            "fieldname": "pbm_sunday_time",
            "fieldtype": "Float",
            "precision": 3,
            "width": 150,
        },
        {
            "label": "PBM Total Downtime",
            "fieldname": "pbm_total_downtime",
            "fieldtype": "Float",
            "precision": 3,
            "width": 165,
        },
        {
            "label": "Utilisation Available Hours",
            "fieldname": "utilisation_available_hours",
            "fieldtype": "Float",
            "precision": 3,
            "width": 175,
        },
        {
            "label": "Availability Available Hours",
            "fieldname": "availability_available_hours",
            "fieldtype": "Float",
            "precision": 3,
            "width": 205,
        },
        {
            "label": "Availability %",
            "fieldname": "availability_percentage",
            "fieldtype": "Percent",
            "precision": 2,
            "width": 125,
        },
        # OLD UTILISATION SUPPORT COLUMNS
        # {
        #     "label": "Utilisation Work Hrs",
        #     "fieldname": "utilisation_work_hours",
        #     "fieldtype": "Float",
        #     "precision": 3,
        #     "width": 160,
        # },
        # {
        #     "label": "Utilisation Available Hrs",
        #     "fieldname": "utilisation_available_hours",
        #     "fieldtype": "Float",
        #     "precision": 3,
        #     "width": 180,
        # },
        {
            "label": "Utilisation %",
            "fieldname": "utilisation_percentage",
            "fieldtype": "Percent",
            "precision": 2,
            "width": 125,
        },
    ]


def get_data(filters):
    locations = parse_multiselect(
        filters.get("locations")
    )

    selected_assets = parse_multiselect(
        filters.get("assets")
    )

    companies = parse_multiselect(
        filters.get("companies")
    )

    free_hours = max(
        flt(filters.get("free_hours")),
        0,
    )

    planning_rows = get_planning_rows(
        filters.from_date,
        filters.to_date,
        locations,
    )

    if not planning_rows:
        return []

    planning_map = build_planning_map(
        planning_rows
    )

    assets = get_assets(
        planning_rows,
        selected_assets,
        companies,
    )

    if not assets:
        return []

    spare_assets = get_spare_swing_assets(
        filters.from_date,
        filters.to_date,
        locations,
    )

    if filters.get("production_machines_only"):
        assets = [
            asset
            for asset in assets
            if asset.name not in spare_assets
            and asset.asset_name not in spare_assets
        ]

    if not assets:
        return []

    preuse_map = get_preuse_map(
        filters.from_date,
        filters.to_date,
        locations,
    )

    pbm_map = get_pbm_map(
        filters.from_date,
        filters.to_date,
        assets,
        locations,
    )

    assets_by_location = defaultdict(list)

    for asset in assets:
        assets_by_location[
            asset.location
        ].append(asset)

    shift_rows = []

    current_date = getdate(
        filters.from_date
    )

    end_date = getdate(
        filters.to_date
    )

    while current_date <= end_date:
        date_text = str(current_date)

        for location, location_assets in assets_by_location.items():
            planning = planning_map.get(
                (
                    location,
                    date_text,
                )
            )

            if not planning:
                continue

            shifts = get_shifts(
                planning.get("shift_system")
            )

            for asset in location_assets:
                for shift in shifts:
                    shift_pbm = pbm_map.get(
                        (
                            asset.asset_name,
                            date_text,
                            location,
                            shift,
                        ),
                        {},
                    )

                    required_hours = get_required_hours(
                        planning,
                        shift,
                    )

                    preuse = preuse_map.get(
                        (
                            location,
                            date_text,
                            shift,
                            asset.asset_name,
                        )
                    )

                    work_hours = 0.0
                    pre_use_status = ""

                    if preuse:
                        pre_use_status = str(
                            preuse.get(
                                "pre_use_avail_status"
                            )
                            or ""
                        )

                        if pre_use_status in ("3", "6"):
                            required_hours = 0.0

                        start_hours = preuse.get(
                            "eng_hrs_start"
                        )

                        end_hours = preuse.get(
                            "eng_hrs_end"
                        )

                        if (
                            start_hours is not None
                            and end_hours is not None
                        ):
                            work_hours = max(
                                flt(end_hours)
                                - flt(start_hours),
                                0,
                            )

                    shift_rows.append({
                        "asset_category": (
                            asset.asset_category
                        ),
                        "shift_date": current_date,
                        "asset_name": asset.asset_name,
                        "shift": shift,
                        "location": location,
                        "company": asset.company,
                        "shift_limit_hours": (
                            12.0
                            if str(
                                planning.get("shift_system")
                                or ""
                            ).strip().lower() == "2x12hour"
                            else 8.0
                        ),
                        "is_spare_swing_unit": (
                            1
                            if (
                                asset.name in spare_assets
                                or asset.asset_name in spare_assets
                            )
                            else 0
                        ),
                        "spare_swing_reason": (
                            "Spare/Swing unit in Monthly Production Planning"
                        ),
                        "actual_hours": (
                            get_shift_actual_hours(
                                planning,
                                shift,
                            )
                        ),
                        "planned_downtime": (
                            get_shift_planned_downtime(
                                location,
                                current_date,
                                shift,
                            )
                        ),
                        "required_hours": max(
                            flt(required_hours),
                            0,
                        ),
                        "work_hours": work_hours,
                        "pre_use_avail_status": (
                            pre_use_status
                        ),
                        "pbm_elapsed_time": flt(
                            shift_pbm.get(
                                "pbm_elapsed_time"
                            )
                        ),
                        "pbm_startup_fatigue_time": flt(
                            shift_pbm.get(
                                "pbm_startup_fatigue_time"
                            )
                        ),
                        "pbm_sunday_time": flt(
                            shift_pbm.get(
                                "pbm_sunday_time"
                            )
                        ),
                        "pbm_total_downtime": flt(
                            shift_pbm.get(
                                "pbm_total_downtime"
                            )
                        ),
                        "indent": 3,
                    })


        current_date = add_days(
            current_date,
            1,
        )

    mark_invalid_preuse_rows(
        shift_rows
    )

    for row in shift_rows:
        row["required_hours"] = max(
            flt(row.get("required_hours"))
            - (
                free_hours
                / max(
                    len(
                        get_shifts_for_row(
                            row,
                            planning_map,
                        )
                    ),
                    1,
                )
            ),
            0,
        )

        row["pbm_total_downtime"] = max(
            flt(
                row.get(
                    "pbm_total_downtime"
                )
            ),
            0,
        )

        calculate_availability_values(row)
        validate_au_row(row)
        round_engine_row(row)

    data = build_tree_rows(
        shift_rows
    )

    apply_au_percentage_basis(
        data,
        filters.get(
            "au_percentage_basis"
        ),
    )

    return data

def apply_au_percentage_basis(
    rows,
    percentage_basis,
):
    multiplier = (
        1.0
        if percentage_basis == "100% A & U"
        else 0.85
    )

    for row in rows:
        for fieldname in (
            "availability_percentage",
            "utilisation_percentage",
        ):
            value = row.get(fieldname)

            if value is None:
                continue

            row[fieldname] = round(
                flt(value) * multiplier,
                3,
            )

    return rows



def get_shifts_for_row(
    row,
    planning_map,
):
    planning = planning_map.get(
        (
            row.get("location"),
            str(row.get("shift_date")),
        ),
        {},
    )

    return get_shifts(
        planning.get("shift_system")
    )


def mark_invalid_preuse_rows(rows):
    daily_hours = defaultdict(float)

    for row in rows:
        key = (
            row.get("asset_category"),
            str(row.get("shift_date")),
            row.get("location"),
            row.get("asset_name"),
        )

        daily_hours[key] += flt(
            row.get("work_hours")
        )

    for row in rows:
        key = (
            row.get("asset_category"),
            str(row.get("shift_date")),
            row.get("location"),
            row.get("asset_name"),
        )

        shift_invalid = (
            flt(
                row.get("work_hours")
            ) > 12
        )

        daily_invalid = (
            flt(
                daily_hours.get(key)
            ) > 24
        )

        row["invalid_pre_use"] = (
            1
            if shift_invalid or daily_invalid
            else 0
        )

        if shift_invalid:
            row["invalid_pre_use_status"] = (
                "Invalid: Shift > 12h"
            )
        elif daily_invalid:
            row["invalid_pre_use_status"] = (
                "Invalid: Day > 24h"
            )
        else:
            row["invalid_pre_use_status"] = "Valid"




def calculate_availability_values(row):
    required_hours = max(
        flt(
            row.get("required_hours")
        ),
        0,
    )

    work_hours = max(
        flt(
            row.get("work_hours")
        ),
        0,
    )

    pbm_total_downtime = max(
        flt(
            row.get("pbm_total_downtime")
        ),
        0,
    )


    # OLD AVAILABLE HOURS CALCULATION
    # if work_hours > 0:
    #     uncapped_available_hours = max(
    #         work_hours
    #         - pbm_total_downtime,
    #         0,
    #     )
    #
    #     if uncapped_available_hours <= 0:
    #         uncapped_available_hours = min(
    #             work_hours,
    #             required_hours,
    #         )
    # else:
    #     uncapped_available_hours = max(
    #         required_hours
    #         - pbm_total_downtime,
    #         0,
    #     )
    #
    # utilisation_available_hours = min(
    #     uncapped_available_hours,
    #     required_hours,
    # )

    remaining_required_hours = max(
        required_hours - pbm_total_downtime,
        0,
    )

    utilisation_available_hours = max(
        remaining_required_hours,
        min(
            work_hours,
            required_hours,
        ),
    )

    availability_available_hours = max(
        work_hours,
        max(
            required_hours - pbm_total_downtime,
            0,
        ),
    )

    availability_percentage = (
        (
            availability_available_hours
            / required_hours
        )
        * 100
        if required_hours > 0
        else None
    )

    # OLD UTILISATION CALCULATION
    # if required_hours > 0:
    #     if work_hours >= required_hours:
    #         utilisation_available_hours = required_hours
    #     else:
    #         utilisation_available_hours = max(
    #             required_hours
    #             - pbm_total_downtime,
    #             0,
    #         )
    # else:
    #     utilisation_available_hours = 0.0
    #
    # utilisation_work_hours = (
    #     work_hours
    #     if utilisation_available_hours > 0
    #     else 0.0
    # )
    #
    # utilisation_percentage = (
    #     (
    #         utilisation_work_hours
    #         / utilisation_available_hours
    #     )
    #     * 100
    #     if utilisation_available_hours > 0
    #     else None
    # )
    #
    # row["utilisation_work_hours"] = (
    #     utilisation_work_hours
    # )
    #
    # row["utilisation_available_hours"] = (
    #     utilisation_available_hours
    # )

    utilisation_percentage = (
        (
            work_hours
            / utilisation_available_hours
        )
        * 100
        if (
            required_hours > 0
            and utilisation_available_hours > 0
        )
        else 0.0
    )

    row["utilisation_available_hours"] = (
        utilisation_available_hours
    )

    row["availability_available_hours"] = (
        availability_available_hours
    )

    row["availability_percentage"] = (
        availability_percentage
    )

    row["utilisation_percentage"] = (
        utilisation_percentage
    )

def validate_au_row(row):
    shift_limit_hours = max(
        flt(row.get("shift_limit_hours")),
        0,
    )

    required_hours = max(
        flt(row.get("required_hours")),
        0,
    )

    work_hours = max(
        flt(row.get("work_hours")),
        0,
    )

    pbm_total_downtime = max(
        flt(row.get("pbm_total_downtime")),
        0,
    )

    # OLD UTILISATION AVAILABLE HOURS VALIDATION
    # utilisation_available_hours = max(
    #     flt(
    #         row.get(
    #             "utilisation_available_hours"
    #         )
    #     ),
    #     0,
    # )

    utilisation_percentage = row.get(
        "utilisation_percentage"
    )

    invalid_reasons = []
    warning_reasons = []

    if work_hours > shift_limit_hours:
        invalid_reasons.append(
            f"Work {work_hours:g}h exceeds "
            f"{shift_limit_hours:g}h shift"
        )

    if pbm_total_downtime > shift_limit_hours:
        invalid_reasons.append(
            f"PBM {pbm_total_downtime:g}h exceeds "
            f"{shift_limit_hours:g}h shift"
        )

    if (
        work_hours
        + pbm_total_downtime
        > shift_limit_hours
    ):
        invalid_reasons.append(
            f"Work + PBM = "
            f"{work_hours + pbm_total_downtime:g}h "
            f"exceeds {shift_limit_hours:g}h shift"
        )

    if required_hours > shift_limit_hours:
        invalid_reasons.append(
            f"Required {required_hours:g}h exceeds "
            f"{shift_limit_hours:g}h shift"
        )

    # OLD UTILISATION AVAILABLE HOURS VALIDATION
    # if (
    #     utilisation_available_hours
    #     > shift_limit_hours
    # ):
    #     invalid_reasons.append(
    #         f"Utilisation Available "
    #         f"{utilisation_available_hours:g}h exceeds "
    #         f"{shift_limit_hours:g}h shift"
    #     )
    #
    # if (
    #     work_hours > 0
    #     and utilisation_available_hours <= 0
    # ):
    #     warning_reasons.append(
    #         "Machine worked but Utilisation "
    #         "Available Hours is 0"
    #     )

    if (
        required_hours <= 0
        and work_hours > 0
    ):
        warning_reasons.append(
            "Machine worked while Required Hours is 0"
        )

    if (
        utilisation_percentage is not None
        and flt(utilisation_percentage) > 150
    ):
        warning_reasons.append(
            f"Utilisation is "
            f"{flt(utilisation_percentage):.2f}%"
        )

    if invalid_reasons:
        row["invalid_au"] = 1
        row["au_validation_level"] = "invalid"
        row["au_validation_status"] = (
            "Invalid A&U: "
            + "; ".join(invalid_reasons)
        )
        row["utilisation_percentage"] = None
    elif warning_reasons:
        row["invalid_au"] = 0
        row["au_validation_level"] = "warning"
        row["au_validation_status"] = (
            "A&U Warning: "
            + "; ".join(warning_reasons)
        )
    else:
        row["invalid_au"] = 0
        row["au_validation_level"] = "valid"
        row["au_validation_status"] = "Valid"


def round_engine_row(row):
    percentage_fields = {
        "availability_percentage",
        "utilisation_percentage",
    }


    for fieldname in (
        "planned_downtime",
        "required_hours",
        "work_hours",
        "pbm_elapsed_time",
        "pbm_startup_fatigue_time",
        "pbm_sunday_time",
        "pbm_total_downtime",
        "utilisation_available_hours",
        "availability_available_hours",
        # OLD UTILISATION SUPPORT FIELDS
        # "utilisation_work_hours",
        # "utilisation_available_hours",
        "availability_percentage",
        "utilisation_percentage",
    ):
        if (
            fieldname in percentage_fields
            and row.get(fieldname) is None
        ):
            continue

        row[fieldname] = round(
            flt(
                row.get(fieldname)
            ),
            3,
        )


def get_valid_rows(rows):
    return [
        row
        for row in rows
        if not row.get(
            "invalid_pre_use"
        )
        and not row.get(
            "invalid_au"
        )
    ]


def build_summary_row(
    rows,
    indent,
    **identity_fields,
):

    valid_rows = get_valid_rows(
        rows
    )

    # PBM represents actual breakdown downtime and must not disappear
    # merely because an A&U validation rule flags the shift.
    # We still exclude invalid Pre-Use rows, but retain PBM from
    # invalid_au rows so Mechanical Downtime matches breakdown detail.
    pbm_rows = [
        row
        for row in rows
        if not row.get("invalid_pre_use")
    ]

    problem_dates = {
        str(row.get("shift_date"))
        for row in rows
        if row.get("shift_date")
        and row.get("au_validation_level")
        in ("warning", "invalid")
    }

    problem_day_count = len(
        problem_dates
    )

    invalid_au_rows = [
        row
        for row in rows
        if row.get("au_validation_level")
        == "invalid"
    ]

    warning_au_rows = [
        row
        for row in rows
        if row.get("au_validation_level")
        == "warning"
    ]

    if invalid_au_rows:
        au_validation_level = "invalid"
        au_validation_status = (
            f"{len(invalid_au_rows)} invalid A&U "
            f"shift(s)"
        )
    elif warning_au_rows:
        au_validation_level = "warning"
        au_validation_status = (
            f"{len(warning_au_rows)} A&U warning "
            f"shift(s)"
        )
    else:
        au_validation_level = "valid"
        au_validation_status = "Valid"

    # OLD UTILISATION ROW FILTER
    # utilisation_rows = [
    #     row
    #     for row in valid_rows
    #     if flt(
    #         row.get("utilisation_available_hours")
    #     ) > 0
    # ]

    summary = {
        **identity_fields,
        "indent": indent,
        "au_problem_day_count": problem_day_count,
        "au_validation_level": au_validation_level,
        "au_validation_status": au_validation_status,
        "invalid_pre_use_status": (
            ""
            if valid_rows
            else "No valid Pre-Use"
        ),
    }

    summary["actual_hours"] = sum(
        flt(row.get("actual_hours"))
        for row in rows
    )


    # KPI fields continue to use fully valid A&U rows.
    for fieldname in (
        "planned_downtime",
        "required_hours",
        "work_hours",
        "utilisation_available_hours",
        "availability_available_hours",
    ):
        summary[fieldname] = sum(
            flt(
                row.get(fieldname)
            )
            for row in valid_rows
        )

    # PBM is physical downtime. Keep it even when the shift has an
    # A&U validation error, otherwise Breakdown Detail and Month End
    # Mechanical Downtime no longer reconcile.
    #
    # PBM is reported in whole minutes by the canonical Breakdown
    # helper. Convert each shift value back to whole minutes before
    # summing so decimal-hour display rounding cannot accumulate over
    # the month.
    for fieldname in (
        "pbm_elapsed_time",
        "pbm_startup_fatigue_time",
        "pbm_sunday_time",
        "pbm_total_downtime",
    ):
        summary_minutes = sum(
            int(
                round(
                    flt(
                        row.get(
                            fieldname
                        )
                    )
                    * 60
                )
            )
            for row in pbm_rows
        )

        summary[fieldname] = (
            summary_minutes
            / 60
        )

    summary["availability_percentage"] = (
        (
            summary["availability_available_hours"]
            / summary["required_hours"]
        )
        * 100
        if summary["required_hours"] > 0
        else None
    )

    # OLD TOTAL UTILISATION CALCULATION
    # utilisation_work_hours = summary[
    #     "utilisation_work_hours"
    # ]
    #
    # utilisation_available_hours = summary[
    #     "utilisation_available_hours"
    # ]
    #
    # summary["utilisation_percentage"] = (
    #     (
    #         utilisation_work_hours
    #         / utilisation_available_hours
    #     )
    #     * 100
    #     if utilisation_available_hours > 0
    #     else None
    # )

    summary["utilisation_percentage"] = (
        (
            summary["work_hours"]
            / summary["utilisation_available_hours"]
        )
        * 100
        if summary["utilisation_available_hours"] > 0
        else None
    )

    round_engine_row(
        summary
    )

    return summary


def build_tree_rows(shift_rows):
    grouped = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(list)
        )
    )

    for row in shift_rows:
        grouped[
            row.get("asset_category")
        ][
            str(row.get("shift_date"))
        ][
            row.get("asset_name")
        ].append(row)

    data = []

    priority_categories = {
        "ADT": 0,
        "Dozer": 1,
        "Excavator": 2,
    }

    sorted_categories = sorted(
        grouped,
        key=lambda category: (
            priority_categories.get(category, 999),
            category or "",
        ),
    )

    for category in sorted_categories:
        category_rows = [
            shift_row
            for date_assets in grouped[
                category
            ].values()
            for machine_rows in date_assets.values()
            for shift_row in machine_rows
        ]

        data.append(
            build_summary_row(
                category_rows,
                indent=0,
                asset_category=category,
            )
        )

        for shift_date in sorted(
            grouped[category]
        ):
            machines = grouped[
                category
            ][shift_date]

            date_rows = [
                shift_row
                for machine_rows in machines.values()
                for shift_row in machine_rows
            ]

            first_date_row = (
                date_rows[0]
                if date_rows
                else {}
            )

            data.append(
                build_summary_row(
                    date_rows,
                    indent=1,
                    asset_category=category,
                    shift_date=shift_date,
                    location=first_date_row.get(
                        "location"
                    ),
                )
            )

            for asset_name in sorted(
                machines
            ):
                machine_rows = machines[
                    asset_name
                ]

                first_machine_row = (
                    machine_rows[0]
                )

                machine_invalid = any(
                    row.get(
                        "invalid_pre_use"
                    )
                    for row in machine_rows
                )

                machine_summary = build_summary_row(
                    machine_rows,
                    indent=2,
                    asset_category=category,
                    shift_date=shift_date,
                    asset_name=asset_name,
                    location=(
                        first_machine_row.get(
                            "location"
                        )
                    ),
                    company=(
                        first_machine_row.get(
                            "company"
                        )
                    ),
                    is_spare_swing_unit=(
                        first_machine_row.get(
                            "is_spare_swing_unit"
                        )
                    ),
                    spare_swing_reason=(
                        first_machine_row.get(
                            "spare_swing_reason"
                        )
                    ),
                )

                if machine_invalid:
                    machine_summary[
                        "invalid_pre_use_status"
                    ] = "Contains Invalid Shift"

                data.append(
                    machine_summary
                )

                for shift_row in sorted(
                    machine_rows,
                    key=lambda row: (
                        row.get("shift") or ""
                    ),
                ):
                    data.append(
                        shift_row
                    )

    return data


def get_shift_actual_hours(
    planning,
    shift,
):
    shift_system = str(
        planning.get("shift_system")
        or ""
    ).strip().lower()

    return (
        12.0
        if shift_system == "2x12hour"
        else 8.0
    )


def get_shift_planned_downtime(
    location,
    shift_date,
    shift,
):
    day_of_week = getdate(
        shift_date
    ).weekday()

    if day_of_week == 5:
        day_type = "Saturday"
    elif day_of_week == 6:
        day_type = "Sunday"
    else:
        day_type = "Weekday"

    configuration = frappe.db.get_value(
        "Startup and Fatigue spesification",
        {
            "site": location,
            "shift": shift,
            "day_type": day_type,
        },
        [
            "startup_start",
            "startup_end",
            "fatigue_start",
            "fatigue_end",
        ],
        as_dict=True,
    )

    if not configuration:
        frappe.log_error(
            title="Missing Startup and Fatigue specification",
            message=(
                f"No configuration found for "
                f"{location}-{shift}-{day_type}"
            ),
        )
        return 0.0

    startup_hours = get_time_window_hours(
        configuration.startup_start,
        configuration.startup_end,
    )

    fatigue_hours = get_time_window_hours(
        configuration.fatigue_start,
        configuration.fatigue_end,
    )

    return startup_hours + fatigue_hours


def get_time_window_hours(
    start_time,
    end_time,
):
    if start_time is None or end_time is None:
        return 0.0

    start_seconds = start_time.total_seconds()
    end_seconds = end_time.total_seconds()

    if end_seconds < start_seconds:
        end_seconds += 24 * 60 * 60

    return (
        end_seconds - start_seconds
    ) / 3600


def parse_multiselect(value):
    if not value:
        return []

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    value_text = str(value).strip()

    if not value_text:
        return []

    try:
        parsed = json.loads(
            value_text
        )

        if isinstance(parsed, list):
            return [
                str(item).strip()
                for item in parsed
                if str(item).strip()
            ]
    except Exception:
        pass

    return [
        item.strip()
        for item in value_text.split(",")
        if item.strip()
    ]


def get_planning_rows(
    from_date,
    to_date,
    locations,
):
    conditions = [
        "mpp.docstatus < 2",
        "mpp.site_status = 'Producing'",
        (
            "mpp.prod_month_start_date "
            "<= %(to_date)s"
        ),
        (
            "mpp.prod_month_end_date "
            ">= %(from_date)s"
        ),
    ]

    values = {
        "from_date": from_date,
        "to_date": to_date,
    }

    if locations:
        conditions.append(
            "mpp.location IN %(locations)s"
        )

        values["locations"] = tuple(
            locations
        )

    return frappe.db.sql(
        f"""
        SELECT
            mpp.name,
            mpp.location,
            mpp.shift_system,
            mpp.prod_month_start_date,
            mpp.prod_month_end_date
        FROM `tabMonthly Production Planning` mpp
        WHERE {" AND ".join(conditions)}
        ORDER BY
            mpp.location,
            mpp.prod_month_start_date
        """,
        values,
        as_dict=True,
    )


def build_planning_map(planning_rows):
    planning_map = {}

    for planning_row in planning_rows:
        planning_doc = frappe.get_doc(
            "Monthly Production Planning",
            planning_row.name,
        )

        for day in planning_doc.month_prod_days:
            shift_date = getdate(
                day.shift_start_date
            )

            planning_map[
                (
                    planning_row.location,
                    str(shift_date),
                )
            ] = {
                "shift_system": (
                    planning_row.shift_system
                ),
                "shift_day_hours": flt(
                    day.shift_day_hours
                ),
                "shift_night_hours": flt(
                    day.shift_night_hours
                ),
                "shift_morning_hours": flt(
                    day.shift_morning_hours
                ),
                "shift_afternoon_hours": flt(
                    day.shift_afternoon_hours
                ),
            }

    return planning_map


def get_assets(
    planning_rows,
    selected_assets,
    companies,
):
    locations = sorted({
        row.location
        for row in planning_rows
        if row.location
    })

    conditions = [
        "asset.docstatus = 1",
        "asset.location IN %(locations)s",
        "IFNULL(asset.asset_name, '') != ''",
        "asset.asset_category IN %(allowed_categories)s",
    ]

    values = {
        "locations": tuple(locations),
        "allowed_categories": tuple(
            sorted(
                ALLOWED_ASSET_CATEGORIES
            )
        ),
    }

    if selected_assets:
        conditions.append(
            """
            (
                asset.name IN %(assets)s
                OR asset.asset_name IN %(assets)s
            )
            """
        )

        values["assets"] = tuple(
            selected_assets
        )

    if companies:
        conditions.append(
            "asset.company IN %(companies)s"
        )

        values["companies"] = tuple(
            companies
        )

    assets = frappe.db.sql(
        f"""
        SELECT
            asset.name,
            asset.asset_name,
            asset.asset_category,
            asset.location,
            asset.company
        FROM `tabAsset` asset
        WHERE {" AND ".join(conditions)}
        ORDER BY
            asset.asset_category,
            asset.asset_name
        """,
        values,
        as_dict=True,
    )

    return assets


def get_preuse_map(
    from_date,
    to_date,
    locations,
):
    conditions = [
        (
            "puh.shift_date BETWEEN "
            "%(from_date)s AND %(to_date)s"
        ),
        "puh.docstatus < 2",
    ]

    values = {
        "from_date": from_date,
        "to_date": to_date,
    }

    if locations:
        conditions.append(
            "puh.location IN %(locations)s"
        )

        values["locations"] = tuple(
            locations
        )

    rows = frappe.db.sql(
        f"""
        SELECT
            puh.name,
            puh.location,
            puh.shift_date,
            puh.shift
        FROM `tabPre-Use Hours` puh
        WHERE {" AND ".join(conditions)}
        """,
        values,
        as_dict=True,
    )

    preuse_map = {}

    for row in rows:
        doc = frappe.get_doc(
            "Pre-Use Hours",
            row.name,
        )

        for asset_row in doc.pre_use_assets:
            plant_no = get_preuse_plant_no(
                asset_row
            )

            if not plant_no:
                continue

            preuse_map[
                (
                    row.location,
                    str(row.shift_date),
                    row.shift,
                    plant_no,
                )
            ] = {
                "eng_hrs_start": (
                    asset_row.eng_hrs_start
                ),
                "eng_hrs_end": (
                    asset_row.eng_hrs_end
                ),
                "pre_use_avail_status": getattr(
                    asset_row,
                    "pre_use_avail_status",
                    None,
                ),
            }

    return preuse_map


def get_preuse_plant_no(asset_row):
    plant_no = getattr(
        asset_row,
        "plant_no",
        None,
    )

    if plant_no:
        return str(
            plant_no
        ).strip()

    asset_link = getattr(
        asset_row,
        "asset_name",
        None,
    )

    if not asset_link:
        return None

    return frappe.db.get_value(
        "Asset",
        asset_link,
        "asset_name",
    )


def get_shifts(shift_system):
    shift_system = (
        shift_system or ""
    ).strip().lower()

    if shift_system == "2x12hour":
        return [
            "Day",
            "Night",
        ]

    return [
        "Morning",
        "Afternoon",
        "Night",
    ]


def get_required_hours(
    planning,
    shift,
):
    field_map = {
        "Day": "shift_day_hours",
        "Night": "shift_night_hours",
        "Morning": "shift_morning_hours",
        "Afternoon": "shift_afternoon_hours",
    }

    return flt(
        planning.get(
            field_map.get(
                shift,
                "",
            ),
            0,
        )
    )




def get_spare_swing_assets(
    from_date,
    to_date,
    locations,
):
    conditions = [
        "mpp.docstatus < 2",
        (
            "mpp.prod_month_start_date "
            "<= %(to_date)s"
        ),
        (
            "mpp.prod_month_end_date "
            ">= %(from_date)s"
        ),
    ]

    values = {
        "from_date": from_date,
        "to_date": to_date,
    }

    if locations:
        conditions.append(
            "mpp.location IN %(locations)s"
        )

        values["locations"] = tuple(
            locations
        )

    condition_sql = " AND ".join(
        conditions
    )

    spare_assets = set()

    queries = [
        f"""
        SELECT DISTINCT
            etl.truck AS asset_name
        FROM `tabMonthly Production Planning` mpp
        INNER JOIN `tabExcavator Truck Link` etl
            ON etl.parent = mpp.name
            AND etl.parenttype
                = 'Monthly Production Planning'
        WHERE {condition_sql}
          AND IFNULL(etl.truck, '') != ''
          AND IFNULL(etl.excavator, '') = ''
        """,
        f"""
        SELECT DISTINCT
            etl.excavator AS asset_name
        FROM `tabMonthly Production Planning` mpp
        INNER JOIN `tabExcavator Truck Link` etl
            ON etl.parent = mpp.name
            AND etl.parenttype
                = 'Monthly Production Planning'
        WHERE {condition_sql}
          AND IFNULL(etl.excavator, '') != ''
          AND IFNULL(etl.truck, '') = ''
          AND NOT EXISTS (
              SELECT 1
              FROM `tabExcavator Truck Link` assigned
              WHERE assigned.parent = etl.parent
                AND assigned.parenttype
                    = etl.parenttype
                AND assigned.excavator
                    = etl.excavator
                AND IFNULL(assigned.truck, '') != ''
          )
        """,
        f"""
        SELECT DISTINCT
            dp.asset_name
        FROM `tabMonthly Production Planning` mpp
        INNER JOIN `tabDozers Planned` dp
            ON dp.parent = mpp.name
            AND dp.parenttype
                = 'Monthly Production Planning'
        WHERE {condition_sql}
          AND IFNULL(dp.asset_name, '') != ''
          AND IFNULL(dp.dozing_type, '') = ''
        """,
    ]

    for query in queries:
        try:
            rows = frappe.db.sql(
                query,
                values,
                as_dict=True,
            )

            for row in rows:
                if row.asset_name:
                    spare_assets.add(
                        str(
                            row.asset_name
                        ).strip()
                    )
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                (
                    "Availability Utilisation "
                    "Engine Spare Assets"
                ),
            )

            frappe.clear_messages()

    resolved_assets = set(
        spare_assets
    )

    for asset_identifier in list(
        spare_assets
    ):
        asset = frappe.db.get_value(
            "Asset",
            asset_identifier,
            [
                "name",
                "asset_name",
            ],
            as_dict=True,
        )

        if not asset:
            asset = frappe.db.get_value(
                "Asset",
                {
                    "asset_name": asset_identifier,
                },
                [
                    "name",
                    "asset_name",
                ],
                as_dict=True,
            )

        if not asset:
            continue

        if asset.name:
            resolved_assets.add(
                str(asset.name).strip()
            )

        if asset.asset_name:
            resolved_assets.add(
                str(asset.asset_name).strip()
            )

    return resolved_assets


def get_pbm_map(
    from_date,
    to_date,
    assets,
    locations,
):
    """
    Build PBM downtime values using the same Availability & Utilisation
    calculation rules, but without issuing repeated A&U SQL queries for
    every individual breakdown segment.

    Performance strategy:
    - Load all relevant A&U shift rows once.
    - Index those rows by asset/location.
    - Cache Startup/Fatigue configuration by location/shift.
    - Perform overlap calculations in memory.
    """

    from engineering.engineering.doctype.availability_and_utilisation import (
        availability_and_utilisation as au,
    )

    report_start = get_datetime(
        f"{from_date} 06:00:00"
    )

    report_end = get_datetime(
        f"{add_days(to_date, 1)} 06:00:00"
    )

    def normalise_asset_name(value):
        return str(
            value or ""
        ).strip()

    # Keep both the stored value and its trimmed equivalent in the
    # database query, while all in-memory PBM keys use the trimmed name.
    raw_asset_names = [
        str(asset.asset_name)
        for asset in assets
        if asset.asset_name
    ]

    asset_names = sorted({
        name
        for raw_name in raw_asset_names
        for name in (
            raw_name,
            normalise_asset_name(raw_name),
        )
        if name
    })

    if not asset_names:
        return {}

    # ------------------------------------------------------------------
    # Load Plant Breakdown or Maintenance rows once
    # ------------------------------------------------------------------

    conditions = [
        "IFNULL(asset_name, '') != ''",
        "IFNULL(breakdown_reason, '') != ''",
        "IFNULL(exclude_from_au, 0) = 0",
        "asset_name IN %(asset_names)s",
        (
            "breakdown_start_datetime "
            "< %(report_end)s"
        ),
        (
            "("
            "resolved_datetime >= %(report_start)s "
            "OR resolved_datetime IS NULL"
            ")"
        ),
    ]

    values = {
        "asset_names": tuple(asset_names),
        "report_start": report_start,
        "report_end": report_end,
    }

    if locations:
        conditions.append(
            "location IN %(locations)s"
        )

        values["locations"] = tuple(
            locations
        )

    rows = frappe.db.sql(
        f"""
        SELECT
            name,
            asset_name,
            location,
            breakdown_start_datetime,
            resolved_datetime
        FROM `tabPlant Breakdown or Maintenance`
        WHERE {" AND ".join(conditions)}
        ORDER BY breakdown_start_datetime
        """,
        values,
        as_dict=True,
    )

    if not rows:
        return {}

    # ------------------------------------------------------------------
    # Load all A&U shift rows needed for the complete report ONCE.
    #
    # Previously get_required_downtime_minutes_for_breakdown() executed
    # essentially this query for every PBM segment.
    # ------------------------------------------------------------------

    au_conditions = [
        "asset_name IN %(asset_names)s",
        (
            "shift_date >= "
            "DATE(%(from_date)s) - INTERVAL 1 DAY"
        ),
        (
            "shift_date <= "
            "DATE(%(to_date)s) + INTERVAL 1 DAY"
        ),
    ]

    au_values = {
        "asset_names": tuple(asset_names),
        "from_date": from_date,
        "to_date": to_date,
    }

    if locations:
        au_conditions.append(
            "location IN %(locations)s"
        )

        au_values["locations"] = tuple(
            locations
        )

    au_rows = frappe.db.sql(
        f"""
        SELECT
            name,
            shift_date,
            shift,
            shift_system,
            location,
            asset_name,
            shift_required_hours
        FROM `tabAvailability and Utilisation`
        WHERE {" AND ".join(au_conditions)}
        ORDER BY
            asset_name ASC,
            location ASC,
            shift_date ASC,
            FIELD(
                shift,
                'Day',
                'Morning',
                'Afternoon',
                'Night'
            ) ASC
        """,
        au_values,
        as_dict=True,
    )

    # ------------------------------------------------------------------
    # Index A&U rows so each breakdown only examines rows belonging to
    # the same asset and location.
    # ------------------------------------------------------------------

    au_rows_by_asset_location = {}

    for au_row in au_rows:
        au_key = (
            normalise_asset_name(
                au_row.asset_name
            ),
            au_row.location,
        )

        au_rows_by_asset_location.setdefault(
            au_key,
            [],
        ).append(au_row)

    # ------------------------------------------------------------------
    # Startup/Fatigue configuration cache.
    #
    # _exclusion_windows() previously called frappe.db.get_value()
    # repeatedly. We intentionally still use frappe.db.get_value here,
    # but only once per unique location/shift pair so record-selection
    # behaviour remains consistent.
    # ------------------------------------------------------------------

    exclusion_configuration_cache = {}

    def get_exclusion_configuration(
        location,
        shift,
        shift_date,
    ):
        day_of_week = getdate(
            shift_date
        ).weekday()

        if day_of_week == 5:
            day_type = "Saturday"
        elif day_of_week == 6:
            day_type = "Sunday"
        else:
            day_type = "Weekday"

        cache_key = (
            location,
            shift,
            day_type,
        )

        if cache_key not in exclusion_configuration_cache:
            configuration_fields = [
                "startup_start",
                "startup_end",
                "fatigue_start",
                "fatigue_end",
            ]

            # Prefer an explicit day-specific configuration.
            configuration = frappe.db.get_value(
                "Startup and Fatigue spesification",
                {
                    "site": location,
                    "shift": shift,
                    "day_type": day_type,
                },
                configuration_fields,
                as_dict=True,
            )

            # Backward compatibility:
            # if this site/shift has only one configuration,
            # use it as the generic Weekday/Saturday/Sunday rule.
            if not configuration:
                legacy_configurations = frappe.get_all(
                    "Startup and Fatigue spesification",
                    filters={
                        "site": location,
                        "shift": shift,
                    },
                    fields=configuration_fields,
                    limit=2,
                )

                if len(legacy_configurations) == 1:
                    configuration = frappe._dict(
                        legacy_configurations[0]
                    )

            exclusion_configuration_cache[
                cache_key
            ] = configuration

        return exclusion_configuration_cache[
            cache_key
        ]

    def time_text(value):
        if isinstance(value, timedelta):
            seconds = (
                int(value.total_seconds())
                % 86400
            )

            hours, remainder = divmod(
                seconds,
                3600,
            )

            minutes, seconds = divmod(
                remainder,
                60,
            )

            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{seconds:02d}"
            )

        return str(value).split(".")[0]

    def get_cached_exclusion_windows(
        location,
        shift,
        shift_start,
        shift_end,
    ):
        configuration = (
            get_exclusion_configuration(
                location,
                shift,
                shift_start,
            )
        )

        if not configuration:
            return []

        def build_windows(
            start_time,
            end_time,
        ):
            windows = []

            start_time = time_text(
                start_time
            )

            end_time = time_text(
                end_time
            )

            base_date = getdate(
                shift_start
            )

            for day_offset in (0, 1):
                window_date = add_days(
                    base_date,
                    day_offset,
                )

                window_start = get_datetime(
                    f"{window_date} {start_time}"
                )

                window_end_date = (
                    window_date
                )

                if end_time <= start_time:
                    window_end_date = add_days(
                        window_date,
                        1,
                    )

                window_end = get_datetime(
                    f"{window_end_date} {end_time}"
                )

                if (
                    window_end <= shift_start
                    or window_start >= shift_end
                ):
                    continue

                windows.append((
                    max(
                        window_start,
                        shift_start,
                    ),
                    min(
                        window_end,
                        shift_end,
                    ),
                ))

            return windows

        windows = []

        # Preserve original order:
        # startup first, fatigue second.
        windows.extend(
            build_windows(
                configuration.startup_start,
                configuration.startup_end,
            )
        )

        windows.extend(
            build_windows(
                configuration.fatigue_start,
                configuration.fatigue_end,
            )
        )

        return windows

    # ------------------------------------------------------------------
    # Same calculation as
    # get_required_downtime_minutes_for_breakdown(), but against the
    # already-loaded A&U rows.
    # ------------------------------------------------------------------

    def calculate_required_downtime(
        asset_name,
        location,
        start_datetime,
        resolved_datetime,
    ):
        if (
            not start_datetime
            or not resolved_datetime
        ):
            return {}

        start_dt = get_datetime(
            start_datetime
        )

        end_dt = get_datetime(
            resolved_datetime
        )

        if (
            not start_dt
            or not end_dt
            or end_dt <= start_dt
        ):
            return {}

        candidate_rows = (
            au_rows_by_asset_location.get(
                (
                    normalise_asset_name(
                        asset_name
                    ),
                    location,
                ),
                [],
            )
        )

        shift_results = {}

        for au_row in candidate_rows:
            try:
                row_date = getdate(
                    au_row.shift_date
                )

                if (
                    row_date
                    < add_days(
                        getdate(start_dt),
                        -1,
                    )
                ):
                    continue

                if (
                    row_date
                    > add_days(
                        getdate(end_dt),
                        1,
                    )
                ):
                    continue

                required_hours = max(
                    flt(
                        au_row.shift_required_hours
                    ),
                    0,
                )

                shift_start, shift_end = (
                    au.get_shift_timings(
                        au_row.shift_system,
                        au_row.shift,
                        str(
                            au_row.shift_date
                        ),
                    )
                )

                if (
                    not shift_start
                    or not shift_end
                ):
                    continue

                shift_overlap_hours = (
                    au._overlap_hours(
                        start_dt,
                        end_dt,
                        shift_start,
                        shift_end,
                    )
                )

                if shift_overlap_hours <= 0:
                    continue

                shift_excluded_hours = 0.0

                for (
                    window_start,
                    window_end,
                ) in get_cached_exclusion_windows(
                    au_row.location,
                    au_row.shift,
                    shift_start,
                    shift_end,
                ):
                    shift_excluded_hours += (
                        au._overlap_hours(
                            start_dt,
                            end_dt,
                            window_start,
                            window_end,
                        )
                    )

                shift_excluded_hours = min(
                    shift_excluded_hours,
                    shift_overlap_hours,
                )

                valid_overlap_hours = max(
                    (
                        shift_overlap_hours
                        - shift_excluded_hours
                    ),
                    0,
                )

                sunday_hours = 0.0
                required_downtime_hours = 0.0

                # Match get_required_downtime_minutes_for_breakdown():
                #
                # - A shift with zero required hours contributes no
                #   A&U mechanical downtime.
                # - If that zero-required shift is Sunday, keep its
                #   valid overlap in the Sunday bucket.
                # - Otherwise PBM may never exceed the shift's
                #   configured Required Hours.
                if required_hours <= 0:
                    if (
                        getdate(
                            au_row.shift_date
                        ).weekday() == 6
                    ):
                        sunday_hours = (
                            valid_overlap_hours
                        )
                else:
                    required_downtime_hours = min(
                        valid_overlap_hours,
                        required_hours,
                    )

                shift_key = (
                    str(au_row.shift_date),
                    au_row.shift,
                )

                bucket = shift_results.setdefault(
                    shift_key,
                    {
                        "pbm_elapsed_time": 0.0,
                        "pbm_startup_fatigue_time": 0.0,
                        "pbm_sunday_time": 0.0,
                        "pbm_total_downtime": 0.0,
                    },
                )

                bucket[
                    "pbm_elapsed_time"
                ] += shift_overlap_hours

                bucket[
                    "pbm_startup_fatigue_time"
                ] += shift_excluded_hours

                bucket[
                    "pbm_sunday_time"
                ] += sunday_hours

                bucket[
                    "pbm_total_downtime"
                ] += required_downtime_hours

            except Exception:
                continue

        return shift_results

    def round_shift_results_to_minutes(
        shift_results,
    ):
        """
        The canonical Breakdown/Month End helper returns integer
        minutes for each operational breakdown segment.

        The optimised Engine works in fractional hours, so distribute
        the rounded whole-minute total back to the contributing shifts
        while preserving the exact rounded segment total.
        """
        if not shift_results:
            return shift_results

        fieldnames = (
            "pbm_elapsed_time",
            "pbm_startup_fatigue_time",
            "pbm_sunday_time",
            "pbm_total_downtime",
        )

        rounded_results = {
            shift_key: {
                fieldname: 0.0
                for fieldname in fieldnames
            }
            for shift_key in shift_results
        }

        for fieldname in fieldnames:
            minute_parts = []
            total_exact_minutes = 0.0

            for (
                shift_key,
                values,
            ) in shift_results.items():

                exact_minutes = (
                    max(
                        flt(
                            values.get(
                                fieldname
                            )
                        ),
                        0.0,
                    )
                    * 60
                )

                whole_minutes = int(
                    exact_minutes
                )

                fractional_minute = (
                    exact_minutes
                    - whole_minutes
                )

                total_exact_minutes += (
                    exact_minutes
                )

                minute_parts.append([
                    shift_key,
                    whole_minutes,
                    fractional_minute,
                ])

            target_minutes = int(
                round(
                    total_exact_minutes
                )
            )

            assigned_minutes = sum(
                part[1]
                for part in minute_parts
            )

            extra_minutes = max(
                target_minutes
                - assigned_minutes,
                0,
            )

            # Largest-remainder allocation keeps the total exactly
            # equal to the canonical rounded minute total.
            minute_parts.sort(
                key=lambda part: (
                    -part[2],
                    str(part[0]),
                )
            )

            for index in range(
                min(
                    extra_minutes,
                    len(minute_parts),
                )
            ):
                minute_parts[
                    index
                ][1] += 1

            for (
                shift_key,
                whole_minutes,
                fractional_minute,
            ) in minute_parts:

                rounded_results[
                    shift_key
                ][
                    fieldname
                ] = (
                    whole_minutes
                    / 60
                )

        return rounded_results

    # ------------------------------------------------------------------
    # Build PBM map.
    # ------------------------------------------------------------------

    pbm_map = {}

    # Exact interval protection.
    seen_intervals = set()

    # Popup clean_reason_details() presents breakdown timestamps at
    # minute precision. Use the same operational-segment identity here
    # so records that only differ by seconds are not counted twice.
    seen_segments = set()

    for row in rows:
        start_dt = get_datetime(
            row.breakdown_start_datetime
        )

        end_dt = (
            get_datetime(
                row.resolved_datetime
            )
            if row.resolved_datetime
            else report_end
        )

        clipped_start = max(
            start_dt,
            report_start,
        )

        clipped_end = min(
            end_dt,
            report_end,
        )

        if clipped_end <= clipped_start:
            continue

        interval_key = (
            normalise_asset_name(
                row.asset_name
            ),
            row.location,
            str(clipped_start),
            str(clipped_end),
        )

        if interval_key in seen_intervals:
            continue

        seen_intervals.add(
            interval_key
        )

        current_date = getdate(
            clipped_start
        )

        current_day_start = get_datetime(
            f"{current_date} 06:00:00"
        )

        if clipped_start < current_day_start:
            current_date = add_days(
                current_date,
                -1,
            )

        while True:
            day_start = get_datetime(
                f"{current_date} 06:00:00"
            )

            day_end = (
                day_start
                + timedelta(days=1)
            )

            if day_start >= clipped_end:
                break

            segment_start = max(
                clipped_start,
                day_start,
            )

            segment_end = min(
                clipped_end,
                day_end,
            )

            if segment_end > segment_start:
                segment_key = (
                    normalise_asset_name(
                        row.asset_name
                    ),
                    row.location,
                    str(current_date),
                    str(segment_start)[:16],
                    str(segment_end)[:16],
                )

                if segment_key in seen_segments:
                    current_date = add_days(
                        current_date,
                        1,
                    )
                    continue

                seen_segments.add(
                    segment_key
                )

                calculated_by_shift = (
                    round_shift_results_to_minutes(
                        calculate_required_downtime(
                            row.asset_name,
                            row.location,
                            segment_start,
                            segment_end,
                        )
                    )
                )

                for (
                    shift_key,
                    calculated,
                ) in calculated_by_shift.items():
                    shift_date, shift = shift_key

                    key = (
                        normalise_asset_name(
                            row.asset_name
                        ),
                        shift_date,
                        row.location,
                        shift,
                    )

                    bucket = pbm_map.setdefault(
                        key,
                        {
                            "pbm_elapsed_time": 0.0,
                            "pbm_startup_fatigue_time": 0.0,
                            "pbm_sunday_time": 0.0,
                            "pbm_total_downtime": 0.0,
                        },
                    )

                    for fieldname in (
                        "pbm_elapsed_time",
                        "pbm_startup_fatigue_time",
                        "pbm_sunday_time",
                        "pbm_total_downtime",
                    ):
                        bucket[fieldname] += flt(
                            calculated.get(
                                fieldname
                            )
                        )

            current_date = add_days(
                current_date,
                1,
            )

    # Backward-compatible aliases for historical A&U records
    # whose asset_name contains leading/trailing whitespace.
    for au_row in au_rows:
        raw_asset_name = str(
            au_row.asset_name or ""
        )

        clean_asset_name = (
            normalise_asset_name(
                raw_asset_name
            )
        )

        if (
            not clean_asset_name
            or raw_asset_name
            == clean_asset_name
        ):
            continue

        clean_key = (
            clean_asset_name,
            str(au_row.shift_date),
            au_row.location,
            au_row.shift,
        )

        raw_key = (
            raw_asset_name,
            str(au_row.shift_date),
            au_row.location,
            au_row.shift,
        )

        if (
            clean_key in pbm_map
            and raw_key not in pbm_map
        ):
            pbm_map[
                raw_key
            ] = pbm_map[
                clean_key
            ]

    return pbm_map
# BEGIN INVALID AU PBM DRILLDOWN
@frappe.whitelist()
def get_invalid_au_pbm_records(
    asset_name=None,
    location=None,
    shift_date=None,
    shift=None,
):
    """
    Return the actual Plant Breakdown or Maintenance records that
    contribute PBM downtime to one A&U shift.

    This is a read-only drill-down helper for the Invalid A&U dialog.
    It does not alter any A&U or PBM calculations.
    """

    from frappe.utils import (
        flt,
        get_datetime,
        getdate,
    )

    from engineering.engineering.doctype.availability_and_utilisation import (
        availability_and_utilisation as au,
    )

    from engineering.engineering.report.availability_and_utilisation_month_end_report import (
        availability_and_utilisation_month_end_report as month_end,
    )

    asset_name = str(
        asset_name or ""
    ).strip()

    location = str(
        location or ""
    ).strip()

    shift = str(
        shift or ""
    ).strip()

    shift_date_text = str(
        shift_date or ""
    ).strip()

    if not asset_name:
        frappe.throw(
            "Machine is required."
        )

    if not shift_date_text:
        frappe.throw(
            "Shift Date is required."
        )

    if shift not in (
        "Day",
        "Night",
        "Morning",
        "Afternoon",
    ):
        frappe.throw(
            f"Unsupported shift: {shift}"
        )

    shift_date_value = getdate(
        shift_date_text
    )

    # ---------------------------------------------------------
    # Find the exact A&U shift row so that the same shift
    # system used by A&U is used for the PBM drill-down.
    # ---------------------------------------------------------

    au_conditions = [
        (
            "TRIM(IFNULL(asset_name, '')) "
            "= %(asset_name)s"
        ),
        "shift_date = %(shift_date)s",
        "shift = %(shift)s",
    ]

    au_values = {
        "asset_name": asset_name,
        "shift_date": shift_date_value,
        "shift": shift,
    }

    if location:
        au_conditions.append(
            "location = %(location)s"
        )

        au_values[
            "location"
        ] = location

    au_rows = frappe.db.sql(
        f"""
        SELECT
            name,
            shift_system,
            location,
            asset_name
        FROM `tabAvailability and Utilisation`
        WHERE {" AND ".join(au_conditions)}
        ORDER BY modified DESC
        LIMIT 2
        """,
        au_values,
        as_dict=True,
    )

    if not au_rows:
        frappe.throw(
            (
                "No Availability and Utilisation shift "
                f"was found for {asset_name} on "
                f"{shift_date_value} {shift}."
            )
        )

    if (
        not location
        and len(au_rows) > 1
    ):
        frappe.throw(
            (
                "More than one A&U shift was found. "
                "Please select a Location in the report."
            )
        )

    au_row = au_rows[0]

    location = str(
        au_row.get("location") or location or ""
    ).strip()

    shift_system = str(
        au_row.get("shift_system") or ""
    ).strip()

    shift_start, shift_end = (
        au.get_shift_timings(
            shift_system,
            shift,
            str(shift_date_value),
        )
    )

    if (
        not shift_start
        or not shift_end
    ):
        frappe.throw(
            (
                "Could not determine the A&U shift "
                f"window for {asset_name} "
                f"{shift_date_value} {shift}."
            )
        )

    # ---------------------------------------------------------
    # Load actual PBM documents overlapping this shift.
    # ---------------------------------------------------------

    pbm_rows = frappe.db.sql(
        """
        SELECT
            name,
            asset_name,
            location,
            breakdown_reason,
            breakdown_start_datetime,
            resolved_datetime
        FROM `tabPlant Breakdown or Maintenance`
        WHERE
            TRIM(IFNULL(asset_name, ''))
                = %(asset_name)s
            AND location = %(location)s
            AND IFNULL(breakdown_reason, '') != ''
            AND IFNULL(exclude_from_au, 0) = 0
            AND breakdown_start_datetime
                < %(shift_end)s
            AND (
                resolved_datetime
                    > %(shift_start)s
                OR resolved_datetime IS NULL
            )
        ORDER BY
            breakdown_start_datetime ASC,
            name ASC
        """,
        {
            "asset_name": asset_name,
            "location": location,
            "shift_start": shift_start,
            "shift_end": shift_end,
        },
        as_dict=True,
    )

    records = []
    seen_segments = set()

    for pbm_row in pbm_rows:
        start_datetime = pbm_row.get(
            "breakdown_start_datetime"
        )

        resolved_datetime = pbm_row.get(
            "resolved_datetime"
        )

        if not start_datetime:
            continue

        start_dt = get_datetime(
            start_datetime
        )

        end_dt = (
            get_datetime(
                resolved_datetime
            )
            if resolved_datetime
            else shift_end
        )

        clipped_start = max(
            start_dt,
            shift_start,
        )

        clipped_end = min(
            end_dt,
            shift_end,
        )

        if clipped_end <= clipped_start:
            continue

        # Match the Engine's minute-level duplicate protection.
        segment_key = (
            asset_name,
            location,
            str(shift_date_value),
            str(clipped_start)[:16],
            str(clipped_end)[:16],
        )

        if segment_key in seen_segments:
            continue

        seen_segments.add(
            segment_key
        )

        calculated = (
            month_end
            .get_required_downtime_minutes_for_breakdown(
                frappe._dict({
                    "location": location,
                    "start_date": (
                        str(shift_date_value)
                    ),
                    "end_date": (
                        str(shift_date_value)
                    ),
                }),
                asset_name,
                clipped_start,
                clipped_end,
            )
        )

        contributing_minutes = int(
            round(
                flt(
                    calculated.get(
                        "required_downtime_minutes"
                    )
                )
            )
        )

        # Do not show PBMs that overlap the physical shift but
        # contribute zero time to PBM Total Downtime.
        if contributing_minutes <= 0:
            continue

        records.append({
            "name": (
                pbm_row.get("name")
                or ""
            ),
            "breakdown_reason": (
                pbm_row.get(
                    "breakdown_reason"
                )
                or ""
            ),
            "breakdown_start_datetime": (
                str(
                    pbm_row.get(
                        "breakdown_start_datetime"
                    )
                    or ""
                )
            ),
            "resolved_datetime": (
                str(
                    pbm_row.get(
                        "resolved_datetime"
                    )
                    or ""
                )
            ),
            "contributing_minutes": (
                contributing_minutes
            ),
        })

    return {
        "asset_name": asset_name,
        "location": location,
        "shift_date": str(
            shift_date_value
        ),
        "shift": shift,
        "records": records,
    }
# END INVALID AU PBM DRILLDOWN
