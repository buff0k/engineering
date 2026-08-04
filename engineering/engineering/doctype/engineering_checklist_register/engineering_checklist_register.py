import frappe
from frappe.model.document import Document


class EngineeringChecklistRegister(Document):
    def autoname(self):
        self.set_site_month_year_name()

    def before_insert(self):
        self.set_site_month_year_name()

    def validate(self):
        self.ensure_supplier_assets_loaded()
        self.prevent_header_changes_after_save()

    def set_site_month_year_name(self):
        site = _make_name_part(self.site)
        month = _make_name_part(self.month)
        year = _make_name_part(self.year)

        if not site or not month or not year:
            frappe.throw("Site, Month and Year are required before saving.")

        self.name = f"{site}-{month}-{year}"

    def prevent_header_changes_after_save(self):
        if self.is_new():
            return

        old_doc = self.get_doc_before_save()
        if not old_doc:
            return

        locked_fields = ["site", "month", "year"]

        for fieldname in locked_fields:
            if self.get(fieldname) != old_doc.get(fieldname):
                frappe.throw(f"{frappe.unscrub(fieldname)} cannot be changed after saving.")


    def ensure_supplier_assets_loaded(self):
        """Always add missing supplier machines for the selected site."""

        if not self.get("site"):
            return

        child_field = self._get_checklist_child_fieldname()

        if not child_field:
            return

        existing = set()

        for row in self.get(child_field) or []:
            fleet_no = row.get("fleet_no")
            if fleet_no:
                existing.add(str(fleet_no).strip())
                existing.add(self._norm_asset(fleet_no))

        supplier_assets = frappe.get_all(
            "Asset",
            filters={
                "location": self.site,
                "asset_owner": "Supplier",
                "supplier": ["is", "set"],
                "docstatus": ["!=", 2],
            },
            fields=[
                "name",
                "asset_name",
                "asset_category",
                "item_name",
                "supplier",
            ],
            order_by="name asc",
            limit_page_length=0,
        )

        for asset in supplier_assets:
            keys = set()

            if asset.get("name"):
                keys.add(str(asset.get("name")).strip())
                keys.add(self._norm_asset(asset.get("name")))

            if asset.get("asset_name"):
                keys.add(str(asset.get("asset_name")).strip())
                keys.add(self._norm_asset(asset.get("asset_name")))

            if existing.intersection(keys):
                continue

            self.append(child_field, {
                "fleet_no": asset.get("name"),
                "machine_type": asset.get("asset_category") or "",
                "item_name": asset.get("item_name") or asset.get("asset_name") or asset.get("name"),
                "target": 100,
                "checklist_submission": 0,
            })

            existing.update(keys)

    def _get_checklist_child_fieldname(self):
        meta = frappe.get_meta(self.doctype)

        preferred_fields = ["rows", "machines", "checklist_rows"]

        for fieldname in preferred_fields:
            field = meta.get_field(fieldname)
            if field and field.fieldtype == "Table":
                return fieldname

        for field in meta.fields:
            if field.fieldtype == "Table":
                return field.fieldname

        return None

    def _norm_asset(self, value):
        return (
            str(value or "")
            .strip()
            .upper()
            .replace("IS0", "IS")
            .replace(" ", "")
        )


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
    "Service Truck",
]


MACHINE_TYPE_ALIASES = {
    "excavator": "Excavator",
    "excavators": "Excavator",

    "adt": "ADT",
    "adts": "ADT",

    "dozer": "DOZER",
    "dozers": "DOZER",

    "water bowser": "WATER BOWSER",
    "water bowsers": "WATER BOWSER",

    "diesel bowser": "Diesel bowser",
    "diesel bowsers": "Diesel bowser",
    "diesel bowswer": "Diesel bowser",
    "diesel bowswers": "Diesel bowser",

    "grader": "GRADER",
    "graders": "GRADER",

    "tlb": "TLB",
    "tlbs": "TLB",

    "drill": "DRILLS",
    "drills": "DRILLS",
    "drilling": "DRILLS",

    "ldv": "LDV",
    "ldvs": "LDV",

    "lighting plant": "LIGHTING PLANT",
    "lighting plants": "LIGHTING PLANT",
    "lightning plant": "LIGHTING PLANT",
    "lightning plants": "LIGHTING PLANT",

    "water pump": "WATER PUMP",
    "water pumps": "WATER PUMP",

    "generator": "GENERATOR",
    "generators": "GENERATOR",
    "genarator": "GENERATOR",
    "genarators": "GENERATOR",

    "fel": "FEL",
    "fels": "FEL",
    "front end loader": "FEL",
    "front-end loader": "FEL",
    "front end loaders": "FEL",
    "front-end loaders": "FEL",

    "loader": "Loader",
    "loaders": "Loader",

    "service truck": "Service Truck",
    "service trucks": "Service Truck",
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

    config = _get_asset_source_config()

    rows = frappe.get_all(
        config["doctype"],
        filters={
            config["site_field"]: site,
            "docstatus": 1,
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

    forced_machine_types = [
        "DRILLS",
        "FEL",
        "Loader",
        "Diesel bowser",
        "Service Truck",
    ]

    for machine_type in forced_machine_types:
        if machine_type not in seen:
            seen.add(machine_type)
            result.append(machine_type)

    result.sort(key=lambda value: _normalize_text(value).lower())

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