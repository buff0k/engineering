import frappe
from frappe.model.document import Document


class RequiredHoursExceptionSpecification(Document):
    def validate(self):
        seen = set()

        for row in self.exceptions or []:
            key = (row.asset, row.day_type, row.shift)

            if key in seen:
                frappe.throw(
                    f"Duplicate exception for {row.asset}, "
                    f"{row.day_type}, {row.shift}."
                )

            seen.add(key)

            asset_location = frappe.db.get_value(
                "Asset", row.asset, "location"
            )

            if asset_location and asset_location != self.location:
                frappe.throw(
                    f"Asset {row.asset} belongs to {asset_location}, "
                    f"not {self.location}."
                )
