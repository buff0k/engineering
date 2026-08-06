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
            "label": "Shift Available Hours",
            "fieldname": "shift_available_hours",
            "fieldtype": "Float",
            "precision": 3,
            "width": 175,
        },
        {
            "label": "Available Hours Above 100",
            "fieldname": "available_hours_above_100",
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
                daily_pbm = pbm_map.get(
                    (
                        asset.asset_name,
                        date_text,
                        location,
                    ),
                    {},
                )

                for shift in shifts:
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
                                location,
                                current_date,
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
                        "pbm_elapsed_time": 0.0,
                        "pbm_startup_fatigue_time": 0.0,
                        "pbm_sunday_time": 0.0,
                        "pbm_total_downtime": 0.0,
                        "indent": 3,
                    })

                asset_shift_rows = [
                    row
                    for row in shift_rows
                    if row.get("asset_name")
                    == asset.asset_name
                    and row.get("location")
                    == location
                    and str(row.get("shift_date"))
                    == date_text
                ]

                distribute_daily_pbm(
                    asset_shift_rows,
                    daily_pbm,
                )

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
        round_engine_row(row)

    return build_tree_rows(
        shift_rows
    )


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


def distribute_daily_pbm(
    shift_rows,
    daily_pbm,
):
    if not shift_rows:
        return

    total_required = sum(
        flt(
            row.get("required_hours")
        )
        for row in shift_rows
    )

    for row in shift_rows:
        if total_required > 0:
            ratio = (
                flt(
                    row.get("required_hours")
                )
                / total_required
            )
        else:
            ratio = (
                1
                / len(shift_rows)
            )

        for fieldname in (
            "pbm_elapsed_time",
            "pbm_startup_fatigue_time",
            "pbm_sunday_time",
            "pbm_total_downtime",
        ):
            row[fieldname] = (
                flt(
                    daily_pbm.get(
                        fieldname
                    )
                )
                * ratio
            )


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

    uncapped_available_hours = max(
        work_hours
        - pbm_total_downtime,
        0,
    )

    shift_available_hours = min(
        uncapped_available_hours,
        required_hours,
    )

    available_hours_above_100 = max(
        work_hours,
        shift_available_hours,
    )

    availability_percentage = (
        (
            available_hours_above_100
            / required_hours
        )
        * 100
        if required_hours > 0
        else 0
    )

    utilisation_percentage = (
        (
            work_hours
            / shift_available_hours
        )
        * 100
        if shift_available_hours > 0
        else 0
    )

    row["shift_available_hours"] = (
        shift_available_hours
    )

    row["available_hours_above_100"] = (
        available_hours_above_100
    )

    row["availability_percentage"] = (
        availability_percentage
    )

    row["utilisation_percentage"] = (
        utilisation_percentage
    )


def round_engine_row(row):
    for fieldname in (
        "actual_hours",
        "planned_downtime",
        "required_hours",
        "work_hours",
        "pbm_elapsed_time",
        "pbm_startup_fatigue_time",
        "pbm_sunday_time",
        "pbm_total_downtime",
        "shift_available_hours",
        "available_hours_above_100",
        "availability_percentage",
        "utilisation_percentage",
    ):
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
    ]


def build_summary_row(
    rows,
    indent,
    **identity_fields,
):
    valid_rows = get_valid_rows(
        rows
    )

    summary = {
        **identity_fields,
        "indent": indent,
        "invalid_pre_use_status": (
            ""
            if valid_rows
            else "No valid Pre-Use"
        ),
    }

    for fieldname in (
        "actual_hours",
        "planned_downtime",
        "required_hours",
        "work_hours",
        "pbm_elapsed_time",
        "pbm_startup_fatigue_time",
        "pbm_sunday_time",
        "pbm_total_downtime",
    ):
        summary[fieldname] = round(
            sum(
                flt(
                    row.get(fieldname)
                )
                for row in valid_rows
            ),
            3,
        )

    calculate_availability_values(
        summary
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

    for category in sorted(grouped):
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
    location,
    shift_date,
    shift,
):
    daily_hours = get_actual_hours(
        location,
        shift_date,
    )

    if shift in (
        "Day",
        "Night",
    ):
        return daily_hours / 2

    return daily_hours / 3


def get_shift_planned_downtime(
    location,
    shift_date,
    shift,
):
    daily_hours = get_planned_downtime(
        location,
        shift_date,
    )

    if shift in (
        "Day",
        "Night",
    ):
        return daily_hours / 2

    return daily_hours / 3


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


def get_actual_hours(
    location,
    shift_date,
):
    day_of_week = getdate(
        shift_date
    ).weekday()

    site = (
        location or ""
    ).strip().lower()

    special_saturday_sites = {
        "koppie",
        "uitgevallen",
        "bankfontein",
        "kriel",
    }

    if day_of_week == 6:
        return 0.0

    if day_of_week == 5:
        if site in special_saturday_sites:
            return 18.0

        return 24.0

    return 24.0


def get_planned_downtime(
    location,
    shift_date,
):
    day_of_week = getdate(
        shift_date
    ).weekday()

    site = (
        location or ""
    ).strip().lower()

    special_saturday_sites = {
        "koppie",
        "uitgevallen",
        "bankfontein",
        "kriel",
    }

    if day_of_week == 6:
        return 0.0

    if day_of_week == 5:
        if site in special_saturday_sites:
            return 4.0

        return 6.0

    return 6.0


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
    from engineering.engineering.report.availability_and_utilisation_month_end_report import (
        availability_and_utilisation_month_end_report as month_end,
    )

    report_start = get_datetime(
        f"{from_date} 06:00:00"
    )

    report_end = get_datetime(
        f"{add_days(to_date, 1)} 06:00:00"
    )

    asset_names = sorted({
        asset.asset_name
        for asset in assets
        if asset.asset_name
    })

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
        "asset_names": tuple(
            asset_names
        ),
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

    pbm_map = {}
    seen_intervals = set()

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
            row.asset_name,
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
                calculated = (
                    month_end
                    .get_required_downtime_minutes_for_breakdown(
                        frappe._dict({
                            "location": (
                                row.location
                            ),
                            "start_date": (
                                from_date
                            ),
                            "end_date": (
                                to_date
                            ),
                        }),
                        row.asset_name,
                        segment_start,
                        segment_end,
                    )
                )

                key = (
                    row.asset_name,
                    str(current_date),
                    row.location,
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

                bucket[
                    "pbm_elapsed_time"
                ] += (
                    flt(
                        calculated.get(
                            "total_minutes"
                        )
                    )
                    / 60
                )

                bucket[
                    "pbm_startup_fatigue_time"
                ] += (
                    flt(
                        calculated.get(
                            "excluded_minutes"
                        )
                    )
                    / 60
                )

                bucket[
                    "pbm_sunday_time"
                ] += (
                    flt(
                        calculated.get(
                            "sunday_minutes"
                        )
                    )
                    / 60
                )

                bucket[
                    "pbm_total_downtime"
                ] += (
                    flt(
                        calculated.get(
                            "required_downtime_minutes"
                        )
                    )
                    / 60
                )

            current_date = add_days(
                current_date,
                1,
            )

    return pbm_map