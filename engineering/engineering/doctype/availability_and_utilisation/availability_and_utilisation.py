import frappe
from frappe.model.document import Document
from frappe.utils import add_days, nowdate, getdate

class AvailabilityandUtilisation(Document):
    pass

@frappe.whitelist()
def create_availability_and_utilisation():
    # Define the starting date
    start_date = getdate("2024-11-01")
    today = getdate(nowdate())
    end_date = add_days(today, -1)  # Set end date to yesterday
    
    created_records = []
    updated_records = []

    # Loop over each date from start_date to end_date
    current_date = start_date
    while current_date <= end_date:
        # Skip Sundays
        if current_date.weekday() != 6:  # 6 represents Sunday
            # Format the date as yyyy-MM-dd (database-compatible format)
            shift_date = current_date.strftime("%Y-%m-%d")
            
            # Retrieve all production sites with site_status "Producing"
            producing_sites = frappe.get_all("Production Sites", filters={"site_status": "Producing"}, fields=["name"])

            for site in producing_sites:
                # Get assets linked to the current production site with specified categories and status "Submitted"
                assets = frappe.get_all("Asset", filters={
                    "location": site["name"],
                    "asset_category": ["in", ["Dozer", "ADT", "Rigid", "Excavator"]],
                    "status": "Submitted"
                }, fields=["name", "asset_name"])

                # For each asset, create records for both shifts "A" and "B"
                for asset in assets:
                    for shift in ["A", "B"]:
                        # Check if the document already exists
                        doc_exists = frappe.db.exists("Availability and Utilisation", {
                            "asset_name": asset["asset_name"],
                            "shift_date": shift_date,
                            "shift": shift
                        })
                        
                        # Fetch matching "Pre-Use Hours" document if it exists
                        pre_use_link_doc = frappe.get_all("Pre-Use Hours", filters={
                            "location": site["name"],
                            "shift_date": shift_date,
                            "shift": shift,
                            "docstatus": 1  # Only fetch submitted documents
                        }, fields=["name"], limit=1)
                        pre_use_link = pre_use_link_doc[0]["name"] if pre_use_link_doc else None
                        
                        if doc_exists:
                            # Update existing document with pre_use_link if missing
                            existing_doc = frappe.get_doc("Availability and Utilisation", doc_exists)
                            if not existing_doc.pre_use_link and pre_use_link:
                                existing_doc.pre_use_link = pre_use_link
                                existing_doc.save(ignore_permissions=True)
                                updated_records.append(existing_doc.name)
                        else:
                            # Create a new Availability and Utilisation document
                            try:
                                doc = frappe.get_doc({
                                    "doctype": "Availability and Utilisation",
                                    "production_site": site["name"],
                                    "location": site["name"],
                                    "shift_date": shift_date,
                                    "shift": shift,
                                    "asset_name": asset["asset_name"],
                                    "pre_use_link": pre_use_link  # Set pre_use_link if available
                                })
                                doc.insert(ignore_permissions=True)
                                created_records.append(doc.name)
                            except Exception as e:
                                # Log the error if the document creation fails
                                frappe.log_error(f"Error creating Availability and Utilisation for asset {asset['asset_name']} on {shift_date}, shift {shift}: {str(e)}")

        # Move to the next day
        current_date = add_days(current_date, 1)

    try:
        frappe.db.commit()  # Commit the database transactions
    except Exception as e:
        # Log an error if commit fails
        frappe.log_error(f"Database commit failed: {str(e)}")
        return "Error: Database commit failed"

    return {
        "created_records": created_records,
        "updated_records": updated_records
    }  # Return the list of created and updated document names
