import frappe
from frappe.model.document import Document
from frappe import throw, _
from datetime import datetime

class PlantBreakdown(Document):
    def before_save(self):
        # Ensure current breakdown_status is treated as a string
        current_status = str(self.breakdown_status) if self.breakdown_status else None
        previous_status = None

        # Fetch the previous document state, if it exists
        previous_doc = self.get_doc_before_save()
        if previous_doc:
            previous_status = str(previous_doc.breakdown_status) if previous_doc.breakdown_status else None

        # Validation for the first save
        if self.is_new():
            if current_status != '1':
                throw(_("When the document is saved for the first time, breakdown_status must be 1."))

        # Validation for subsequent saves
        else:
            if previous_status == '1' and current_status not in ['1', '2']:
                throw(_("Breakdown_status can only be changed from 1 to 2 or left at 1."))
            if previous_status == '2' and current_status not in ['2', '3']:
                throw(_("Breakdown_status can only be changed from 2 to 3 or left at 2."))
            if previous_status == '3':
                throw(_("The document is locked and cannot be edited once breakdown_status is 3."))

        # Update breakdown history if any field changes
        if self.fields_have_changed(previous_doc):
            self.append_breakdown_history(current_status)

        # Automatically mark all breakdown_resolved fields as checked if changing to status '3'
        if current_status == '3':
            for entry in self.breakdown_history:
                entry.breakdown_resolved = 1

        # Calculate timeclock
        self.calculate_timeclock()

    def append_breakdown_history(self, current_status):
        """Append a new entry to the breakdown history child table."""
        current_timestamp = frappe.utils.now_datetime()
        user = frappe.session.user

        # Create a new history entry with all required fields
        new_entry = {
            "update_by": user,
            "update_date_time": current_timestamp,
            "location": self.location,
            "asset_name": self.asset_name,
            "breakdown_reason_updates": self.breakdown_reason_updates or '',
            "breakdown_status": current_status,
            "breakdown_start_hours": self.hours_breakdown_start or 0,
        }

        # Append the new entry to the child table
        self.append("breakdown_history", new_entry)

    def fields_have_changed(self, previous_doc):
        """Check if any relevant fields have changed."""
        if not previous_doc:
            return True  # If there's no previous document, treat as changed

        # List of fields to track for changes
        fields_to_check = [
            "location", "asset_name", "breakdown_status",
            "breakdown_reason_updates", "hours_breakdown_start"
        ]

        for field in fields_to_check:
            previous_value = getattr(previous_doc, field, None)
            current_value = getattr(self, field, None)
            if previous_value != current_value:
                return True

        return False

    def calculate_timeclock(self):
        """Calculate the total time difference between the first and last rows."""
        if not self.breakdown_history or len(self.breakdown_history) < 2:
            return  # Skip calculation if no rows or only one row exists

        first_entry = self.breakdown_history[0]
        last_entry = self.breakdown_history[-1]

        try:
            # Handle cases where update_date_time might be a string or datetime object
            first_time = (
                first_entry.update_date_time 
                if isinstance(first_entry.update_date_time, datetime) 
                else datetime.strptime(first_entry.update_date_time, '%Y-%m-%d %H:%M:%S.%f')
            )
            last_time = (
                last_entry.update_date_time 
                if isinstance(last_entry.update_date_time, datetime) 
                else datetime.strptime(last_entry.update_date_time, '%Y-%m-%d %H:%M:%S.%f')
            )

            total_duration = last_time - first_time

            # Calculate days, hours, and minutes
            days = total_duration.days
            hours, remainder = divmod(total_duration.seconds, 3600)
            minutes = remainder // 60

            # Construct the timeclock value in days, hours, and minutes
            timeclock_value = f"{days} day{'s' if days != 1 else ''}, {hours} hour{'s' if hours != 1 else ''}, {minutes} minute{'s' if minutes != 1 else ''}"
            last_entry.timeclock = timeclock_value
        except Exception as e:
            # Log an error if there's an issue
            frappe.log_error(
                title="Date-Time Parsing Error in Timeclock Calculation",
                message=f"Error: {str(e)}, First Entry: {first_entry.update_date_time}, Last Entry: {last_entry.update_date_time}"
            )
            last_entry.timeclock = "Error calculating timeclock"
