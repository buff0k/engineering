# availability_and_utilisation.py
# Drop-in replacement (safe import, worker-safe, no Pre-Use changes required)

import frappe
from frappe.utils import (
    getdate,
    add_days,
    today,
    formatdate,
    get_first_day,
    get_last_day,
    time_diff_in_hours,
    get_datetime,
    now_datetime,
)
from datetime import timedelta
from frappe.model.document import Document


# =============================================================================
# Helpers (IMPORT-SAFE)
# =============================================================================

def _safe_flag(name: str) -> bool:
    """Avoid AttributeError on older/newer frappe flags."""
    try:
        return bool(getattr(frappe.flags, name, False))
    except Exception:
        return False


def _get_doc_asset_item_name(doc_name):
    """Safely retrieve asset_name and item_name from an existing AU doc."""
    try:
        d = frappe.get_doc("Availability and Utilisation", doc_name)
        return (d.asset_name or "Unknown", d.item_name or "Unknown")
    except Exception:
        return ("Unknown", "Unknown")


def _preuse_docname_from_au(doc):
    """
    Pre-Use Hours autoname is: format:{location}-{shift_date}-{shift}
    and shift_date is stored as YYYY-MM-DD.
    """
    sd = getdate(doc.shift_date).strftime("%Y-%m-%d")
    return f"{doc.location}-{sd}-{doc.shift}"


def _get_preuse_doc_for_au(doc):
    """
    Return a Pre-Use Hours doc matched for this AU doc WITHOUT requiring
    Pre-Use changes. Tries:
      1) Pre-Use Hours.avail_util_lookup == AU.pre_use_lookup
      2) Pre-Use Hours.name == {location}-{YYYY-MM-DD}-{shift} (autoname)
      3) Fallback search by location+shift_date+shift
    """
    # 1) Best: avail_util_lookup (if it exists and is populated)
    if getattr(doc, "pre_use_lookup", None):
        try:
            hit = frappe.get_all(
                "Pre-Use Hours",
                filters={"avail_util_lookup": doc.pre_use_lookup},
                fields=["name"],
                limit=1,
            )
            if hit:
                return frappe.get_doc("Pre-Use Hours", hit[0].name)
        except Exception:
            # Field may not exist on some sites; ignore and continue
            pass

    # 2) Autoname match
    name_guess = _preuse_docname_from_au(doc)
    if frappe.db.exists("Pre-Use Hours", name_guess):
        return frappe.get_doc("Pre-Use Hours", name_guess)

    # 3) Fallback filter match (handles renamed records / legacy)
    try:
        hit = frappe.get_all(
            "Pre-Use Hours",
            filters={
                "location": doc.location,
                "shift_date": doc.shift_date,
                "shift": doc.shift,
            },
            fields=["name"],
            limit=1,
        )
        if hit:
            return frappe.get_doc("Pre-Use Hours", hit[0].name)
    except Exception:
        pass

    return None


def _preuse_row_plant_no(preuse_row):
    """
    Pre-Use child row:
      - row.asset_name is Link -> Asset (stores Asset.name)
      - row.plant_no (Data) may exist and may be filled by JS
    We need Plant No (Asset.asset_name) to match AU.asset_name.
    """
    # Prefer plant_no if present and populated
    plant_no = getattr(preuse_row, "plant_no", None)
    if plant_no:
        return plant_no

    asset_link = getattr(preuse_row, "asset_name", None)
    if not asset_link:
        return None

    # asset_link is Asset.name
    try:
        return frappe.db.get_value("Asset", asset_link, "asset_name")
    except Exception:
        return None


