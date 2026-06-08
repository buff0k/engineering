# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TravelLogSheet(Document):
    def validate(self):
        self.validate_odo_meters()
        self.set_previous_odo_meter_out()

    def validate_odo_meters(self):
        if self.odo_meter_out is None:
            return

        if self.odo_meter_in is None:
            return

        if int(self.odo_meter_in) < int(self.odo_meter_out):
            frappe.throw("ODO Meter In cannot be less than ODO Meter Out")

    def set_previous_odo_meter_out(self):
        if not self.fleet_number:
            return

        if self.odo_meter_out not in [None, "", 0]:
            return

        previous_odo = frappe.db.get_value(
            "Travel Log Sheet",
            {
                "fleet_number": self.fleet_number,
                "name": ["!=", self.name],
            },
            "odo_meter_in",
            order_by="date desc, creation desc",
        )

        if previous_odo is not None:
            self.odo_meter_out = previous_odo