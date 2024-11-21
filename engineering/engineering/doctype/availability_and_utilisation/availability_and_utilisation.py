import frappe
from frappe.utils import getdate, today, add_days, formatdate
from datetime import timedelta
from frappe.model.document import Document

class AvailabilityandUtilisation(Document):
    @staticmethod
    def generate_records():
        created_records = []
        updated_records = []
        error_records = []

        # Calculate the date range: last 5 days up to today
        current_date = getdate(today())
        start_date = add_days(current_date, -5)
        end_date = current_date

        # Log the start of the record generation process
        frappe.log_error("Starting record generation for Availability and Utilisation", "Process Start")

        # Phase 1: Create or Update Availability and Utilisation documents
        production_planning_records = frappe.get_all(
            "Monthly Production Planning",
            filters={"site_status": "Producing"},
            fields=["location", "shift_system"]
        )

        for planning_record in production_planning_records:
            location = planning_record.location
            shift_system = planning_record.shift_system

            # Iterate through the date range
            date = start_date
            while date <= end_date:
                if date.weekday() == 6:  # Skip Sundays
                    date = add_days(date, 1)
                    continue

                # Determine shifts based on the shift system
                shifts = ["Day", "Night"] if shift_system == "2x12Hour" else ["Morning", "Afternoon", "Night"]

                for shift in shifts:
                    # Fetch assets for the location
                    assets = frappe.get_all(
                        "Asset",
                        filters={
                            "location": location,
                            "asset_category": ["in", ["Dozer", "ADT", "Rigid", "Excavator"]],
                            "status": "Submitted"
                        },
                        fields=["name", "asset_name"]
                    )

                    for asset in assets:
                        try:
                            # Check if the record already exists
                            existing_record = frappe.get_all(
                                "Availability and Utilisation",
                                filters={
                                    "shift_date": date,
                                    "location": location,
                                    "shift": shift,
                                    "asset_name": asset.asset_name
                                },
                                fields=["name"],
                                limit=1
                            )

                            if existing_record:
                                # Update the existing record
                                doc = frappe.get_doc("Availability and Utilisation", existing_record[0].name)
                                doc.pre_use_lookup = None  # Reset if needed
                                doc.pre_use_link = None
                                doc.save(ignore_permissions=True)
                                updated_records.append(doc.name)
                            else:
                                # Create a new record
                                doc = frappe.get_doc({
                                    "doctype": "Availability and Utilisation",
                                    "shift_date": date,
                                    "shift": shift,
                                    "asset_name": asset.asset_name,
                                    "location": location,
                                    "pre_use_lookup": None,
                                    "pre_use_link": None
                                })
                                doc.insert(ignore_permissions=True)
                                created_records.append(doc.name)
                        except Exception as e:
                            error_message = f"Error processing document on {date} - Shift {shift} for Asset {asset.asset_name} at {location}: {str(e)}"
                            frappe.log_error(error_message, "Avail. & Util. Processing Error")
                            error_records.append(error_message)

                date = add_days(date, 1)

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

        # Log completion message
        success_message = (
            f"Successfully created {len(created_records)} records. "
            f"Updated {len(updated_records)} records."
        )
        if error_records:
            success_message += "\nErrors encountered. Check the error log for details."

        frappe.log_error(success_message, "Process Completion")

        return success_message

# Button handler function that calls the generate_records method
@frappe.whitelist()
def create_availability_and_utilisation():
    result_message = AvailabilityandUtilisation.generate_records()
    return result_message