def get_shift_timings(shift_system, shift, shift_date):
    """Calculate shift start and end timings based on the system and shift."""
    shift_start = None
    shift_end = None

    if shift_system == "3x8Hour":
        if shift == "Morning":
            shift_start = get_datetime(shift_date + " 06:00:00")
            shift_end = get_datetime(shift_date + " 14:00:00")
        elif shift == "Afternoon":
            shift_start = get_datetime(shift_date + " 14:00:00")
            shift_end = get_datetime(shift_date + " 22:00:00")
        elif shift == "Night":
            shift_start = get_datetime(shift_date + " 22:00:00")
            next_day = (getdate(shift_date) + timedelta(days=1)).strftime("%Y-%m-%d")
            shift_end = get_datetime(next_day + " 06:00:00")

    elif shift_system == "2x12Hour":
        if shift == "Day":
            shift_start = get_datetime(shift_date + " 06:00:00")
            shift_end = get_datetime(shift_date + " 18:00:00")
        elif shift == "Night":
            shift_start = get_datetime(shift_date + " 18:00:00")
            next_day = (getdate(shift_date) + timedelta(days=1)).strftime("%Y-%m-%d")
            shift_end = get_datetime(next_day + " 06:00:00")

    return shift_start, shift_end


# =============================================================================
# Main DocType
# =============================================================================

