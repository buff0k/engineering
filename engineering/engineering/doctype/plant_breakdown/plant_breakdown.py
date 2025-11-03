import frappe
from frappe.model.document import Document
from frappe import throw, _
from datetime import datetime

class PlantBreakdown(Document):
    def before_save(self):
        # 1) Prevent edits once locked at status '3'
        previous = self.get_doc_before_save()
        prev_status = str(previous.breakdown_status) if previous and previous.breakdown_status else None
        if prev_status == '3':
            throw(_("Cannot edit once breakdown_status is 3."))

        # 2) Log change events for audit (JS handles history row creation)
        self.track_history_changes()

        # 3) Validate status progression: new record must start at '1', then 1→2→3
        current_status = str(self.breakdown_status) if self.breakdown_status else None
        if self.is_new():
            if current_status != '1':
                throw(_("On first save, breakdown_status must be 1."))
        else:
            if prev_status == '1' and current_status not in ['1', '2']:
                throw(_("Can only change status 1→2 or stay at 1."))
            if prev_status == '2' and current_status not in ['2', '3']:
                throw(_("Can only change status 2→3 or stay at 2."))

        # 4) Mark resolved flags when final status is reached
        if current_status == '3':
            for entry in self.breakdown_history:
                entry.breakdown_resolved = 1

        # 5) Recalculate timeclocks on all history entries
        self.calculate_timeclock()

        # 6) Aggregate history entries into the parent reason field (no duplicate hours)
        if self.breakdown_history:
            lines = []
            for entry in self.breakdown_history:
                status = entry.breakdown_status
                timestamp = entry.update_date_time
                downtime_type = getattr(entry, 'downtime_type', 'Plant Breakdown')
                line = f"[{downtime_type}] Status {status} ({timestamp}): "

                # Only include start hours for the initial breakdown
                if status == '1' and entry.breakdown_start_hours is not None:
                    line += f"Start Hours: {entry.breakdown_start_hours} | "
                # Append the recorded reason
                if entry.breakdown_reason_updates:
                    line += entry.breakdown_reason_updates
                # Append timeclock if calculated
                if entry.timeclock:
                    line += f" [Timeclock: {entry.timeclock}]"
                lines.append(line)
            self.breakdown_reason_updates = "\n".join(lines)

    def track_history_changes(self):
        """Track add/remove/update events in breakdown_history for an audit log."""
        previous = self.get_doc_before_save()
        #  nothing to compare on a brand‐new doc
        if not previous:
            return
        old_rows = previous.breakdown_history if previous else []
        new_rows = self.breakdown_history

        old_ids = {r.name for r in old_rows}
        new_ids = {r.name for r in new_rows}
        added = [r for r in new_rows if r.name not in old_ids]
        removed = [r for r in old_rows if r.name not in new_ids]
        updated = [
            {'old': o, 'new': n}
            for o in old_rows for n in new_rows
            if o.name == n.name and self.row_changed(o, n)
        ]

        entries = []
        for r in added:
            entries.append({'action': 'Added', 'details': r.as_dict()})
        for r in removed:
            entries.append({'action': 'Removed', 'details': r.as_dict()})
        for u in updated:
            fields = self.get_changed_fields(u['old'], u['new'])
            details = {f: {'before': getattr(u['old'], f), 'after': getattr(u['new'], f)} for f in fields}
            entries.append({'action': 'Updated', 'details': details})

        if entries:
            ts = frappe.utils.now_datetime()
            user = frappe.session.user
            self.history_change_log = (self.history_change_log or '') + self.format_log_table(ts, user, entries)

    def format_log_table(self, timestamp, user, log_entries):
        """Format the history_change_log as an HTML table."""
        html = [
            '<table border="1" style="width:100%;border-collapse:collapse;">',
            '<thead><tr><th>Timestamp, User, Action</th><th>Details</th></tr></thead>',
            '<tbody>'
        ]
        for e in log_entries:
            details = []
            for fld, val in e['details'].items():
                if isinstance(val, dict) and 'before' in val and 'after' in val:
                    details.append(f"{fld}: {val['before']} → {val['after']}")
                else:
                    details.append(f"{fld}: {val}")
            html.append(f"<tr><td>{timestamp}<br>{user}<br>{e['action']}</td><td>{'<br>'.join(details)}</td></tr>")
        html.append('</tbody></table>')
        return ''.join(html)

    def row_changed(self, old_row, new_row):
        """Detect if any tracked field in a history row changed."""
        fields = [
            'update_by', 'update_date_time', 'location',
            'asset_name', 'breakdown_reason_updates',
            'breakdown_status', 'breakdown_start_hours'
        ]
        return any(getattr(old_row, f) != getattr(new_row, f) for f in fields)

    def get_changed_fields(self, old_row, new_row):
        """Return list of fields that differ between two history rows."""
        return [
            f for f in [
                'update_by', 'update_date_time', 'location',
                'asset_name', 'breakdown_reason_updates',
                'breakdown_status', 'breakdown_start_hours'
            ]
            if getattr(old_row, f) != getattr(new_row, f)
        ]

    def calculate_timeclock(self):
        """Compute elapsed time between first and last history entry."""
        if len(self.breakdown_history) < 2:
            return
        first = self.breakdown_history[0]
        last = self.breakdown_history[-1]
        try:
            t1 = self.parse_datetime_field(first.update_date_time, 'First Entry')
            t2 = self.parse_datetime_field(last.update_date_time, 'Last Entry')
            delta = t2 - t1
            days = delta.days
            hrs, rem = divmod(delta.seconds, 3600)
            mins = rem // 60
            last.timeclock = f"{days} day{'s' if days != 1 else ''}, {hrs} hour{'s' if hrs != 1 else ''}, {mins} minute{'s' if mins != 1 else ''}"
        except Exception as e:
            frappe.log_error(title='Timeclock Error', message=str(e))
            last.timeclock = 'Error calculating timeclock'

    def parse_datetime_field(self, value, label):
        """Parse a datetime string or object into a datetime."""
        if not value:
            raise ValueError(f"{label} - missing date-time")
        if isinstance(value, datetime):
            return value
        for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
            try:
                return datetime.strptime(value, fmt)
            except:
                pass
        raise ValueError(f"{label} - invalid format: {value}")
