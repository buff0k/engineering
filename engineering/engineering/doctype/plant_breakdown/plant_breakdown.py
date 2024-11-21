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
            self.update_breakdown_history(current_status)

        # Check all history rows if breakdown_status is changed to 3
        if current_status == '3':
            self.mark_history_as_closed()

        # Update the timeclock field in history
        self.update_timeclock()

    def update_breakdown_history(self, current_status):
        """Update the breakdown history child table."""
        now_date = frappe.utils.nowdate()
        now_time = frappe.utils.nowtime()
        user = frappe.session.user

        # Create a new history entry
        new_entry = {
            "update_by": user,
            "date": now_date,
            "time": now_time,
            "location": self.location,
            "asset_name": self.asset_name,
            "breakdown_reason_updates": self.breakdown_reason_updates or '',
            "breakdown_status": current_status,
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

    def mark_history_as_closed(self):
        """Mark all rows in the breakdown_history table as closed."""
        for entry in self.breakdown_history:
            entry.breakdown_closed = 1

    def update_timeclock(self):
        """Update the timeclock field in the breakdown_history table."""
        if len(self.breakdown_history) < 2:
            return  # No calculation needed for fewer than 2 rows

        try:
            # Parse date and time from the first and last rows
            first_entry = self.breakdown_history[0]
            last_entry = self.breakdown_history[-1]

            first_datetime = datetime.strptime(f"{first_entry.date} {first_entry.time}", '%Y-%m-%d %H:%M:%S.%f')
            last_datetime = datetime.strptime(f"{last_entry.date} {last_entry.time}", '%Y-%m-%d %H:%M:%S.%f')

            # Calculate duration in hours
            duration = (last_datetime - first_datetime).total_seconds() / 3600
            duration = round(duration, 2)  # Round to 2 decimal places

            # Update the timeclock field for all rows
            for entry in self.breakdown_history:
                entry.timeclock = duration
        except ValueError as e:
            frappe.log_error(
                title="Timeclock Calculation Error",
                message=f"Error: {str(e)}, First Entry: {first_entry}, Last Entry: {last_entry}"
            )