class AvailabilityandUtilisation(Document):
    @staticmethod
    def generate_records():
        # Prevent execution during migration or app install
        if _safe_flag("in_migrate") or _safe_flag("in_install_app"):
            frappe.logger().info("Skipped generate_records during migrate/install")
            return

        process_started_at = now_datetime()
        created_records = []
        updated_records = []
        error_records = []
        record_logs = {}  # aggregated per record

        def append_log(record_key, message):
            record_logs.setdefault(record_key, []).append(message)

        current_date = getdate(today())

        # =============================================================================
        # Phase 1: Create or Update AU docs (last 7 days)
        # =============================================================================
        start_date = current_date - timedelta(days=7)
        end_date = current_date

        production_planning_records = frappe.get_all(
            "Monthly Production Planning",
            filters={
                "site_status": "Producing",
                "prod_month_start_date": ["<=", end_date],
                "prod_month_end_date": [">=", start_date],
            },
            fields=["location", "prod_month_start_date", "prod_month_end_date", "shift_system"],
            order_by="prod_month_start_date asc",
        )

        date = start_date
        while date <= end_date:
            for planning_record in production_planning_records:
                location = planning_record.location
                shift_system = (planning_record.shift_system or "").strip()
                prod_month_start_date = planning_record.prod_month_start_date
                prod_month_end_date = planning_record.prod_month_end_date

                if not (getdate(date) >= getdate(prod_month_start_date) and getdate(date) <= getdate(prod_month_end_date)):
                    continue

                assets = frappe.get_all(
                    "Asset",
                    filters={
                        "location": location,
                        "asset_category": ["in", ["Dozer", "ADT", "Rigid", "Excavator"]],
                        "docstatus": 1,
                    },
                    fields=["name", "asset_name", "item_name", "asset_category"],
                )

                shifts = ["Day", "Night"] if shift_system.lower() == "2x12hour" else ["Morning", "Afternoon", "Night"]

                for shift in shifts:
                    for asset in assets:
                        record_key = f"{location}-{asset.asset_name}-{date}-{shift}"
                        try:
                            existing_record = frappe.get_all(
                                "Availability and Utilisation",
                                filters={
                                    "shift_date": date,
                                    "location": location,
                                    "shift": shift,
                                    "asset_name": asset.asset_name,  # AU stores Plant No in asset_name
                                },
                                fields=["name"],
                                limit=1,
                            )

                            if existing_record:
                                doc = frappe.get_doc("Availability and Utilisation", existing_record[0].name)
                                doc.pre_use_lookup = None
                                doc.pre_use_link = None
                                doc.save(ignore_permissions=True)

                                doc.db_set("day_number", getdate(date).day, update_modified=True)
                                doc.db_set("asset_category", asset.asset_category, update_modified=True)

                                updated_records.append(doc.name)
                                append_log(
                                    doc.name,
                                    (
                                        f"Phase 1: Updated record={doc.name}, shift={shift}, date={date}, "
                                        f"asset_name={doc.asset_name}, item_name={doc.item_name}, "
                                        f"day_number={getdate(date).day}, asset_category={asset.asset_category}"
                                    ),
                                )
                            else:
                                doc = frappe.get_doc(
                                    {
                                        "doctype": "Availability and Utilisation",
                                        "shift_date": date,
                                        "shift": shift,
                                        "asset_name": asset.asset_name,  # Plant No
                                        "location": location,
                                        "shift_system": shift_system,
                                        "pre_use_lookup": None,
                                        "pre_use_link": None,
                                    }
                                )
                                doc.insert(ignore_permissions=True)

                                doc.db_set("day_number", getdate(date).day, update_modified=True)
                                doc.db_set("asset_category", asset.asset_category, update_modified=True)

                                created_records.append(doc.name)
                                append_log(
                                    doc.name,
                                    (
                                        f"Phase 1: Created record={doc.name}, shift={shift}, date={date}, "
                                        f"asset_name={doc.asset_name}, item_name={doc.item_name}, "
                                        f"day_number={getdate(date).day}, asset_category={asset.asset_category}"
                                    ),
                                )
                        except Exception as e:
                            err_msg = (
                                f"Phase 1 Error: asset_name={asset.asset_name}, item_name={asset.item_name}, "
                                f"location={location}, date={date}, shift={shift}: {str(e)}"
                            )
                            append_log(record_key, err_msg)
                            error_records.append(err_msg)

            date = add_days(date, 1)

        # =============================================================================
        # Phase 2: Update pre_use_lookup field
        # =============================================================================
        for doc_name in created_records + updated_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)
                formatted_date = formatdate(doc.shift_date, "dd-mm-yyyy")
                doc.pre_use_lookup = f"{doc.location}-{formatted_date}-{doc.shift}"
                doc.save(ignore_permissions=True)
                append_log(doc.name, f"Phase 2: pre_use_lookup updated for doc={doc.name}")
            except Exception as e:
                asset_name, item_name = _get_doc_asset_item_name(doc_name)
                err_msg = f"Phase 2 Error for doc={doc_name}, asset_name={asset_name}, item_name={item_name}: {str(e)}"
                append_log(doc_name, err_msg)
                error_records.append(err_msg)

        # =============================================================================
        # Phase 3: Update pre_use_link using pre_use_lookup (WITH FALLBACKS)
        # =============================================================================
        for doc_name in created_records + updated_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)

                pre_use_doc = _get_preuse_doc_for_au(doc)
                if pre_use_doc:
                    doc.pre_use_link = pre_use_doc.name
                    doc.save(ignore_permissions=True)
                    append_log(doc.name, f"Phase 3: pre_use_link set to {pre_use_doc.name} for doc={doc.name}")
                else:
                    append_log(doc.name, f"Phase 3: No Pre-Use Hours found for doc={doc.name} lookup={doc.pre_use_lookup}")

            except Exception as e:
                asset_name, item_name = _get_doc_asset_item_name(doc_name)
                err_msg = f"Phase 3 Error for doc={doc_name}, asset_name={asset_name}, item_name={item_name}: {str(e)}"
                append_log(doc_name, err_msg)
                error_records.append(err_msg)

        # =============================================================================
        # Phase 4: Update shift_required_hours  (FIXED FILTERS)
        # =============================================================================
        relevant_records = frappe.get_all(
            "Availability and Utilisation",
            filters=[
                ["shift_date", ">=", get_first_day(today())],
                ["shift_date", "<=", get_last_day(today())],
            ],
            fields=["name", "shift_date", "location", "shift"],
        )

        for record in relevant_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", record.name)
                shift_date = getdate(doc.shift_date)
                location = doc.location

                planning_doc_row = frappe.get_all(
                    "Monthly Production Planning",
                    filters={
                        "prod_month_start_date": ["<=", shift_date],
                        "prod_month_end_date": [">=", shift_date],
                        "location": location,
                        "site_status": "Producing",
                    },
                    fields=["name"],
                    limit=1,
                )
                if not planning_doc_row:
                    continue

                planning_doc = frappe.get_doc("Monthly Production Planning", planning_doc_row[0].name)
                for day in planning_doc.month_prod_days:
                    if getdate(day.shift_start_date) == shift_date:
                        if doc.shift == "Day":
                            doc.shift_required_hours = day.shift_day_hours
                        elif doc.shift == "Night":
                            doc.shift_required_hours = day.shift_night_hours
                        elif doc.shift == "Morning":
                            doc.shift_required_hours = day.shift_morning_hours
                        elif doc.shift == "Afternoon":
                            doc.shift_required_hours = day.shift_afternoon_hours

                        doc.save(ignore_permissions=True)
                        append_log(doc.name, f"Phase 4: shift_required_hours updated for doc={doc.name}")
                        break

            except Exception as e:
                asset_name, item_name = _get_doc_asset_item_name(record["name"])
                err_msg = f"Phase 4 Error for doc={record['name']}, asset_name={asset_name}, item_name={item_name}: {str(e)}"
                append_log(record["name"], err_msg)
                error_records.append(err_msg)

        # =============================================================================
        # Phase 5: Update from Pre-Use Hours (FIXED ASSET MATCHING, NO PRE-USE CHANGES)
        # =============================================================================
        for doc_name in created_records + updated_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)

                pre_use_doc = _get_preuse_doc_for_au(doc)
                if not pre_use_doc:
                    append_log(doc.name, f"Phase 5: No Pre-Use Hours found for doc={doc.name} lookup={doc.pre_use_lookup}")
                    continue

                # AU asset_name is Plant No
                target_plant_no = doc.asset_name
                matched_row = None

                for asset_row in pre_use_doc.pre_use_assets:
                    row_plant_no = _preuse_row_plant_no(asset_row)
                    if row_plant_no and row_plant_no == target_plant_no:
                        matched_row = asset_row
                        break

                if not matched_row:
                    append_log(
                        doc.name,
                        f"Phase 5: Pre-Use Hours {pre_use_doc.name} found but no asset matched Plant No={target_plant_no}",
                    )
                    continue

                # Apply values
                if matched_row.eng_hrs_start is not None:
                    doc.shift_start_hours = matched_row.eng_hrs_start
                if matched_row.eng_hrs_end is not None:
                    doc.shift_end_hours = matched_row.eng_hrs_end

                if getattr(matched_row, "pre_use_avail_status", None) is not None:
                    doc.pre_use_avail_status = matched_row.pre_use_avail_status

                if doc.shift_start_hours is not None and doc.shift_end_hours is not None:
                    doc.shift_working_hours = max(0, doc.shift_end_hours - doc.shift_start_hours)
                else:
                    doc.shift_working_hours = 0

                # Ensure link is set too
                doc.pre_use_link = pre_use_doc.name
                doc.save(ignore_permissions=True)

                append_log(doc.name, f"Phase 5: Pre-Use Hours applied for doc={doc.name} from {pre_use_doc.name}")

            except Exception as e:
                asset_name, item_name = _get_doc_asset_item_name(doc_name)
                err_msg = f"Phase 5 Error for doc={doc_name}, asset_name={asset_name}, item_name={item_name}: {str(e)}"
                append_log(doc_name, err_msg)
                error_records.append(err_msg)

        # =============================================================================
        # Phase 6: Update item_name using asset lookup
        # =============================================================================
        for doc_name in created_records + updated_records:
            previous_item_name = None
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)
                previous_item_name = doc.item_name

                asset_doc = frappe.get_all(
                    "Asset",
                    filters={"asset_name": doc.asset_name, "docstatus": 1},  # doc.asset_name = Plant No
                    fields=["item_name"],
                    limit=1,
                )
                if asset_doc:
                    fetched_item_name = asset_doc[0].get("item_name")
                    if fetched_item_name != previous_item_name:
                        doc.item_name = fetched_item_name or None
                        doc.save(ignore_permissions=True)
                        append_log(doc.name, f"Phase 6: item_name updated for doc={doc.name}")
            except Exception as e:
                asset_name, item_name = _get_doc_asset_item_name(doc_name)
                err_msg = (
                    f"Phase 6 Error for doc={doc_name}, asset_name={asset_name}, item_name={item_name}: {str(e)}. "
                    f"Previous item_name: {previous_item_name}."
                )
                append_log(doc_name, err_msg)
                error_records.append(err_msg)

        # =============================================================================
        # Phase 7: Update shift_breakdown_hours
        # =============================================================================
        current_date = getdate(today())
        start_date = current_date - timedelta(days=7)

        parent_records = frappe.get_all(
            "Availability and Utilisation",
            filters=[["shift_date", ">=", start_date], ["shift_date", "<=", current_date]],
            fields=[
                "name",
                "shift_date",
                "shift",
                "shift_system",
                "location",
                "asset_name",
                "shift_breakdown_hours",
            ],
            order_by="creation desc",
        )

        for parent_record in parent_records:
            try:
                breakdown_history_rows = frappe.get_all(
                    "Breakdown History",
                    filters={
                        "location": parent_record["location"],
                        "asset_name": parent_record["asset_name"],
                        "exclude_from_au": 0,  # only include unexcluded breakdowns
                    },
                    fields=["update_date_time", "breakdown_status"],
                    order_by="update_date_time",
                )

                if not breakdown_history_rows:
                    append_log(parent_record["name"], f"Phase 7: No breakdown history found for doc={parent_record['name']}")
                    continue

                # shift start/end times
                shift_start, shift_end = get_shift_timings(
                    parent_record["shift_system"],
                    parent_record["shift"],
                    str(parent_record["shift_date"]),
                )

                breakdown_start = breakdown_history_rows[0]["update_date_time"]
                breakdown_end = None
                for row in breakdown_history_rows:
                    if str(row["breakdown_status"]) == "3":
                        breakdown_end = row["update_date_time"]

                if not breakdown_end:
                    breakdown_end = shift_end

                shift_breakdown_hours = 0
                scenario = None

                if breakdown_start < shift_end and breakdown_end > shift_start:
                    if breakdown_start >= shift_start:
                        if breakdown_end <= shift_end:
                            shift_breakdown_hours = time_diff_in_hours(breakdown_end, breakdown_start)
                            scenario = "Scenario 3: Breakdown within shift."
                        else:
                            shift_breakdown_hours = time_diff_in_hours(shift_end, breakdown_start)
                            scenario = "Scenario 4: Breakdown started during shift and continued."
                    else:
                        if breakdown_end <= shift_end:
                            shift_breakdown_hours = time_diff_in_hours(breakdown_end, shift_start)
                            scenario = "Scenario 2: Breakdown started before shift and ended during shift."
                        else:
                            shift_breakdown_hours = time_diff_in_hours(shift_end, shift_start)
                            scenario = "Scenario 1: Breakdown spanned the entire shift."
                else:
                    shift_breakdown_hours = 0
                    scenario = "No Breakdown During Shift"

                # Cap breakdown hours: does not exceed (required - working)
                doc = frappe.get_doc("Availability and Utilisation", parent_record["name"])
                shift_required_hours = doc.shift_required_hours or 0
                shift_working_hours = doc.shift_working_hours or 0
                max_breakdown_allowed = max(shift_required_hours - shift_working_hours, 0)
                shift_breakdown_hours = min(shift_breakdown_hours, max_breakdown_allowed)

                frappe.db.set_value(
                    "Availability and Utilisation",
                    parent_record["name"],
                    "shift_breakdown_hours",
                    shift_breakdown_hours,
                )

                append_log(
                    parent_record["name"],
                    (
                        f"Phase 7: shift_breakdown_hours updated for doc={parent_record['name']}. "
                        f"{scenario} => {shift_breakdown_hours} hour(s). "
                        f"(Shift Start: {shift_start}, Shift End: {shift_end}, "
                        f"Breakdown Start: {breakdown_start}, Breakdown End: {breakdown_end})"
                    ),
                )

            except Exception as e:
                asset_name, item_name = _get_doc_asset_item_name(parent_record["name"])
                err_msg = f"Phase 7 Error for doc={parent_record['name']}, asset_name={asset_name}, item_name={item_name}: {str(e)}"
                append_log(parent_record["name"], err_msg)
                error_records.append(err_msg)

        # =============================================================================
        # Phase 8: Calculate and set final fields
        # =============================================================================
        for doc_name in created_records + updated_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)

                shift_required_hours = doc.shift_required_hours or 0
                shift_breakdown_hours = doc.shift_breakdown_hours or 0
                shift_working_hours = doc.shift_working_hours or 0

                if doc.pre_use_avail_status in ("3", "6"):
                    shift_required_hours = 0
                    shift_available_hours = shift_working_hours
                    shift_other_lost_hours = 0
                else:
                    shift_available_hours = max(shift_required_hours - shift_breakdown_hours, 0)
                    if shift_working_hours > shift_available_hours:
                        shift_other_lost_hours = max(shift_required_hours - shift_working_hours, 0)
                    else:
                        shift_other_lost_hours = max(shift_available_hours - shift_working_hours, 0)

                doc.shift_required_hours = shift_required_hours
                doc.shift_available_hours = shift_available_hours
                doc.shift_other_lost_hours = shift_other_lost_hours

                max_val = max(shift_working_hours, shift_available_hours)

                doc.plant_shift_utilisation = (shift_working_hours / shift_available_hours) * 100 if shift_available_hours > 0 else 0

                if doc.pre_use_avail_status in ("3", "6"):
                    doc.plant_shift_availability = 100
                else:
                    doc.plant_shift_availability = (max_val / shift_required_hours) * 100 if shift_required_hours > 0 else 0

                doc.save(ignore_permissions=True)

                append_log(
                    doc.name,
                    (
                        f"Phase 8: Final fields updated for doc={doc.name}. "
                        f"(shift_required_hours={shift_required_hours}, "
                        f"shift_breakdown_hours={shift_breakdown_hours}, "
                        f"shift_working_hours={shift_working_hours}, "
                        f"shift_available_hours={shift_available_hours}, "
                        f"shift_other_lost_hours={shift_other_lost_hours}, "
                        f"plant_shift_utilisation={doc.plant_shift_utilisation}, "
                        f"plant_shift_availability={doc.plant_shift_availability})"
                    ),
                )

            except Exception as e:
                asset_name, item_name = _get_doc_asset_item_name(doc_name)
                err_msg = f"Phase 8 Error for doc={doc_name}, asset_name={asset_name}, item_name={item_name}: {str(e)}"
                append_log(doc_name, err_msg)
                error_records.append(err_msg)

        # =============================================================================
        # Phase 9: Combined Log (Split into 10 parts)
        # =============================================================================
        record_keys = list(record_logs.keys())
        total_logs = len(record_keys)
        max_logs_per_entry = max(1, total_logs // 10)

        for i in range(0, total_logs, max_logs_per_entry):
            batch_keys = record_keys[i : i + max_logs_per_entry]
            batch_messages = []
            for key in batch_keys:
                batch_messages.append(f"{key}: " + " | ".join(record_logs[key]))

            frappe.log_error("\n".join(batch_messages), f"Phase Update Log - Batch {i // max_logs_per_entry + 1}")

        # =============================================================================
        # Phase 10: Summary Log
        # =============================================================================
        process_completed_at = now_datetime()
        duration = process_completed_at - process_started_at

        success_message = (
            f"Successfully created {len(created_records)} records. "
            f"Updated {len(updated_records)} records. "
            f"Started at {process_started_at.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"completed at {process_completed_at.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"duration {duration}. "
        )
        if error_records:
            success_message += f"Errors encountered: {len(error_records)}. Check log batches for details."

        frappe.log_error(message=success_message, title="Availability & Utilisation - Process Completion")
        return success_message


# =============================================================================
# Whitelisted: Manual trigger
# =============================================================================

@frappe.whitelist()
def create_availability_and_utilisation():
    """Manual trigger to run generation of records."""
    return AvailabilityandUtilisation.generate_records()


# =============================================================================
# Whitelisted: Targeted single-record sync (FAST TEST, NO ENGINE)
# =============================================================================

@frappe.whitelist()
def sync_single_au(au_name: str):
    """
    Fast, end-to-end test:
      - updates pre_use_lookup
      - finds matching Pre-Use Hours (no Pre-Use changes required)
      - pulls start/end/working hours into AU

    Safe to run in production for ONE doc.
    """
    doc = frappe.get_doc("Availability and Utilisation", au_name)

    # build lookup same as engine
    formatted_date = formatdate(doc.shift_date, "dd-mm-yyyy")
    doc.pre_use_lookup = f"{doc.location}-{formatted_date}-{doc.shift}"

    pre_use_doc = _get_preuse_doc_for_au(doc)
    if not pre_use_doc:
        doc.save(ignore_permissions=True)
        return f"No Pre-Use Hours found for AU={doc.name} lookup={doc.pre_use_lookup}"

    target_plant_no = doc.asset_name
    matched_row = None
    for r in pre_use_doc.pre_use_assets:
        if _preuse_row_plant_no(r) == target_plant_no:
            matched_row = r
            break

    if not matched_row:
        doc.pre_use_link = pre_use_doc.name
        doc.save(ignore_permissions=True)
        return f"Pre-Use {pre_use_doc.name} found but no matching asset for Plant No={target_plant_no}"

    doc.pre_use_link = pre_use_doc.name
    doc.shift_start_hours = matched_row.eng_hrs_start
    doc.shift_end_hours = matched_row.eng_hrs_end
    doc.pre_use_avail_status = matched_row.pre_use_avail_status

    if doc.shift_start_hours is not None and doc.shift_end_hours is not None:
        doc.shift_working_hours = max(0, doc.shift_end_hours - doc.shift_start_hours)
    else:
        doc.shift_working_hours = 0

    doc.save(ignore_permissions=True)
    return f"Synced AU={doc.name} from Pre-Use={pre_use_doc.name} (Plant No={target_plant_no})"


# =============================================================================
# Scheduled job: enqueue heavy processing on long queue
# =============================================================================

@frappe.whitelist()
def run_daily():
    """Scheduled job: enqueue heavy processing on the long queue."""
    started_at = now_datetime()
    frappe.log_error(
        f"Scheduled job enqueuing at {started_at.strftime('%Y-%m-%d %H:%M:%S')} for Availability and Utilisation",
        "Daily Job Start",
    )

    frappe.enqueue(
        "engineering.engineering.doctype.availability_and_utilisation.availability_and_utilisation.create_availability_and_utilisation",
        queue="long",
        job_name="Availability & Utilisation Engine (Scheduled)",
        timeout=60 * 60,
    )

    enqueued_at = now_datetime()
    frappe.log_error(
        f"Scheduled job enqueued at {enqueued_at.strftime('%Y-%m-%d %H:%M:%S')} for Availability and Utilisation",
        "Daily Job Enqueued",
    )


# =============================================================================
# Background queue function
# =============================================================================

@frappe.whitelist()
def queue_availability_and_utilisation():
    """
    Enqueue the AU generation process to run in background (async).
    """
    frappe.enqueue(
        "engineering.engineering.doctype.availability_and_utilisation.availability_and_utilisation.create_availability_and_utilisation",
        queue="long",
        job_name="Availability & Utilisation Engine Run",
        timeout=60 * 60,
    )
    frappe.msgprint(
        msg="⏳ Availability & Utilisation generation has been queued. Check Error Log for progress.",
        title="Process Queued",
        indicator="blue",
    )
    return "Queued"
