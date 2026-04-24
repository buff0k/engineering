# Copyright (c) 2026, Isambane
# For license information, please see license.txt

import frappe
from datetime import datetime, time, timedelta

from frappe.model.document import Document
from frappe.utils import getdate


class MechanicalDailyWorksheet(Document):
    def autoname(self):
        site = self.site or "NO-SITE"

        worksheet_date = getdate(self.date) if self.date else getdate()
        worksheet_date = worksheet_date.strftime("%Y-%m-%d")

        mechanic_name = self.mechanic_name_surname or "NO-MECHANIC"
        mechanic_name = mechanic_name.strip().upper()

        base_name = f"{site}-{worksheet_date}-{mechanic_name}"

        self.name = self.get_unique_name(base_name)

    def get_unique_name(self, base_name):
        if not frappe.db.exists(self.doctype, base_name):
            return base_name

        counter = 1

        while True:
            new_name = f"{base_name}-{counter}"

            if not frappe.db.exists(self.doctype, new_name):
                return new_name

            counter += 1

    def validate(self):
        self.calculate_total_hours()
        self.calculate_child_hours()
        self.calculate_total_work_time()

    def calculate_total_hours(self):
        self.total_hours = self.get_hours_difference(
            self.clock_in_time,
            self.clock_out_time
        )

    def calculate_child_hours(self):
        for row in self.work_details:
            row.hours = self.get_hours_difference(
                row.time_started,
                row.time_done
            )

    def calculate_total_work_time(self):
        total = 0.0

        for row in self.work_details:
            total += float(row.hours or 0)

        self.total_work_time = round(total, 2)

    def get_hours_difference(self, start_value, end_value):
        if not start_value or not end_value:
            return 0

        start_seconds = self.time_to_seconds(start_value)
        end_seconds = self.time_to_seconds(end_value)

        if start_seconds is None or end_seconds is None:
            return 0

        # Handles night shift, example 22:00 to 02:00
        if end_seconds < start_seconds:
            end_seconds += 24 * 60 * 60

        difference_seconds = end_seconds - start_seconds
        hours = difference_seconds / 3600

        return round(hours, 2)

    def time_to_seconds(self, value):
        if not value:
            return None

        if isinstance(value, timedelta):
            return int(value.total_seconds())

        if isinstance(value, time):
            return (
                value.hour * 3600
                + value.minute * 60
                + value.second
            )

        if isinstance(value, str):
            value = value.strip()

            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    parsed_time = datetime.strptime(value, fmt).time()
                    return (
                        parsed_time.hour * 3600
                        + parsed_time.minute * 60
                        + parsed_time.second
                    )
                except ValueError:
                    continue

        return None