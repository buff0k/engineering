import frappe
from frappe.utils import getdate, add_days, today, formatdate, get_first_day, get_last_day, time_diff_in_hours, get_datetime
from datetime import timedelta
from frappe.model.document import Document


class AvailabilityandUtilisation(Document):
    @staticmethod
    def generate_records():
        created_records = []
        updated_records = []
        error_records = []
        current_date = getdate(today())

        # Log the start of the record generation process
        frappe.log_error("Starting record generation for Availability and Utilisation", "Process Start")

        # Phase 1: Create or Update Availability and Utilisation documents for the last 7 days
        production_planning_records = frappe.get_all(
            "Monthly Production Planning",
            filters={
                "site_status": "Producing",
                "prod_month_end": [">=", get_first_day(current_date - timedelta(days=7))],
                "prod_month_end": ["<=", get_last_day(current_date)],
            },
            fields=["location", "prod_month_end", "shift_system"],
            order_by="prod_month_end asc",  # Ensure earlier records are processed first
        )

        start_date = current_date - timedelta(days=7)
        end_date = current_date

        # Iterate through each day in the last 7 days
        date = start_date
        while date <= end_date:
            for planning_record in production_planning_records:
                location = planning_record.location
                shift_system = planning_record.shift_system
                prod_month_end = planning_record.prod_month_end

                # Ensure this planning record applies to the current date
                if getdate(date) <= getdate(prod_month_end):
                    frappe.log_error(
                        f"Date: {date}, Location: {location}, Using Shift System: {shift_system}, Prod Month-End: {prod_month_end}",
                        "Date-Specific Shift System Match",
                    )

                    # Fetch assets for the location
                    assets = frappe.get_all(
                        "Asset",
                        filters={
                            "location": location,
                            "asset_category": ["in", ["Dozer", "ADT", "Rigid", "Excavator"]],
                            "docstatus": 1,
                        },
                        fields=["name", "asset_name"],
                    )

                    # Determine shifts based on the applicable shift system
                    shifts = ["Day", "Night"] if shift_system.strip().lower() == "2x12hour" else ["Morning", "Afternoon", "Night"]

                    frappe.log_error(
                        f"Date: {date}, Location: {location}, Shifts: {shifts}",
                        "Shift Determination Debug",
                    )

                    # Create or update records for each shift
                    for shift in shifts:
                        for asset in assets:
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
                                    # Update the existing record
                                    doc = frappe.get_doc("Availability and Utilisation", existing_record[0].name)
                                    doc.pre_use_lookup = None  # Reset if needed
                                    doc.pre_use_link = None
                                    doc.save(ignore_permissions=True)
                                    updated_records.append(doc.name)

                                    frappe.log_error(
                                        f"Updated Record: {doc.name}, Shift: {shift}, Date: {date}, Location: {location}",
                                        "Record Update Debug",
                                    )
                                else:
                                    # Create a new record
                                    doc = frappe.get_doc({
                                        "doctype": "Availability and Utilisation",
                                        "shift_date": date,
                                        "shift": shift,
                                        "asset_name": asset.asset_name,
                                        "location": location,
                                        "shift_system": shift_system,
                                        "pre_use_lookup": None,
                                        "pre_use_link": None,
                                    })
                                    doc.insert(ignore_permissions=True)
                                    created_records.append(doc.name)

                                    frappe.log_error(
                                        f"Created Record: {doc.name}, Shift: {shift}, Date: {date}, Location: {location}",
                                        "Record Creation Debug",
                                    )
                            except Exception as e:
                                error_message = (
                                    f"Error processing document on {date} - Shift {shift} for Asset {asset.asset_name} at {location}: {str(e)}"
                                )
                                frappe.log_error(error_message, "Avail. & Util. Processing Error")
                                error_records.append(error_message)
                    break  # Exit loop after processing the matching planning record

            date = add_days(date, 1)  # Move to the next day

        # Phase 2: Update pre_use_lookup field
        for doc_name in created_records + updated_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)
                formatted_date = formatdate(doc.shift_date, "dd-mm-yyyy")
                doc.pre_use_lookup = f"{doc.location}-{formatted_date}-{doc.shift}"
                doc.save(ignore_permissions=True)
            except Exception as e:
                error_message = f"Error updating pre_use_lookup for document {doc_name}: {str(e)}"
                frappe.log_error(error_message, "Pre-Use Lookup Update Error")
                error_records.append(error_message)

        # Phase 3: Use pre_use_lookup to update pre_use_link
        for doc_name in created_records + updated_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)

                # Match the pre_use_lookup with avail_util_lookup in Pre-Use Hours
                matching_pre_use = frappe.get_all(
                    "Pre-Use Hours",
                    filters={"avail_util_lookup": doc.pre_use_lookup},
                    fields=["name"],
                    limit=1
                )

                if matching_pre_use:
                    doc.pre_use_link = matching_pre_use[0].name
                    doc.save(ignore_permissions=True)
                else:
                    frappe.log_error(
                        f"No matching Pre-Use Hours found for pre_use_lookup: {doc.pre_use_lookup}",
                        "Pre-Use Link Not Found"
                    )

            except Exception as e:
                error_message = f"Error updating pre_use_link for document {doc_name}: {str(e)}"
                frappe.log_error(error_message, "Pre-Use Link Update Error")
                error_records.append(error_message)

        # Phase 4: Update shift_required_hours for all relevant records
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

                # Find the corresponding Monthly Production Planning document
                planning_doc = frappe.get_all(
                    "Monthly Production Planning",
                    filters={
                        "prod_month_end": [">=", get_first_day(shift_date)],
                        "prod_month_end": ["<=", get_last_day(shift_date)],
                        "location": location
                    },
                    fields=["name"],
                    limit=1
                )

                if planning_doc:
                    planning_doc_name = planning_doc[0].name
                    planning_doc = frappe.get_doc("Monthly Production Planning", planning_doc_name)

                    # Access the month_prod_days child table
                    month_prod_days = planning_doc.month_prod_days

                    # Match the corresponding shift_start_date in the child table
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
                            break

            except Exception as e:
                error_message = f"Error updating shift_required_hours for record {record.name}: {str(e)}"
                frappe.log_error(error_message, "Shift Required Hours Update Error")
                error_records.append(error_message)

        # Phase 5: Use pre_use_lookup to update Availability and Utilisation from Pre-Use Hours
        for doc_name in created_records + updated_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)

                # Find the matching Pre-Use Hours document
                pre_use_doc = frappe.get_all(
                    "Pre-Use Hours",
                    filters={"avail_util_lookup": doc.pre_use_lookup},
                    fields=["name"],
                    limit=1
                )

                if pre_use_doc:
                    pre_use_doc = frappe.get_doc("Pre-Use Hours", pre_use_doc[0].name)

                    # Access the pre_use_assets child table
                    for asset_row in pre_use_doc.pre_use_assets:
                        if asset_row.asset_name == doc.asset_name:
                            # Update shift_start_hours and shift_end_hours in Availability and Utilisation
                            if asset_row.eng_hrs_start is not None:
                                doc.shift_start_hours = asset_row.eng_hrs_start
                            if asset_row.eng_hrs_end is not None:
                                doc.shift_end_hours = asset_row.eng_hrs_end

                            # Calculate and update shift_working_hours
                            if doc.shift_start_hours is not None and doc.shift_end_hours is not None:
                                doc.shift_working_hours = max(0, doc.shift_end_hours - doc.shift_start_hours)
                            else:
                                doc.shift_working_hours = 0

                            doc.save(ignore_permissions=True)
                            break

            except Exception as e:
                error_message = f"Error updating Availability and Utilisation for record {doc_name}: {str(e)}"
                frappe.log_error(error_message, "Availability & Utilisation Update Error")
                error_records.append(error_message)

        # Phase 6: Update item_name using asset_name as lookup, but only for submitted assets (docstatus = 1)
        for doc_name in created_records + updated_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)
                previous_item_name = doc.item_name  # Store the current item_name for comparison

                # Fetch the linked asset document using asset_name as the lookup field
                asset_doc = frappe.get_all(
                    "Asset",
                    filters={"asset_name": doc.asset_name, "docstatus": 1},
                    fields=["item_name"],
                    limit=1
                )

                if asset_doc:
                    asset_doc = asset_doc[0]  # Get the first result (as limit=1 ensures only one result)
                    fetched_item_name = asset_doc.get("item_name")  # Item name from Asset

                    if fetched_item_name != previous_item_name:
                        # Update the item_name only if it differs
                        doc.item_name = fetched_item_name or None
                        doc.save(ignore_permissions=True)

                        # Log the update
                        frappe.log_error(
                            f"Updated item_name for document {doc_name}. Previous: {previous_item_name}, Fetched: {fetched_item_name}",
                            "Item Name Updated"
                        )

            except Exception as e:
                error_message = (
                    f"Error updating item_name for document {doc_name}: {str(e)}. "
                    f"Previous item_name: {previous_item_name}, Asset Lookup item_name: {fetched_item_name}"
                )
                frappe.log_error(error_message, "Item Name Update Error")
                error_records.append(error_message)

        # Continue consistent indentation for the remaining phases...

        # Phase 7: Update shift_breakdown_hours
        parent_records = frappe.get_all(
            "Availability and Utilisation",
            filters={},
            fields=[
                "name", "shift_date", "shift", "shift_system",
                "location", "asset_name", "shift_breakdown_hours"
            ],
            order_by="creation desc",
            limit=21  # Process all records from the last 7 days
        )

        for parent_record in parent_records:
            try:
                # Fetch breakdown_history child table rows from Plant Breakdown
                breakdown_history_rows = frappe.get_all(
                    "Breakdown History",
                    filters={
                        "location": parent_record["location"],  # Match location in child table
                        "asset_name": parent_record["asset_name"]  # Match asset_name in child table
                    },
                    fields=["update_date_time", "breakdown_status"],
                    order_by="update_date_time"
                )

                if not breakdown_history_rows:
                    # Log that no breakdown history is available
                    frappe.log_error(
                        f"No breakdown history found for record {parent_record['name']}:\n"
                        f"Shift System: {parent_record['shift_system']}\n"
                        f"Shift: {parent_record['shift']}\n"
                        f"Shift Date: {parent_record['shift_date']} | Location: {parent_record['location']} | Asset: {parent_record['asset_name']}",
                        "No Breakdown History"
                    )
                    continue

                # Determine shift timings
                shift_start, shift_end = get_shift_timings(
                    parent_record["shift_system"], parent_record["shift"], str(parent_record["shift_date"])
                )

                # Initialize variables for breakdown hours calculation
                breakdown_start = breakdown_history_rows[0]["update_date_time"]  # First row is always breakdown_start
                breakdown_end = None  # To be determined

                # Identify breakdown_end
                for row in breakdown_history_rows:
                    if row["breakdown_status"] == "3":  # Breakdown resolved
                        breakdown_end = row["update_date_time"]

                # If no explicit breakdown_end (status 3), assume ongoing breakdown until shift_end
                if not breakdown_end:
                    breakdown_end = shift_end  # Treat as ongoing for the rest of the shift

                # Calculate shift breakdown hours
                shift_breakdown_hours = 0
                scenario = None

                # Ensure overlap exists before calculating breakdown hours
                if breakdown_start < shift_end and breakdown_end > shift_start:
                    if breakdown_start >= shift_start:
                        if breakdown_end <= shift_end:
                            # Scenario 3: Breakdown started and ended during the shift
                            shift_breakdown_hours = time_diff_in_hours(breakdown_end, breakdown_start)
                            scenario = "Scenario 3: Breakdown started and ended during the shift."
                        elif breakdown_end > shift_end:
                            # Scenario 4: Breakdown started during the shift and lasted for the rest of the shift
                            shift_breakdown_hours = time_diff_in_hours(shift_end, breakdown_start)
                            scenario = "Scenario 4: Breakdown started during the shift and lasted for the rest of the shift."
                    elif breakdown_start < shift_start:
                        if breakdown_end <= shift_end:
                            # Scenario 2: Breakdown started before the shift and ended during the shift
                            shift_breakdown_hours = time_diff_in_hours(breakdown_end, shift_start)
                            scenario = "Scenario 2: Breakdown started before and ended during the shift."
                        elif breakdown_end > shift_end:
                            # Scenario 1: Breakdown lasted the entire shift
                            shift_breakdown_hours = time_diff_in_hours(shift_end, shift_start)
                            scenario = "Scenario 1: Breakdown lasted the entire shift."
                else:
                    # No overlap between breakdown and shift
                    shift_breakdown_hours = 0
                    scenario = "No Breakdown During Shift"

                # Always update shift_breakdown_hours
                frappe.db.set_value(
                    "Availability and Utilisation", parent_record["name"], "shift_breakdown_hours", shift_breakdown_hours
                )

                # Log success
                log_message = (
                    f"Record: {parent_record['name']}:\n"
                    f"Shift System: {parent_record['shift_system']}\n"
                    f"Shift: {parent_record['shift']}\n"
                    f"Shift Start: {shift_start.strftime('%Y-%m-%d %H:%M:%S') if shift_start else 'None'}\n"
                    f"Shift End: {shift_end.strftime('%Y-%m-%d %H:%M:%S') if shift_end else 'None'}\n"
                    f"Breakdown Start: {breakdown_start.strftime('%Y-%m-%d %H:%M:%S') if breakdown_start else 'None'}\n"
                    f"Breakdown End: {breakdown_end.strftime('%Y-%m-%d %H:%M:%S') if breakdown_end else 'None'}\n"
                    f"Scenario: {scenario} | Shift Breakdown Hours Updated Successfully: {shift_breakdown_hours}"
                )
                frappe.log_error(log_message, "Phase 7 Update Success")

            except Exception as e:
                # Always log errors
                error_message = (
                    f"Error updating shift_breakdown_hours for record {parent_record['name']}:\n"
                    f"Shift System: {parent_record['shift_system']}\n"
                    f"Shift: {parent_record['shift']}\n"
                    f"Shift Date: {parent_record['shift_date']} | Location: {parent_record['location']} | Asset: {parent_record['asset_name']}\n"
                    f"Exception: {str(e)}"
                )
                frappe.log_error(error_message, "Shift Breakdown Hours Update Error")

        # Phase 8: Calculate and set shift_available_hours, plant_shift_utilisation, and plant_shift_availability
        for doc_name in created_records + updated_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)

                # Ensure shift_required_hours is non-zero to avoid division errors
                shift_required_hours = doc.shift_required_hours or 0
                shift_breakdown_hours = doc.shift_breakdown_hours or 0
                shift_working_hours = doc.shift_working_hours or 0

                # Calculate shift_available_hours
                shift_available_hours = max(shift_required_hours - shift_breakdown_hours, 0)
                doc.shift_available_hours = shift_available_hours

                # Calculate plant_shift_utilisation (as a percentage)
                if shift_required_hours > 0:
                    doc.plant_shift_utilisation = (shift_working_hours / shift_required_hours) * 100
                else:
                    doc.plant_shift_utilisation = 0  # Default to 0 if required hours are zero

                # Calculate plant_shift_availability (as a percentage)
                if shift_required_hours > 0:
                    doc.plant_shift_availability = (shift_available_hours / shift_required_hours) * 100
                else:
                    doc.plant_shift_availability = 0  # Default to 0 if required hours are zero

                # Save the updated fields
                doc.save(ignore_permissions=True)

                # Log success
                frappe.log_error(
                    f"Phase 8: Calculated and updated fields for {doc_name}:\n"
                    f"Shift Available Hours: {shift_available_hours}\n"
                    f"Plant Shift Utilisation: {doc.plant_shift_utilisation}\n"
                    f"Plant Shift Availability: {doc.plant_shift_availability}",
                    "Phase 8 Update Success"
                )

            except Exception as e:
                error_message = f"Error updating Phase 8 fields for document {doc_name}: {str(e)}"
                frappe.log_error(error_message, "Phase 8 Error")
                error_records.append(error_message)


        # Log completion message
        success_message = (
            f"Successfully created {len(created_records)} records. "
            f"Updated {len(updated_records)} records."
        )
        if error_records:
            success_message += "\nErrors encountered. Check the error log for details."

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
    result_message = AvailabilityandUtilisation.generate_records()
    return result_message

@frappe.whitelist()
def run_daily():
    # Run the availability and utilisation engine
    frappe.log_error("Scheduled job started at 05:40 AM for Availability and Utilisation", "Daily Job Start")
    AvailabilityandUtilisation.generate_records()
    frappe.log_error("Scheduled job completed for Availability and Utilisation", "Daily Job Completion")