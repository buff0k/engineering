# Copyright (c) 2025, Isambane Mining (Pty) Ltd
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime


class PlantBreakdownorMaintenance(Document):
    """Main doctype for recording equipment breakdowns or maintenance."""

    def before_save(self):
        """Run calculations and update logs before saving."""
        # 1) Calculate total breakdown hours
        self.calculate_breakdown_hours()

        # 2) Update text summary for dashboards or reports
        self.update_summary()

        # 3) Create or update Breakdown History entries
        self.update_breakdown_history()

    # -------------------------------------------------------------------------
    # CORE CALCULATIONS
    # -------------------------------------------------------------------------
    def calculate_breakdown_hours(self):
        """Compute duration between breakdown start and resolved time (in hours)."""
        if not self.breakdown_start_datetime or not self.resolved_datetime:
            self.breakdown_hours = 0
            return

        try:
            start = get_datetime(self.breakdown_start_datetime)
            end = get_datetime(self.resolved_datetime)
            if end < start:
                frappe.msgprint("Resolved time cannot be earlier than breakdown start.")
                self.breakdown_hours = 0
                return

            delta = end - start
            total_hours = round(delta.total_seconds() / 3600, 2)
            self.breakdown_hours = total_hours

        except Exception as e:
            frappe.log_error(
                f"Breakdown hours calculation failed: {str(e)}",
                "PlantBreakdownOrMaintenance"
            )
            self.breakdown_hours = 0

    def update_summary(self):
        """Update Breakdown Reason/Update text for reports or dashboards."""
        if self.breakdown_start_datetime and self.resolved_datetime:
            self.breakdown_reason_updates = (
                f"[Plant Breakdown or Maintenance] Started: {self.breakdown_start_datetime} | "
                f"Resolved: {self.resolved_datetime} | "
                f"Total Hours: {self.breakdown_hours}"
            )

    # -------------------------------------------------------------------------
    # BREAKDOWN HISTORY SYNC
    # -------------------------------------------------------------------------
    def update_breakdown_history(self):
        """Create or update Breakdown History entries so A&U can read downtime events."""

        # --- Step 1: Skip if no start date ---
        if not self.breakdown_start_datetime:
            return

        # --- Step 2: Ensure a 'Start' record (status 1) exists ---
        start_exists = frappe.db.exists(
            "Breakdown History",
            {
                "update_date_time": self.breakdown_start_datetime,
                "asset_name": self.asset_name,
                "location": self.location,
                "breakdown_status": "1",
            },
        )

        if not start_exists:
            frappe.get_doc({
                "doctype": "Breakdown History",
                "update_by": frappe.session.user,
                "update_date_time": self.breakdown_start_datetime,
                "location": self.location,
                "asset_name": self.asset_name,
                "breakdown_status": "1",
                "breakdown_reason_updates": self.breakdown_reason or "",
                "breakdown_start_hours": self.hours_breakdown_starts or 0,
                "timeclock": self.breakdown_hours or 0,
                "breakdown_resolved": 0,
                "exclude_from_au": self.exclude_from_au or 0,  # ✅ new field
            }).insert(ignore_permissions=True)

        # --- Step 3: If resolved time present, ensure a 'Resolved' record (status 3) exists ---
        if self.resolved_datetime:
            resolved_exists = frappe.db.exists(
                "Breakdown History",
                {
                    "update_date_time": self.resolved_datetime,
                    "asset_name": self.asset_name,
                    "location": self.location,
                    "breakdown_status": "3",
                },
            )

            if not resolved_exists:
                frappe.get_doc({
                    "doctype": "Breakdown History",
                    "update_by": frappe.session.user,
                    "update_date_time": self.resolved_datetime,
                    "location": self.location,
                    "asset_name": self.asset_name,
                    "breakdown_status": "3",
                    "breakdown_reason_updates": self.resolution_summary or "",
                    "breakdown_start_hours": self.hours_breakdown_starts or 0,
                    "timeclock": self.breakdown_hours or 0,
                    "breakdown_resolved": 1,
                    "exclude_from_au": self.exclude_from_au or 0,  # ✅ new field
                }).insert(ignore_permissions=True)
