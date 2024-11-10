# Copyright (c) 2024, BuFf0k and contributors
# For license information, please see license.txt

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

    # Loop over each date from start_date to end_date
    current_date = start_date
    while current_date <= end_date:
        # Skip Sundays
        if current_date.weekday() != 6:  # 6 represents Sunday
            # Format the date as yyyy-MM-dd (database-compatible format)
            shift_date = current_date.strftime("%Y-%m-%d")
            
            # Retrieve all production sites with site_status 'Producing'
            producing_sites = frappe.get_all("Production Sites", filters={"site_status": "Producing"}, fields=["name"])

            for site in producing_sites:
                # Get assets linked to the current production site
                assets = frappe.get_all("Asset", filters={"location": site["name"]}, fields=["name"])

                # For each asset, create records for both shifts "A" and "B"
                for asset in assets:
                    for shift in ["A", "B"]:
                        # Check if the document already exists
                        if not frappe.db.exists("Availability and Utilisation", {
                            "asset_name": asset["name"],
                            "shift_date": shift_date,
                            "shift": shift
                        }):
                            # Create the new Availability and Utilisation document
                            doc = frappe.get_doc({
                                "doctype": "Availability and Utilisation",
                                "production_site": site["name"],
                                "shift_date": shift_date,
                                "shift": shift,
                                "asset_name": asset["name"],
                                "pre_use_link": None  # Optional, set if needed
                            })
                            doc.insert(ignore_permissions=True)
                            created_records.append(doc.name)
        
        # Move to the next day
        current_date = add_days(current_date, 1)
    
    frappe.db.commit()
    return created_records  # Return the list of created document names

class AvailabilityandUtilisation(Document):
	pass