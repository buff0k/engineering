import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class PreUseDeviation(Document):
    def autoname(self):
        site = _normalize_text(self.site)

        fleet_number = (
            _normalize_text(getattr(self, "fleet_number", ""))
            or _normalize_text(getattr(self, "fleet_no", ""))
            or _normalize_text(getattr(self, "asset", ""))
        )

        if not site:
            frappe.throw("Site is required before saving.")

        if not fleet_number:
            frappe.throw("Fleet Number is required before saving.")

        date_time = now_datetime().strftime("%d-%m-%Y %H:%M:%S")

        self.name = f"{site}-{fleet_number}-{date_time}"


ALLOWED_MACHINE_TYPES = [
    "Excavator",
    "ADT",
    "DOZER",
    "WATER BOWSER",
    "DIESEL BOWSER",
    "GRADER",
    "TLB",
    "DRILLS",
    "LDV",
    "LIGHTING PLANT",
    "WATER PUMP",
    "GENERATOR",
]

MACHINE_TYPE_ALIASES = {
    "excavator": "Excavator",
    "adt": "ADT",
    "dozer": "DOZER",
    "water bowser": "WATER BOWSER",
    "diesel bowser": "DIESEL BOWSER",
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


def _get_asset_source_config():
    meta = frappe.get_meta("Asset")
    fieldnames = [f.fieldname for f in meta.fields if f.fieldname]

    required_fields = [
        "location",
        "asset_category",
        "item_name",
        "asset_name",
        "status",
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
        "status_field": "status",
    }


@frappe.whitelist()
def get_machine_type_options(site=None):
    if not site:
        return []

    config = _get_asset_source_config()

    rows = frappe.get_all(
        config["doctype"],
        filters={
            config["site_field"]: site,
            config["status_field"]: "Submitted",
        },
        fields=[
            config["machine_type_field"],
        ],
        order_by="asset_category asc",
        limit_page_length=0,
    )

    result = []
    seen = set()

    for row in rows:
        machine_type = _clean_allowed_machine_type(
            row.get(config["machine_type_field"])
        )

        if machine_type and machine_type not in seen:
            seen.add(machine_type)
            result.append(machine_type)

    result.sort()
    return result


@frappe.whitelist()
def get_site_machines(site, machine_type=None):
    if not site:
        return []

    config = _get_asset_source_config()

    cleaned_requested_type = (
        _clean_allowed_machine_type(machine_type)
        if machine_type
        else ""
    )

    if machine_type and not cleaned_requested_type:
        return []

    asset_rows = frappe.get_all(
        config["doctype"],
        filters={
            config["site_field"]: site,
            config["status_field"]: "Submitted",
        },
        fields=[
            config["fleet_no_field"],
            config["machine_type_field"],
            config["item_name_field"],
            config["status_field"],
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

        if cleaned_requested_type and machine_type_value != cleaned_requested_type:
            continue

        result.append(
            {
                "fleet_no": _normalize_text(record.get(config["fleet_no_field"])),
                "machine_type": machine_type_value,
                "item_name": _normalize_text(record.get(config["item_name_field"])),
            }
        )

    return result