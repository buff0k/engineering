import frappe
from frappe.model.document import Document


class EngineeringLDVChecklistRegister(Document):
    def autoname(self):
        self.set_site_month_year_name()

    def before_insert(self):
        self.set_site_month_year_name()

    def validate(self):
        self.set_site_month_year_name()

    def set_site_month_year_name(self):
        site = _make_name_part(self.site)
        month = _make_name_part(self.month)
        year = _make_name_part(self.year)

        if not site or not month or not year:
            frappe.throw("Site, Month and Year are required before saving.")

        self.name = f"{site}-{month}-{year}"


ALLOWED_MACHINE_TYPES = [
    "Excavator",
    "ADT",
    "DOZER",
    "WATER BOWSER",
    "Diesel bowser",
    "GRADER",
    "TLB",
    "DRILLS",
    "LDV",
    "LIGHTING PLANT",
    "WATER PUMP",
    "GENERATOR",
    "FEL",
    "Loader",
]

MACHINE_TYPE_ALIASES = {
    "excavator": "Excavator",
    "adt": "ADT",
    "dozer": "DOZER",

    "water bowser": "WATER BOWSER",
    "water bowsers": "WATER BOWSER",

    "diesel bowser": "Diesel bowser",
    "diesel bowsers": "Diesel bowser",
    "diesel bowswer": "Diesel bowser",
    "diesel bowswers": "Diesel bowser",

    "grader": "GRADER",
    "tlb": "TLB",

    "drill": "DRILLS",
    "drills": "DRILLS",
    "drilling": "DRILLS",

    "ldv": "LDV",

    "lighting plant": "LIGHTING PLANT",
    "lightning plant": "LIGHTING PLANT",

    "water pump": "WATER PUMP",
    "generator": "GENERATOR",
    "genarator": "GENERATOR",

    "fel": "FEL",
    "front end loader": "FEL",
    "front-end loader": "FEL",

    "loader": "Loader",
    "loaders": "Loader",
}


COMBINED_LDV_SITES = {
    "gwab",
    "klipfontein",
}


def _normalize_text(value):
    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def _make_name_part(value):
    text = _normalize_text(value)

    if not text:
        return ""

    return text.upper().replace(" ", "-")


def _clean_allowed_machine_type(value):
    text = _normalize_text(value)

    if not text:
        return ""

    return MACHINE_TYPE_ALIASES.get(text.lower(), "")


def _get_effective_site_filter(site):
    site_text = _normalize_text(site)

    if site_text.lower() in COMBINED_LDV_SITES:
        return ["in", ["Gwab", "Klipfontein"]]

    return site_text


def _get_asset_source_config():
    meta = frappe.get_meta("Asset")
    fieldnames = [f.fieldname for f in meta.fields if f.fieldname]

    required_fields = [
        "location",
        "asset_category",
        "item_name",
        "asset_name",
    ]

    missing_fields = [field for field in required_fields if field not in fieldnames]

    if missing_fields:
        frappe.throw(
            "Missing required fields on Asset: {0}".format(", ".join(missing_fields))
        )

    return {
        "doctype": "Asset",
        "site_field": "location",
        "machine_type_field": "asset_category",
        "item_name_field": "item_name",
        "fleet_no_field": "asset_name",
    }


@frappe.whitelist()
def get_machine_type_options(site=None):
    if not site:
        return []

    # This LDV register should only show LDV as the machine type option.
    return ["LDV"]


@frappe.whitelist()
def get_site_machines(site, machine_type=None):
    if not site:
        return []

    config = _get_asset_source_config()
    site_filter = _get_effective_site_filter(site)

    # This register is specifically for LDVs, so force LDV even if blank is passed.
    cleaned_requested_type = "LDV"

    asset_rows = frappe.get_all(
        config["doctype"],
        filters={
            config["site_field"]: site_filter,
            "docstatus": 1,
        },
        fields=[
            config["fleet_no_field"],
            config["machine_type_field"],
            config["item_name_field"],
        ],
        order_by="asset_name asc",
        limit_page_length=0,
    )

    result = []

    for record in asset_rows:
        machine_type_value = _clean_allowed_machine_type(
            record.get(config["machine_type_field"])
        )

        if not machine_type_value:
            continue

        if machine_type_value != cleaned_requested_type:
            continue

        result.append(
            {
                "fleet_no": _normalize_text(record.get(config["fleet_no_field"])),
                "machine_type": machine_type_value,
                "item_name": _normalize_text(record.get(config["item_name_field"])),
            }
        )

    return result