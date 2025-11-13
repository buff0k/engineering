# Copyright (c) 2025, Isambane Mining (Pty) Ltd
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime


class PlantBreakdownorMaintenance(Document):
    """Main doctype for recording equipment breakdowns or maintenance."""

    # ---------------------------------------------------------------
    # EVENT HOOKS
    # ---------------------------------------------------------------
    def after_insert(self):
        """Run immediately after the document is created."""
        if self.exclude_from_au:
            self.breakdown_hours = 0
            frappe.msgprint("⚠️ This record is excluded from A&U downtime calculations.")
            self.update_breakdown_history()
            return

        # Calculate duration, update summary, and sync breakdown history
        self.calculate_breakdown_hours()
        self.update_summary()
        self.update_breakdown_history()

    # ---------------------------------------------------------------
    # CORE CALCULATIONS
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # BREAKDOWN HISTORY SYNC
    # ---------------------------------------------------------------
    def update_breakdown_history(self):
        """Create or update Breakdown History entries for A&U."""
        if not self.breakdown_start_datetime:
            return

        parent_name = self.name  # link to parent breakdown

        # --- START (Status 1) ---
        start_name = frappe.get_value(
            "Breakdown History",
            {"parent_breakdown": parent_name, "breakdown_status": "1"},
            "name"
        )

        if start_name:
            doc = frappe.get_doc("Breakdown History", start_name)
            doc.update({
                "update_date_time": self.breakdown_start_datetime,
                "breakdown_reason_updates": self.breakdown_reason or "",
                "exclude_from_au": self.exclude_from_au or 0,
                "location": self.location,
                "asset_name": self.asset_name,
                "timeclock": 0
            })
            doc.save(ignore_permissions=True)
        else:
            frappe.get_doc({
                "doctype": "Breakdown History",
                "parent_breakdown": parent_name,
                "update_by": frappe.session.user,
                "update_date_time": self.breakdown_start_datetime,
                "location": self.location,
                "asset_name": self.asset_name,
                "breakdown_status": "1",
                "breakdown_reason_updates": self.breakdown_reason or "",
                "breakdown_start_hours": self.hours_breakdown_starts or 0,
                "timeclock": 0,
                "breakdown_resolved": 0,
                "exclude_from_au": self.exclude_from_au or 0
            }).insert(ignore_permissions=True)

        # --- RESOLVED (Status 3) ---
        if self.resolved_datetime:
            resolved_name = frappe.get_value(
                "Breakdown History",
                {"parent_breakdown": parent_name, "breakdown_status": "3"},
                "name"
            )

            if resolved_name:
                doc = frappe.get_doc("Breakdown History", resolved_name)
                doc.update({
                    "update_date_time": self.resolved_datetime,
                    "breakdown_reason_updates": self.resolution_summary or "",
                    "timeclock": self.breakdown_hours or 0,
                    "breakdown_resolved": 1,
                    "exclude_from_au": self.exclude_from_au or 0,
                    "location": self.location,
                    "asset_name": self.asset_name
                })
                doc.save(ignore_permissions=True)
            else:
                frappe.get_doc({
                    "doctype": "Breakdown History",
                    "parent_breakdown": parent_name,
                    "update_by": frappe.session.user,
                    "update_date_time": self.resolved_datetime,
                    "location": self.location,
                    "asset_name": self.asset_name,
                    "breakdown_status": "3",
                    "breakdown_reason_updates": self.resolution_summary or "",
                    "breakdown_start_hours": self.hours_breakdown_starts or 0,
                    "timeclock": self.breakdown_hours or 0,
                    "breakdown_resolved": 1,
                    "exclude_from_au": self.exclude_from_au or 0
                }).insert(ignore_permissions=True)

        # ✅ Confirmation popup in ERPNext UI
        frappe.msgprint(f"✅ Breakdown History updated for {self.name}")


# ---------------------------------------------------------------
# GLOBAL HOOK
# ---------------------------------------------------------------
def on_update(doc, method):
    """Always ensure Breakdown History stays updated after saving."""
    # Recalculate only if included
    if doc.exclude_from_au:
        doc.breakdown_hours = 0
    else:
        doc.calculate_breakdown_hours()

    # Always sync to Breakdown History, so exclude flag propagates
    doc.update_breakdown_history()
