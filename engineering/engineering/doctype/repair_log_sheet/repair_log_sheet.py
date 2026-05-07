import frappe
from frappe.model.document import Document
from datetime import datetime
from frappe.utils import get_first_day, get_last_day


class RepairLogSheet(Document):
    def autoname(self):
        if not self.plant_no:
            frappe.throw("Plant No is required before saving.")

        site = ""

        if self.repair_entries:
            site = self.repair_entries[0].site or ""

        if not site:
            frappe.throw("Site could not be found. Please load Repair Entries before saving.")

        if self.month:
            self.name = f"{site}-{self.plant_no}-{self.month}"
        else:
            self.name = f"{site}-{self.plant_no}"


def get_month_date(month):
    if not month:
        return None

    month = month.strip().replace(" ", "")

    if "-" not in month:
        return None

    parts = month.split("-", 1)

    if len(parts) != 2:
        return None

    month_part = parts[0].strip().lower()
    year_part = parts[1].strip()

    month_map = {
        "jan": 1,
        "january": 1,
        "feb": 2,
        "february": 2,
        "mar": 3,
        "march": 3,
        "apr": 4,
        "april": 4,
        "may": 5,
        "jun": 6,
        "june": 6,
        "jul": 7,
        "july": 7,
        "aug": 8,
        "august": 8,
        "sep": 9,
        "sept": 9,
        "september": 9,
        "oct": 10,
        "october": 10,
        "nov": 11,
        "november": 11,
        "dec": 12,
        "december": 12
    }

    if month_part not in month_map:
        return None

    if not year_part.isdigit():
        return None

    if len(year_part) == 2:
        year = 2000 + int(year_part)
    elif len(year_part) == 4:
        year = int(year_part)
    else:
        return None

    return datetime(year, month_map[month_part], 1).date()


@frappe.whitelist()
def get_msr_entries_for_asset(plant_no, month=None):
    if not plant_no:
        return []

    filters = {
        "asset": plant_no,
        "docstatus": ["!=", 2]
    }

    if month:
        month_date = get_month_date(month)

        if month_date:
            filters["service_date"] = [
                "between",
                [
                    get_first_day(month_date),
                    get_last_day(month_date)
                ]
            ]

    msr_list = frappe.get_all(
        "Mechanical Service Report",
        filters=filters,
        fields=[
            "name",
            "service_date",
            "current_hours",
            "service_breakdown",
            "service_interval",
            "description_of_breakdown",
            "artisan_fullname",
            "site"
        ],
        order_by="service_date desc"
    )

    entries = []

    for msr in msr_list:
        defect = msr.service_breakdown or ""

        if defect == "Service":
            description = msr.service_interval or ""
        elif defect == "Breakdown":
            description = msr.description_of_breakdown or ""
        else:
            description = msr.description_of_breakdown or msr.service_interval or ""

        entries.append({
            "msr": msr.name or "",
            "service_date": msr.service_date or "",
            "hours": msr.current_hours or 0,
            "defect": defect,
            "description": description,
            "rep_by": msr.artisan_fullname or "",
            "site": msr.site or ""
        })

    return entries