import frappe
from frappe.model.document import Document


class PurchaseRequisition(Document):
    def autoname(self):
        if not self.pr_no:
            frappe.throw("PR No is required")

        self.name = self.pr_no.strip()

    def validate(self):
        if self.pr_no:
            self.pr_no = self.pr_no.strip()

        total_items = 0

        for row in self.items or []:
            row.total_cost = (row.qty or 0) * (row.unit_price or 0)
            total_items += row.total_cost or 0

        self.total = total_items - (self.discount or 0) + (self.vat or 0)