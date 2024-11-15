import frappe
from frappe.utils import getdate, add_days, today, formatdate
from datetime import timedelta
from frappe.model.document import Document

class AvailabilityandUtilisation(Document):
    @staticmethod
    def generate_records():
        created_records = []
        error_records = []
        current_date = getdate(today())

        # Log the start of the record generation process
        frappe.log_error("Starting record generation for Availability and Utilisation", "Process Start")

        # Phase 1: Create Availability and Utilisation documents
        production_planning_records = frappe.get_all("Monthly Production Planning",
                                                     filters={"site_status": "Producing"},
                                                     fields=["location", "prod_month_end", "shift_system"])

        for planning_record in production_planning_records:
            location = planning_record.location
            prod_month_end = getdate(planning_record.prod_month_end)
            shift_system = planning_record.shift_system

            # Get assets linked to the location with specific categories and status "Submitted"
            assets = frappe.get_all("Asset", filters={
                "location": location,
                "asset_category": ["in", ["Dozer", "ADT", "Rigid", "Excavator"]],
                "status": "Submitted"
            }, fields=["name", "asset_name"])

            start_date = prod_month_end.replace(day=1)
            end_date = min(prod_month_end, current_date - timedelta(days=1))
            date = start_date

            while date <= end_date:
                if date.weekday() == 6:  # Skip Sundays
                    date = add_days(date, 1)
                    continue

                shifts = ["A", "B"] if shift_system == "2x12Hour" else ["A", "B", "C"]

                for shift in shifts:
                    for asset in assets:
                        try:
                            doc = frappe.get_doc({
                                "doctype": "Availability and Utilisation",
                                "shift_date": date,
                                "shift": shift,  # Use "A", "B", or "C"
                                "asset_name": asset.asset_name,
                                "location": location,
                                "pre_use_lookup": None,  # Initially set to None
                                "pre_use_link": None     # Initially set to None
                            })
                            doc.insert(ignore_permissions=True)
                            created_records.append(doc.name)
                        except Exception as e:
                            error_message = f"Error creating document on {date} - Shift {shift} for Asset {asset.asset_name} at {location}: {str(e)}"
                            frappe.log_error(error_message, "Avail. & Util. Creation Error")
                            error_records.append(error_message)

                date = add_days(date, 1)

        # Phase 2: Update pre_use_lookup field
        for doc_name in created_records:
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
        for doc_name in created_records:
            try:
                doc = frappe.get_doc("Availability and Utilisation", doc_name)

                # Match the pre_use_lookup with avail_util_lookup in Pre-Use Hours
                matching_pre_use = frappe.get_all("Pre-Use Hours", filters={
                    "avail_util_lookup": doc.pre_use_lookup,
                }, fields=["name"], limit=1)

                if matching_pre_use:
                    doc.pre_use_link = matching_pre_use[0].name
                    doc.save(ignore_permissions=True)
                    frappe.log_error(f"Updated pre_use_link for {doc.name} to {matching_pre_use[0].name}", "Pre-Use Link Updated")
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
        success_message = f"Successfully created {len(created_records)} records."
        if error_records:
            success_message += "\nErrors encountered. Check the error log for details."

        frappe.log_error(success_message, "Process Completion")

        return success_message

# Button handler function that calls the generate_records method
@frappe.whitelist()
def create_availability_and_utilisation():
    result_message = AvailabilityandUtilisation.generate_records()
    return result_message
