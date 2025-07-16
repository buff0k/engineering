import frappe
from frappe.utils import (
    getdate,
    add_days,
    today,
    formatdate,
    get_first_day,
    get_last_day,
    time_diff_in_hours,
    get_datetime
)
from datetime import timedelta
from frappe.model.document import Document

class AvailabilityandUtilisation(Document):
    @staticmethod
    def generate_records():
        # Prevent execution during migration or app install
        if frappe.flags.in_migrate or frappe.flags.in_install_app:
            frappe.logger().info("Skipped generate_records during migrate/install")
            return
        created_records = []
        updated_records = []
        error_records = []
        record_logs = {}  # Dictionary to hold aggregated log messages per record

        def append_log(record_key, message):
            """Helper function to append a message for a given record key."""
            if record_key not in record_logs:
                record_logs[record_key] = []
            record_logs[record_key].append(message)

        def get_doc_asset_item_name(doc_name):
            """
            Safely retrieve asset_name and item_name from an existing
            'Availability and Utilisation' document. If not found, return Unknown.
            """
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)
                return (doc.asset_name or "Unknown", doc.item_name or "Unknown")
            except Exception:
                return ("Unknown", "Unknown")

        current_date = getdate(today())

        # =============================================================================
        # Phase 1: Create or Update Availability and Utilisation documents
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
                shift_system = planning_record.shift_system
                prod_month_start_date = planning_record.prod_month_start_date
                prod_month_end_date = planning_record.prod_month_end_date

                if (getdate(date) >= getdate(prod_month_start_date)) and (getdate(date) <= getdate(prod_month_end_date)):
                    # Fetch Asset info, including asset_category now
                    assets = frappe.get_all(
                        "Asset",
                        filters={
                            "location": location,
                            "asset_category": ["in", ["Dozer", "ADT", "Rigid", "Excavator"]],
                            "docstatus": 1,
                        },
                        fields=["name", "asset_name", "item_name", "asset_category"],
                    )

                    shifts = (
                        ["Day", "Night"]
                        if shift_system.strip().lower() == "2x12hour"
                        else ["Morning", "Afternoon", "Night"]
                    )

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
                                        "asset_name": asset.asset_name,
                                    },
                                    fields=["name"],
                                    limit=1,
                                )

                                if existing_record:
                                    # -------------------------------
                                    # Update Existing Record
                                    # -------------------------------
                                    doc = frappe.get_doc("Availability and Utilisation", existing_record[0].name)
                                    doc.pre_use_lookup = None
                                    doc.pre_use_link = None
                                    doc.save(ignore_permissions=True)
                                    # Update read-only fields using db_set
                                    doc.db_set("day_number", getdate(date).day, update_modified=True)
                                    doc.db_set("asset_category", asset.asset_category, update_modified=True)
                                    updated_records.append(doc.name)
                                    append_log(
                                        doc.name,
                                        (
                                            f"Phase 1: Updated record={doc.name}, shift={shift}, date={date}, "
                                            f"asset_name={doc.asset_name}, item_name={doc.item_name}, "
                                            f"day_number={getdate(date).day}, asset_category={asset.asset_category}"
                                        )
                                    )
                                else:
                                    # -------------------------------
                                    # Create New Record
                                    # -------------------------------
                                    doc = frappe.get_doc({
                                        "doctype": "Availability and Utilisation",
                                        "shift_date": date,
                                        "shift": shift,
                                        "asset_name": asset.asset_name,
                                        "location": location,
                                        "shift_system": shift_system,
                                        "pre_use_lookup": None,
                                        "pre_use_link": None
                                    })
                                    doc.insert(ignore_permissions=True)
                                    # Update read-only fields using db_set
                                    doc.db_set("day_number", getdate(date).day, update_modified=True)
                                    doc.db_set("asset_category", asset.asset_category, update_modified=True)
                                    created_records.append(doc.name)
                                    append_log(
                                        doc.name,
                                        (
                                            f"Phase 1: Created record={doc.name}, shift={shift}, date={date}, "
                                            f"asset_name={doc.asset_name}, item_name={doc.item_name}, "
                                            f"day_number={getdate(date).day}, asset_category={asset.asset_category}"
                                        )
                                    )
                            except Exception as e:
                                err_msg = (
                                    f"Phase 1 Error: asset_name={asset.asset_name}, item_name={asset.item_name}, "
                                    f"location={location}, date={date}, shift={shift}: {str(e)}"
                                )
                                append_log(record_key, err_msg)
                                error_records.append(err_msg)
                        # The break statement has been removed here so that every shift is processed.
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
                append_log(
                    doc.name,
                    (
                        f"Phase 2: pre_use_lookup updated for doc={doc.name}, "
                        f"asset_name={doc.asset_name}, item_name={doc.item_name}"
                    )
                )
            except Exception as e:
                asset_name, item_name = get_doc_asset_item_name(doc_name)
                err_msg = (
                    f"Phase 2 Error for doc={doc_name}, asset_name={asset_name}, item_name={item_name}: {str(e)}"
                )
                append_log(doc_name, err_msg)
                error_records.append(err_msg)

        # =============================================================================
        # Phase 3: Update pre_use_link using pre_use_lookup
        # =============================================================================
        for doc_name in created_records + updated_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)
                matching_pre_use = frappe.get_all(
                    "Pre-Use Hours",
                    filters={"avail_util_lookup": doc.pre_use_lookup},
                    fields=["name"],
                    limit=1
                )
                if matching_pre_use:
                    doc.pre_use_link = matching_pre_use[0].name
                    doc.save(ignore_permissions=True)
                    append_log(
                        doc.name,
                        (
                            f"Phase 3: pre_use_link updated for doc={doc.name}, "
                            f"asset_name={doc.asset_name}, item_name={doc.item_name}"
                        )
                    )
                else:
                    append_log(
                        doc.name,
                        (
                            f"Phase 3: No matching Pre-Use Hours found for {doc.pre_use_lookup}. "
                            f"doc={doc.name}, asset_name={doc.asset_name}, item_name={doc.item_name}"
                        )
                    )
            except Exception as e:
                asset_name, item_name = get_doc_asset_item_name(doc_name)
                err_msg = (
                    f"Phase 3 Error for doc={doc_name}, asset_name={asset_name}, item_name={item_name}: {str(e)}"
                )
                append_log(doc_name, err_msg)
                error_records.append(err_msg)

        # =============================================================================
        # Phase 4: Update shift_required_hours
        # =============================================================================
        relevant_records = frappe.get_all(
            "Availability and Utilisation",
            filters={
                "shift_date": [">=", get_first_day(today())],
                "shift_date": ["<=", get_last_day(today())]
            },
            fields=["name", "shift_date", "location", "shift"]
        )
        for record in relevant_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", record.name)
                shift_date = getdate(doc.shift_date)
                location = doc.location
                planning_doc = frappe.get_all(
                    "Monthly Production Planning",
                    filters={
                        "prod_month_start_date": ["<=", shift_date],
                        "prod_month_end_date": [">=", shift_date],
                        "location": location
                    },
                    fields=["name"],
                    limit=1
                )
                if planning_doc:
                    planning_doc_name = planning_doc[0].name
                    planning_doc = frappe.get_doc("Monthly Production Planning", planning_doc_name)
                    month_prod_days = planning_doc.month_prod_days
                    for day in month_prod_days:
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
                            append_log(
                                doc.name,
                                (
                                    f"Phase 4: shift_required_hours updated for doc={doc.name}, "
                                    f"asset_name={doc.asset_name}, item_name={doc.item_name}"
                                )
                            )
                            break
            except Exception as e:
                asset_name, item_name = get_doc_asset_item_name(record["name"])
                err_msg = (
                    f"Phase 4 Error for doc={record['name']}, asset_name={asset_name}, "
                    f"item_name={item_name}: {str(e)}"
                )
                append_log(record["name"], err_msg)
                error_records.append(err_msg)

        # =============================================================================
        # Phase 5: Update from Pre-Use Hours
        # =============================================================================
        for doc_name in created_records + updated_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)
                pre_use_doc = frappe.get_all(
                    "Pre-Use Hours",
                    filters={"avail_util_lookup": doc.pre_use_lookup},
                    fields=["name"],
                    limit=1
                )
                if pre_use_doc:
                    pre_use_doc = frappe.get_doc("Pre-Use Hours", pre_use_doc[0].name)
                    for asset_row in pre_use_doc.pre_use_assets:
                        if asset_row.asset_name == doc.asset_name:
                            if asset_row.eng_hrs_start is not None:
                                doc.shift_start_hours = asset_row.eng_hrs_start
                            if asset_row.eng_hrs_end is not None:
                                doc.shift_end_hours = asset_row.eng_hrs_end
                            # --- New Update for pre_use_avail_status ---
                            if asset_row.pre_use_avail_status is not None:
                                doc.pre_use_avail_status = asset_row.pre_use_avail_status
                            # --- End of New Update ---                           
                            if (
                                doc.shift_start_hours is not None and
                                doc.shift_end_hours is not None
                            ):
                                doc.shift_working_hours = max(
                                    0, doc.shift_end_hours - doc.shift_start_hours
                                )
                            else:
                                doc.shift_working_hours = 0
                            doc.save(ignore_permissions=True)
                            append_log(
                                doc.name,
                                (
                                    f"Phase 5: Pre-Use Hours data applied for doc={doc.name}, "
                                    f"asset_name={doc.asset_name}, item_name={doc.item_name}"
                                )
                            )
                            break
            except Exception as e:
                asset_name, item_name = get_doc_asset_item_name(doc_name)
                err_msg = (
                    f"Phase 5 Error for doc={doc_name}, asset_name={asset_name}, item_name={item_name}: {str(e)}"
                )
                append_log(doc_name, err_msg)
                error_records.append(err_msg)

        # =============================================================================
        # Phase 6: Update item_name using asset lookup
        # =============================================================================
        for doc_name in created_records + updated_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)
                previous_item_name = doc.item_name
                asset_doc = frappe.get_all(
                    "Asset",
                    filters={"asset_name": doc.asset_name, "docstatus": 1},
                    fields=["item_name"],
                    limit=1
                )
                if asset_doc:
                    fetched_item_name = asset_doc[0].get("item_name")
                    if fetched_item_name != previous_item_name:
                        doc.item_name = fetched_item_name or None
                        doc.save(ignore_permissions=True)
                        append_log(
                            doc.name,
                            (
                                f"Phase 6: item_name updated for doc={doc.name}, "
                                f"previous_item_name={previous_item_name}, new_item_name={doc.item_name}, "
                                f"asset_name={doc.asset_name}"
                            )
                        )
            except Exception as e:
                asset_name, item_name = get_doc_asset_item_name(doc_name)
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
            filters=[
                ["shift_date", ">=", start_date],
                ["shift_date", "<=", current_date]
            ],
            fields=[
                "name", "shift_date", "shift", "shift_system",
                "location", "asset_name", "shift_breakdown_hours"
            ],
            order_by="creation desc"
        )

        for parent_record in parent_records:
            try:
                breakdown_history_rows = frappe.get_all(
                    "Breakdown History",
                    filters={
                        "location": parent_record["location"],
                        "asset_name": parent_record["asset_name"]
                    },
                    fields=["update_date_time", "breakdown_status"],
                    order_by="update_date_time"
                )
                if not breakdown_history_rows:
                    append_log(
                        parent_record["name"],
                        (
                            f"Phase 7: No breakdown history found for doc={parent_record['name']}, "
                            f"asset_name={parent_record['asset_name']}"
                        )
                    )
                    continue

                # 1) Determine shift start/end times
                shift_start, shift_end = get_shift_timings(
                    parent_record["shift_system"],
                    parent_record["shift"],
                    str(parent_record["shift_date"])
                )

                # 2) Derive breakdown_start/breakdown_end
                breakdown_start = breakdown_history_rows[0]["update_date_time"]
                breakdown_end = None
                for row in breakdown_history_rows:
                    if row["breakdown_status"] == "3":
                        breakdown_end = row["update_date_time"]

                # If there's no official 'end' record, assume breakdown continued to shift_end
                if not breakdown_end:
                    breakdown_end = shift_end

                # 3) Calculate overlap & scenario
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

                # 4) Cap the breakdown hours so that it does not exceed (shift_required_hours - shift_working_hours)
                doc = frappe.get_doc("Availability and Utilisation", parent_record["name"])
                # Ensure we have numbers (default to 0 if None)
                shift_required_hours = doc.shift_required_hours or 0
                shift_working_hours = doc.shift_working_hours or 0
                max_breakdown_allowed = max(shift_required_hours - shift_working_hours, 0)
                shift_breakdown_hours = min(shift_breakdown_hours, max_breakdown_allowed)

                # 5) Update the document in the database
                frappe.db.set_value(
                    "Availability and Utilisation",
                    parent_record["name"],
                    "shift_breakdown_hours",
                    shift_breakdown_hours
                )

                # 6) Log the scenario details
                append_log(
                    parent_record["name"],
                    (
                        f"Phase 7: shift_breakdown_hours updated for doc={parent_record['name']}. "
                        f"{scenario} => {shift_breakdown_hours} hour(s). "
                        f"(Shift Start: {shift_start}, Shift End: {shift_end}, "
                        f"Breakdown Start: {breakdown_start}, Breakdown End: {breakdown_end})"
                    )
                )
            except Exception as e:
                asset_name, item_name = get_doc_asset_item_name(parent_record["name"])
                err_msg = (
                    f"Phase 7 Error for doc={parent_record['name']}, "
                    f"asset_name={asset_name}, item_name={item_name}: {str(e)}"
                )
                append_log(parent_record["name"], err_msg)
                error_records.append(err_msg)
                
         # =============================================================================
        # Phase 8: Calculate and set final fields
        # =============================================================================
        for doc_name in created_records + updated_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)

                # Retrieve or default to zero
                shift_required_hours = doc.shift_required_hours or 0
                shift_breakdown_hours = doc.shift_breakdown_hours or 0
                shift_working_hours = doc.shift_working_hours or 0

                # --- Amendment: Check pre_use_avail_status ---
                if doc.pre_use_avail_status in ("3", "6"):
                    shift_required_hours = 0
                    shift_available_hours = shift_working_hours
                    shift_other_lost_hours = 0
                else:
                    # Calculate shift_available_hours normally
                    shift_available_hours = max(shift_required_hours - shift_breakdown_hours, 0)
                    # New SHIFT_OTHER_LOST_HOURS formula
                    if shift_working_hours > shift_available_hours:
                        shift_other_lost_hours = max(shift_required_hours - shift_working_hours, 0)
                    else:
                        shift_other_lost_hours = max(shift_available_hours - shift_working_hours, 0)

                # Update the document fields with the computed values
                doc.shift_required_hours = shift_required_hours
                doc.shift_available_hours = shift_available_hours
                doc.shift_other_lost_hours = shift_other_lost_hours

                # Calculate the max value between shift_working_hours and shift_available_hours
                max_val = max(shift_working_hours, shift_available_hours)

                # --- Plant Shift Utilisation ---
                if max_val > 0:
                    doc.plant_shift_utilisation = (shift_working_hours / max_val) * 100
                else:
                    doc.plant_shift_utilisation = 0

                # --- Plant Shift Availability ---
                # Default to 100% if pre_use_avail_status is "3" or "6"
                if doc.pre_use_avail_status in ("3", "6"):
                    doc.plant_shift_availability = 100
                else:
                    if shift_required_hours > 0:
                        doc.plant_shift_availability = (max_val / shift_required_hours) * 100
                    else:
                        doc.plant_shift_availability = 0

                doc.save(ignore_permissions=True)

                append_log(
                    doc.name,
                    (
                        f"Phase 8: Final fields updated for doc={doc.name}, asset_name={doc.asset_name}, "
                        f"item_name={doc.item_name}. "
                        f"(shift_required_hours={shift_required_hours}, "
                        f"shift_breakdown_hours={shift_breakdown_hours}, "
                        f"shift_working_hours={shift_working_hours}, "
                        f"shift_available_hours={shift_available_hours}, "
                        f"shift_other_lost_hours={shift_other_lost_hours}, "
                        f"plant_shift_utilisation={doc.plant_shift_utilisation}, "
                        f"plant_shift_availability={doc.plant_shift_availability})"
                    )
                )

            except Exception as e:
                asset_name, item_name = get_doc_asset_item_name(doc_name)
                err_msg = (
                    f"Phase 8 Error for doc={doc_name}, asset_name={asset_name}, item_name={item_name}: {str(e)}"
                )
                append_log(doc_name, err_msg)
                error_records.append(err_msg)

        # =============================================================================
        # Phase 9: Final Combined Log (Split into 10 Parts)
        # =============================================================================
        record_keys = list(record_logs.keys())
        total_logs = len(record_keys)
        max_logs_per_entry = max(1, total_logs // 10)

        for i in range(0, total_logs, max_logs_per_entry):
            batch_keys = record_keys[i:i + max_logs_per_entry]
            batch_messages = []

            for key in batch_keys:
                summary_message = f"{key}: " + " | ".join(record_logs[key])
                batch_messages.append(summary_message)

            combined_message = "\n".join(batch_messages)
            log_title = f"Phase Update Log - Batch {i // max_logs_per_entry + 1}"
            frappe.log_error(combined_message, log_title)

        # =============================================================================
        # Phase 10: Final Summary Log
        # =============================================================================
        success_message = (
            f"Successfully created {len(created_records)} records. "
            f"Updated {len(updated_records)} records. "
        )
        if error_records:
            success_message += (
                f"Errors encountered: {len(error_records)}. "
                "Check log batches for details."
            )

        frappe.log_error(success_message, "Process Completion")
        return success_message


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


@frappe.whitelist()
def create_availability_and_utilisation():
    """Manual trigger to run the generation of records."""
    result_message = AvailabilityandUtilisation.generate_records()
    return result_message


@frappe.whitelist()
def run_daily():
    """Scheduled daily job."""
    frappe.log_error("Scheduled job started at 05:40 AM for Availability and Utilisation", "Daily Job Start")
    AvailabilityandUtilisation.generate_records()
    frappe.log_error("Scheduled job completed for Availability and Utilisation", "Daily Job Completion")
