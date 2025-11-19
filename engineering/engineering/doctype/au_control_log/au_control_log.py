# Copyright (c) 2025, Isambane Mining (Pty) Ltd
# AU Control Log — Manual and Background triggers for A&U Engine

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from engineering.engineering.doctype.availability_and_utilisation.availability_and_utilisation import (
    AvailabilityandUtilisation,
)


# ================================================================
#              HELPER: Append to execution log
# ================================================================

def _append_log(doc, message):
    """Append timestamped messages to the execution log + push to UI."""
    timestamp = now_datetime().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} — {message}"

    # Save in document log
    if not doc.execution_log:
        doc.execution_log = line
    else:
        doc.execution_log += f"\n{line}"

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Developer console output
    print(line)

    # Realtime WebSocket message (UI popup)
    try:
        frappe.publish_realtime(
            event="au_progress_update",
            message=line,
            user=frappe.session.user
        )
    except Exception:
        pass


# ================================================================
#                     MAIN DOC EVENT CLASS
# ================================================================

class AUControlLog(Document):

    @frappe.whitelist()
    def run_availability_engine(self):
        """
        Manual trigger — runs the A&U Engine immediately.
        """

        start_time = now_datetime()
        self.last_run_time = start_time
        frappe.msgprint("🚀 Starting Availability & Utilisation Engine...")

        _append_log(self, "Manual engine run started")

        try:
            # ----------------------------------------------------------
            # Run main engine
            # ----------------------------------------------------------
            _append_log(self, "Executing generate_records()…")
            msg = AvailabilityandUtilisation.generate_records()

            # ----------------------------------------------------------
            # Extract stats from response message
            # ----------------------------------------------------------
            import re
            created = updated = 0

            if msg:
                c = re.search(r"created\s+(\d+)", msg.lower())
                u = re.search(r"updated\s+(\d+)", msg.lower())
                if c: created = int(c.group(1))
                if u: updated = int(u.group(1))

            _append_log(self, f"Engine summary: {created} created, {updated} updated")

            # ----------------------------------------------------------
            # FIXED ERROR LOG HANDLING — works with your schema
            # ----------------------------------------------------------
            logs_raw = frappe.get_all(
                "Error Log",
                filters={"modified": [">", start_time]},
                fields=["creation", "method", "error"],
                order_by="creation desc",
                limit=50,
            )

            logs = []
            for l in logs_raw:
                subject = l.get("method") or l.get("error") or "(no error text)"
                logs.append(f"{l.get('creation')} - {subject}")

            errors = len(logs)
            log_text = "\n".join(logs) if logs else "No errors logged."

            _append_log(self, f"Errors detected: {errors}")

            # ----------------------------------------------------------
            # Update AU Control Log fields
            # ----------------------------------------------------------
            self.records_created = created
            self.records_updated = updated
            self.records_errors = errors
            self.execution_log = self.execution_log + "\n" + log_text if log_text else self.execution_log
            self.last_message = msg or "Engine completed successfully."
            self.save(ignore_permissions=True)
            frappe.db.commit()

            _append_log(self, "Manual run completed successfully.")
            frappe.msgprint(
                f"✅ Completed — {created} created, {updated} updated, {errors} errors."
            )
            return msg

        except Exception as e:
            frappe.log_error(f"Manual run failed: {str(e)}", "AU Control Log")
            _append_log(self, f"❌ Engine failed: {str(e)}")
            frappe.throw(f"❌ Failed: {str(e)}")


# ================================================================
#                    BACKGROUND TRIGGER
# ================================================================

@frappe.whitelist()
def run_availability_engine_background(doc=None):
    """Runs the A&U engine in background (non-blocking)."""

    try:
        control_name = None

        if isinstance(doc, dict):
            control_name = doc.get("name")
        elif isinstance(doc, str):
            control_name = doc

        frappe.enqueue(
            "engineering.engineering.doctype.au_control_log.au_control_log._background_job_runner",
            control_name=control_name,
            queue="long",
            job_name=f"Manual A&U Engine Run ({frappe.session.user})",
            timeout=60 * 60,
        )

        frappe.msgprint(
            msg="⏳ The A&U Engine has been queued in the background.",
            title="Process Queued",
            indicator="blue",
        )

        print("\n🕒 Background run queued successfully.\n")
        return "Queued"

    except Exception as e:
        frappe.log_error(
            f"Background queue failed: {str(e)}",
            "AU Control Log - Background Run",
        )
        frappe.throw(f"❌ Failed to queue background job: {str(e)}")


# ================================================================
#                 BACKGROUND JOB WORKER
# ================================================================

def _background_job_runner(control_name=None):
    """Background runner updates AU Control Log after engine completes."""

    start_time = now_datetime()

    try:
        ctrl = frappe.get_doc("AU Control Log", control_name) if control_name else None
        if ctrl:
            _append_log(ctrl, "Background job started…")

        msg = AvailabilityandUtilisation.generate_records()

        import re
        created = updated = 0

        if msg:
            c = re.search(r"created\s+(\d+)", msg.lower())
            u = re.search(r"updated\s+(\d+)", msg.lower())
            if c: created = int(c.group(1))
            if u: updated = int(u.group(1))

        # -------- FIXED ERROR LOG HANDLING --------
        logs_raw = frappe.get_all(
            "Error Log",
            filters={"modified": [">", start_time]},
            fields=["creation", "method", "error"],
            order_by="creation desc",
            limit=50,
        )

        logs = []
        for l in logs_raw:
            subject = l.get("method") or l.get("error") or "(no error text)"
            logs.append(f"{l.get('creation')} - {subject}")

        errors = len(logs)
        log_text = "\n".join(logs) if logs else "No errors logged."

        # -------- UPDATE THE CONTROL LOG --------
        if ctrl:
            ctrl.last_run_time = start_time
            ctrl.records_created = created
            ctrl.records_updated = updated
            ctrl.records_errors = errors
            ctrl.execution_log = (ctrl.execution_log or "") + "\n" + log_text
            ctrl.last_message = msg or "Background job completed successfully."
            ctrl.save(ignore_permissions=True)
            frappe.db.commit()

            _append_log(ctrl, f"Background completed: {created} created, {updated} updated, {errors} errors")

        print(
            f"\n✅ Background job finished — {created} created, {updated} updated, {errors} errors.\n"
        )

    except Exception as e:
        if control_name:
            ctrl = frappe.get_doc("AU Control Log", control_name)
            _append_log(ctrl, f"❌ Background job failed: {str(e)}")

        frappe.log_error(
            f"Background job runner failed: {str(e)}",
            "AU Control Log Background Job",
        )
        print(f"\n❌ Background job failed: {str(e)}\n")
