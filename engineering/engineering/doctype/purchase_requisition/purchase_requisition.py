from frappe.model.document import Document
from frappe.model.naming import make_autoname


class PurchaseRequisition(Document):
    def autoname(self):
        self.name = make_autoname("PR-.#####")
        self.pr_no = self.name

    def validate(self):
        total_items = 0

        for row in self.items or []:
            row.total_cost = (row.qty or 0) * (row.unit_price or 0)
            total_items += row.total_cost or 0

        self.total = total_items - (self.discount or 0) + (self.vat or 0)

        if self.name:
            self.pr_no = self.name