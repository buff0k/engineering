import frappe
from frappe.model.document import Document
from frappe import throw, _
from datetime import datetime

class PlantBreakdown(Document):
    def before_save(self):
        # Track changes to breakdown_history
        self.track_history_changes()

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

    def fields_have_changed(self, previous_doc):
        """Check if any relevant fields in the main document have changed."""
        if not previous_doc:
            return True  # If there's no previous document, treat as changed

        # List of fields to track for changes in the main document
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

    def track_history_changes(self):
        """Track changes to the breakdown_history table and log them."""
        previous_doc = self.get_doc_before_save()
        previous_history = previous_doc.breakdown_history if previous_doc else []
        current_history = self.breakdown_history

        # Detect changes
        added = [row for row in current_history if row.name not in [p.name for p in previous_history]]
        removed = [row for row in previous_history if row.name not in [c.name for c in current_history]]
        updated = [
            {"old": prev_row, "new": curr_row}
            for prev_row in previous_history
            for curr_row in current_history
            if prev_row.name == curr_row.name and self.row_changed(prev_row, curr_row)
        ]

        # Recalculate timeclock if update_date_time has changed
        if any(self.row_changed(prev_row, curr_row) and "update_date_time" in self.get_changed_fields(prev_row, curr_row)
               for prev_row, curr_row in [(u["old"], u["new"]) for u in updated]):
            self.calculate_timeclock()

        # Construct log message
        log_entries = []

        # Log added rows
        for row in added:
            log_entries.append({"action": "Added", "details": row.as_dict()})

        # Log removed rows
        for row in removed:
            log_entries.append({"action": "Removed", "details": row.as_dict()})

        # Log updated rows
        for change in updated:
            changes = self.get_changed_fields(change["old"], change["new"])
            details = {field: {"before": getattr(change["old"], field), "after": getattr(change["new"], field)} for field in changes}
            log_entries.append({"action": "Updated", "details": details})

        # Append to history change log in simplified table format
        if log_entries:
            current_time = frappe.utils.now_datetime()
            user = frappe.session.user
            log_table = self.format_log_table(current_time, user, log_entries)
            self.history_change_log = (self.history_change_log or "") + log_table

    def format_log_table(self, timestamp, user, log_entries):
        """Format change log as an HTML table."""
        table = f"""
        <table border="1" style="width:100%;border-collapse:collapse;">
            <thead>
                <tr>
                    <th>Timestamp, User, Action</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
        """
        for log in log_entries:
            details_html = "<br>".join([f"{field}: {values['before']} → {values['after']}" for field, values in log.get("details", {}).items()])
            table += f"""
                <tr>
                    <td>{timestamp}<br>{user}<br>{log['action']}</td>
                    <td>{details_html}</td>
                </tr>
            """
        table += "</tbody></table>"
        return table

    def row_changed(self, old_row, new_row):
        """Check if a row has changed."""
        fields_to_check = [
            "update_by", "update_date_time", "location", 
            "asset_name", "breakdown_reason_updates", 
            "breakdown_status", "breakdown_start_hours"
        ]
        for field in fields_to_check:
            if getattr(old_row, field) != getattr(new_row, field):
                return True
        return False

    def get_changed_fields(self, old_row, new_row):
        """Get a list of fields that have changed."""
        changed_fields = []
        fields_to_check = [
            "update_by", "update_date_time", "location", 
            "asset_name", "breakdown_reason_updates", 
            "breakdown_status", "breakdown_start_hours"
        ]
        for field in fields_to_check:
            if getattr(old_row, field) != getattr(new_row, field):
                changed_fields.append(field)
        return changed_fields

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

    def calculate_timeclock(self):
        """Calculate the total time difference between the first and last rows."""
        if not self.breakdown_history or len(self.breakdown_history) < 2:
            return  # Skip calculation if no rows or only one row exists

        first_entry = self.breakdown_history[0]
        last_entry = self.breakdown_history[-1]

        try:
            # Validate and parse update_date_time for first and last entries
            first_time = self.parse_datetime_field(first_entry.update_date_time, "First Entry")
            last_time = self.parse_datetime_field(last_entry.update_date_time, "Last Entry")

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
                message=f"Error: {str(e)}"
            )
            last_entry.timeclock = "Error calculating timeclock"

    def parse_datetime_field(self, value, label):
        """Parse and validate a datetime field."""
        if not value:
            raise ValueError(f"{label} - update_date_time is missing.")
        try:
            # Check if value is already a datetime object
            if isinstance(value, datetime):
                return value
            # Parse datetime string
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            # Attempt parsing without milliseconds if necessary
            try:
                return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError as e:
                raise ValueError(f"{label} - Invalid date format: {value}. Error: {str(e)}")
