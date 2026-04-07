# Copyright (c) 2026, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime


class PreUseDeviation(Document):
	def autoname(self):
		fleet_number = (self.fleet_number or "").strip()
		report_datetime = self.get_report_datetime_for_name()

		if not fleet_number:
			fleet_number = "NO-FLEET"

		if not report_datetime:
			report_datetime = "NO-DATETIME"

		self.name = f"{fleet_number}:{report_datetime}"

	def validate(self):
		self.set_employee_names()
		self.set_machine_details()
		self.set_action_status_and_completion()
		self.set_document_id()

	def before_save(self):
		self.set_employee_names()
		self.set_machine_details()
		self.set_action_status_and_completion()
		self.set_document_id()

	def get_report_datetime_for_name(self):
		# change this only if your real fieldname is different
		report_dt = self.report_datetime if hasattr(self, "report_datetime") else None

		if not report_dt:
			return ""

		try:
			dt = get_datetime(report_dt)
			return dt.strftime("%Y-%m-%d %H-%M-%S")
		except Exception:
			return str(report_dt)

	def set_employee_names(self):
		if hasattr(self, "reported_by_name_and_surname"):
			self.reported_by_name_and_surname = self.get_employee_name(self.reported_by_coy_number)

		if hasattr(self, "actioned_by_name_and_surname"):
			self.actioned_by_name_and_surname = self.get_employee_name(self.actioned_by_coy_number)

	def get_employee_name(self, coy_number):
		if not coy_number:
			return ""

		employee_name = frappe.db.get_value("Employee", coy_number, "employee_name")
		if employee_name:
			return employee_name

		for fieldname in ["employee", "employee_number", "attendance_device_id", "custom_coy_number", "coy_number"]:
			try:
				employee_name = frappe.db.get_value(
					"Employee",
					{fieldname: coy_number},
					"employee_name"
				)
				if employee_name:
					return employee_name
			except Exception:
				pass

		return ""

	def set_machine_details(self):
		if not getattr(self, "fleet_number", None):
			if hasattr(self, "machine_type"):
				self.machine_type = ""
			if hasattr(self, "machine_model"):
				self.machine_model = ""
			return

		asset_category = ""
		item_name = ""

		try:
			result = frappe.db.get_value(
				"Asset",
				{"asset_name": self.fleet_number},
				["asset_category", "item_name"],
				as_dict=True
			)
			if result:
				asset_category = result.get("asset_category") or ""
				item_name = result.get("item_name") or ""
		except Exception:
			pass

		if not asset_category and not item_name:
			try:
				result = frappe.db.get_value(
					"Asset",
					self.fleet_number,
					["asset_category", "item_name"],
					as_dict=True
				)
				if result:
					asset_category = result.get("asset_category") or ""
					item_name = result.get("item_name") or ""
			except Exception:
				pass

		if hasattr(self, "machine_type"):
			self.machine_type = asset_category

		if hasattr(self, "machine_model"):
			self.machine_model = item_name

	def set_action_status_and_completion(self):
		if self.action_date_and_time:
			if hasattr(self, "action_status"):
				self.action_status = "Closed"
			self.completion_percentage = 100
		else:
			if hasattr(self, "action_status"):
				self.action_status = "Open"
			self.completion_percentage = 0

		self.completion_percentage = int(self.completion_percentage or 0)

	def set_document_id(self):
		if hasattr(self, "document_id") and self.name:
			self.document_id = self.name