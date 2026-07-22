# Server path:
# apps/engineering/engineering/templates/pages/tyre_survey_sup.py
# v10: Exact serial-number lookup from Tyre Master with
# editable portal autofill fields.

import json

import frappe
from frappe import _
from frappe.utils import flt

from engineering.templates.pages.tyre_portal_security import (
    assert_draft_access,
    get_portal_supplier,
    validate_portal_access,
)


ALLOWED_SUPPLIER_SITES = [
    "Bankfontein",
    "Duplicate Assets",
    "Grinaker",
    "Gwab",
    "Klipfontein",
    "Koppie",
    "Kriel Rehabilitation",
    "M15",
    "Mimosa",
    "Plot 20",
    "Plot 22",
    "Plot 22 Workshop",
    "PLOT22",
    "Roodepoort",
    "Sold Assets",
    "Tselentis",
    "Uitgevallen",
    "Wonderfontein",
]


TYRE_ITEM_FIELDS = [
    "position",
    "tyre_make",
    "serial_number",
    "brand_number",
    "tyre_size",
    "tread_pattern",
    "star_ply_rating",
    "tra_code",
    "compound_code",
    "overall_diameter",
    "otd",
    "rtd_1",
    "rtd_2",
    "rtd_percent",
    "recommended_pressure",
    "actual_pressure",
    "pressure_variance",
    "condition_notes",
    "required_action",
]


# Tyre Master values that may be copied into a portal tyre
# row after an exact serial-number match.  The portal keeps
# these as editable snapshot values and never writes back to
# Tyre Master.
TYRE_MASTER_PORTAL_FIELDS = [
    "tyre_make",
    "brand_number",
    "tyre_size",
    "tread_pattern",
    "star_ply_rating",
    "tra_code",
    "compound_code",
    "overall_diameter",
    "otd",
    "recommended_pressure",
]


ADT_TYRE_SIZES = [
    "23.5R25",
    "29.5R25",
]


# Tyre makes and tread patterns recorded on ADTs in the
# June 2026 Gwab, MMS Klipfontein and Kriel Block 6 reports.
ADT_TYRE_TREAD_PATTERNS = {
    "Advance": ["GLR09"],
    "Aeolus": ["AL37"],
    "Atlas": ["LB01N"],
    "BKT": ["EARTHMAX SR - 30"],
    "Boto": ["GCA1", "GCB5"],
    "Bridgestone": ["VLT"],
    "Double Coin": ["REM10"],
    "Goodyear": ["GP-3E", "TL-3A+"],
    "Hilo": ["B02N"],
    "Linglong": ["LMS401"],
    "Magna": ["MA02"],
    "Maxam": ["MS302"],
    "Michelin": ["XADN+"],
    "Retread": ["VLT"],
    "Techking": ["PRO ADT"],
    "Tianli": ["TUL300", "TUL302"],
    "Triangle": ["TB516", "TB598", "TB598S"],
}


STANDARD_TYRE_POSITIONS = [
    "LF",
    "RF",
    "RM",
    "RR",
    "LR",
    "LM",
]


B60E_TYRE_POSITIONS = [
    "LF",
    "RF",
    "RRO",
    "RRI",
    "LRI",
    "LRO",
]


STANDARD_ADT_MODEL_CODES = [
    "A40G",
    "B40D",
    "B40E",
    "B45E",
    "740GC",
]


ADT_MODEL_MAKES = {
    "B60E": "Bell",
    "B60": "Bell",
    "B45E": "Bell",
    "A40G": "Volvo",
    "B40D": "Bell",
    "B40E": "Bell",
    "740GC": "Cat",
}


# Temporary fallback for CAT 740GC Assets whose linked
# Asset and Item records do not yet contain the model.
ASSET_INFORMATION_OVERRIDES = {
    "IS0566": {
        "vehicle_make": "Cat",
        "model": "740GC",
    },
    "IS0614": {
        "vehicle_make": "Cat",
        "model": "740GC",
    },
    "IS0616": {
        "vehicle_make": "Cat",
        "model": "740GC",
    },
    "IS0617": {
        "vehicle_make": "Cat",
        "model": "740GC",
    },
    "IS0618": {
        "vehicle_make": "Cat",
        "model": "740GC",
    },
    "IS0619": {
        "vehicle_make": "Cat",
        "model": "740GC",
    },
    "IS566": {
        "vehicle_make": "Cat",
        "model": "740GC",
    },
    "IS614": {
        "vehicle_make": "Cat",
        "model": "740GC",
    },
    "IS616": {
        "vehicle_make": "Cat",
        "model": "740GC",
    },
    "IS617": {
        "vehicle_make": "Cat",
        "model": "740GC",
    },
    "IS618": {
        "vehicle_make": "Cat",
        "model": "740GC",
    },
    "IS619": {
        "vehicle_make": "Cat",
        "model": "740GC",
    },
}


STANDARD_LAYOUT_IMAGE = (
    "/assets/engineering/images/tyre_layouts/"
    "Standard_adt.png"
)


B60E_LAYOUT_IMAGE = (
    "/assets/engineering/images/tyre_layouts/"
    "Bell_B60E.png"
)


# The code searches these possible Asset fieldnames.
#
# If your Asset uses different custom fieldnames, add them to
# the appropriate list below.
ASSET_INFORMATION_FIELDS = {
    "vehicle_make": [
        "custom_vehicle_make",
        "vehicle_make",
        "custom_make",
        "make",
        "manufacturer",
        "brand",
    ],
    "model": [
        "custom_vehicle_model",
        "vehicle_model",
        "custom_model",
        "model",
    ],
    "machine_type": [
        "custom_machine_type",
        "machine_type",
        "custom_vehicle_type",
        "vehicle_type",
        "asset_category",
    ],
}


ITEM_INFORMATION_FIELDS = {
    "vehicle_make": [
        "custom_vehicle_make",
        "custom_make",
        "manufacturer",
        "brand",
    ],
    "model": [
        "custom_vehicle_model",
        "custom_model",
        "model",
    ],
    "machine_type": [
        "custom_machine_type",
        "custom_vehicle_type",
        "item_group",
    ],
}


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    context.title = "Tyre Survey"

    _validate_portal_access()

    portal_supplier = get_portal_supplier()

    if frappe.request.method == "POST":
        _handle_post()

    draft = _get_editable_draft()

    context.site_options = _get_allowed_site_options()
    context.supplier_options = [portal_supplier]
    context.tyre_options = {
        "sizes": ADT_TYRE_SIZES,
        "patterns": ADT_TYRE_TREAD_PATTERNS,
    }
    context.asset_options = _get_asset_options(
        draft.site if draft else None
    )

    context.form_values = {
        "draft_name": draft.name if draft else "",
        "supplier": draft.supplier if draft else portal_supplier,
        "inspector_name": (
            draft.get("inspector_name")
            if draft
            else frappe.db.get_value(
                "User",
                frappe.session.user,
                "full_name",
            ) or ""
        ),
        "site": draft.site if draft else "",
        "fleet_number": draft.fleet_number if draft else "",
        "survey_date": draft.survey_date if draft else "",
        "survey_attachment": (
            draft.survey_attachment if draft else ""
        ),
        "general_remarks": (
            draft.general_remarks if draft else ""
        ),
    }

    if draft:
        context.tyre_rows = [
            {
                fieldname: row.get(fieldname)
                for fieldname in TYRE_ITEM_FIELDS
            }
            for row in draft.tyres
        ]
    else:
        context.tyre_rows = _default_tyre_rows()


def _validate_portal_access():
    validate_portal_access("/tyre_survey_sup")


def _get_draft_name():
    draft_name = (
        frappe.form_dict.get("draft_name") or ""
    ).strip()

    if not draft_name and getattr(frappe.request, "args", None):
        draft_name = (
            frappe.request.args.get("draft_name") or ""
        ).strip()

    return draft_name


def _get_editable_draft():
    draft_name = _get_draft_name()

    if not draft_name:
        return None

    draft = frappe.get_doc(
        "Tyre Survey Supplier Portal Draft",
        draft_name,
    )

    assert_draft_access(draft, write=True)

    if draft.sent_to_erp:
        frappe.throw(
            _("Submitted records cannot be edited."),
            frappe.PermissionError,
        )

    return draft


def _handle_post():
    # The browser never decides the supplier. It is derived from the logged-in
    # user's standard Supplier User Permission on every request.
    supplier = get_portal_supplier()

    inspector_name = (
        frappe.form_dict.get("inspector_name") or ""
    ).strip()

    site = (
        frappe.form_dict.get("site") or ""
    ).strip()

    fleet_number = (
        frappe.form_dict.get("fleet_number") or ""
    ).strip()

    survey_date = (
        frappe.form_dict.get("survey_date") or ""
    ).strip()

    survey_attachment = (
        frappe.form_dict.get("survey_attachment") or ""
    ).strip()

    general_remarks = (
        frappe.form_dict.get("general_remarks") or ""
    ).strip()

    if not supplier:
        frappe.throw(_("Supplier Company is required."))

    if not inspector_name:
        frappe.throw(_("Inspector Name is required."))

    if not site:
        frappe.throw(_("Site is required."))

    if not fleet_number:
        frappe.throw(_("Fleet Number is required."))

    if not survey_date:
        frappe.throw(_("Survey Date is required."))

    _validate_supplier_site_access(site)

    _validate_supplier(supplier)

    _validate_supplier_asset_access(
        fleet_number,
        site,
    )

    tyre_rows = _parse_tyre_rows(
        fleet_number
    )

    if not tyre_rows:
        frappe.throw(
            _("At least one tyre must be captured.")
        )

    if survey_attachment:
        _validate_uploaded_file(survey_attachment)

    draft_name = _get_draft_name()

    if draft_name:
        doc = frappe.get_doc(
            "Tyre Survey Supplier Portal Draft",
            draft_name,
        )

        assert_draft_access(doc, write=True)

        if doc.sent_to_erp:
            frappe.throw(
                _("Submitted records cannot be edited."),
                frappe.PermissionError,
            )
    else:
        doc = frappe.get_doc(
            {
                "doctype":
                    "Tyre Survey Supplier Portal Draft",
                "portal_user": frappe.session.user,
                "sent_to_erp": 0,
            }
        )

    doc.supplier = supplier
    doc.inspector_name = inspector_name
    doc.site = site
    doc.fleet_number = fleet_number
    doc.survey_date = survey_date
    doc.survey_attachment = survey_attachment or None
    doc.general_remarks = general_remarks

    doc.set("tyres", [])

    for tyre_row in tyre_rows:
        doc.append("tyres", tyre_row)

    if draft_name:
        doc.save(ignore_permissions=True)
    else:
        doc.insert(ignore_permissions=True)

    if survey_attachment:
        _attach_file_to_document(
            survey_attachment,
            doc.doctype,
            doc.name,
            "survey_attachment",
        )

    frappe.db.commit()

    frappe.local.flags.redirect_location = (
        "/tyre_survey_list"
    )
    raise frappe.Redirect


def _parse_tyre_rows(asset_name):
    raw_json = (
        frappe.form_dict.get("tyres_json") or "[]"
    )

    try:
        rows = json.loads(raw_json)
    except (TypeError, ValueError):
        frappe.throw(
            _("The tyre information is invalid.")
        )

    if not isinstance(rows, list):
        frappe.throw(
            _("The tyre information is invalid.")
        )

    asset_information = _get_asset_information(
        asset_name
    )

    expected_positions = asset_information[
        "tyre_positions"
    ]

    if len(rows) != len(expected_positions):
        frappe.throw(
            _(
                "The Tyre Survey must contain "
                "exactly six fixed tyre positions."
            )
        )

    cleaned_rows = []

    for row_number, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            frappe.throw(
                _(
                    "Tyre row {0} is invalid."
                ).format(row_number)
            )

        position = str(
            row.get("position") or ""
        ).strip()

        expected_position = expected_positions[
            row_number - 1
        ]

        if position != expected_position:
            frappe.throw(
                _(
                    "Tyre position {0} must be {1}."
                ).format(
                    row_number,
                    expected_position,
                )
            )

        tyre_make = str(
            row.get("tyre_make") or ""
        ).strip()

        tyre_size = str(
            row.get("tyre_size") or ""
        ).strip()

        tread_pattern = str(
            row.get("tread_pattern") or ""
        ).strip()

        # Ignore completely empty rows.
        if not position and not tyre_make and not tyre_size:
            continue

        if not position:
            frappe.throw(
                _(
                    "Position is required on tyre row {0}."
                ).format(row_number)
            )

        if not tyre_make:
            frappe.throw(
                _(
                    "Tyre Make is required on tyre row {0}."
                ).format(row_number)
            )

        if not tyre_size:
            frappe.throw(
                _(
                    "Tyre Size is required on tyre row {0}."
                ).format(row_number)
            )

        if tyre_make not in ADT_TYRE_TREAD_PATTERNS:
            frappe.throw(
                _(
                    "Tyre Make is invalid on tyre row {0}."
                ).format(row_number)
            )

        if tyre_size not in ADT_TYRE_SIZES:
            frappe.throw(
                _(
                    "Tyre Size is invalid on tyre row {0}."
                ).format(row_number)
            )

        if not tread_pattern:
            frappe.throw(
                _(
                    "Tread Pattern is required on tyre row {0}."
                ).format(row_number)
            )

        if tread_pattern not in ADT_TYRE_TREAD_PATTERNS[
            tyre_make
        ]:
            frappe.throw(
                _(
                    "Tread Pattern {0} is not valid for "
                    "Tyre Make {1} on tyre row {2}."
                ).format(
                    tread_pattern,
                    tyre_make,
                    row_number,
                )
            )

        otd = flt(row.get("otd"))

        if str(row.get("rtd_1") or "").strip() == "":
            frappe.throw(
                _(
                    "Remaining Tread Depth 1 is required "
                    "on tyre row {0}."
                ).format(row_number)
            )

        if str(row.get("rtd_2") or "").strip() == "":
            frappe.throw(
                _(
                    "Remaining Tread Depth 2 is required "
                    "on tyre row {0}."
                ).format(row_number)
            )

        rtd_1 = flt(row.get("rtd_1"))
        rtd_2 = flt(row.get("rtd_2"))

        recommended_pressure = flt(
            row.get("recommended_pressure")
        )

        actual_pressure = flt(
            row.get("actual_pressure")
        )

        if otd <= 0:
            frappe.throw(
                _(
                    "Original Tread Depth must be greater "
                    "than zero on tyre row {0}."
                ).format(row_number)
            )

        if rtd_1 < 0 or rtd_2 < 0:
            frappe.throw(
                _(
                    "Remaining Tread Depth cannot be "
                    "negative on tyre row {0}."
                ).format(row_number)
            )

        if rtd_2 > 0:
            average_rtd = (rtd_1 + rtd_2) / 2
        else:
            average_rtd = rtd_1

        rtd_percent = (
            average_rtd / otd
        ) * 100

        pressure_variance = 0

        if (
            recommended_pressure > 0
            and actual_pressure > 0
        ):
            pressure_variance = (
                (
                    actual_pressure
                    - recommended_pressure
                )
                / recommended_pressure
            ) * 100

        cleaned_rows.append(
            {
                "position": position,
                "tyre_make": tyre_make,
                "serial_number": str(
                    row.get("serial_number") or ""
                ).strip(),
                "brand_number": str(
                    row.get("brand_number") or ""
                ).strip(),
                "tyre_size": tyre_size,
                "tread_pattern": tread_pattern,
                "star_ply_rating": str(
                    row.get("star_ply_rating") or ""
                ).strip(),
                "tra_code": str(
                    row.get("tra_code") or ""
                ).strip(),
                "compound_code": str(
                    row.get("compound_code") or ""
                ).strip(),
                "overall_diameter": flt(
                    row.get("overall_diameter")
                ),
                "otd": otd,
                "rtd_1": rtd_1,
                "rtd_2": rtd_2,
                "rtd_percent": rtd_percent,
                "recommended_pressure":
                    recommended_pressure,
                "actual_pressure": actual_pressure,
                "pressure_variance":
                    pressure_variance,
                "condition_notes": str(
                    row.get("condition_notes") or ""
                ).strip(),
                "required_action": str(
                    row.get("required_action") or ""
                ).strip(),
            }
        )

    return cleaned_rows


def _validate_supplier_asset_access(
    asset_name,
    site_name=None,
):
    """
    Temporary testing version.

    Allows all ADT assets, regardless of asset owner or the
    Supplier linked to the logged-in portal user.
    """

    asset = frappe.db.get_value(
        "Asset",
        asset_name,
        [
            "name",
            "asset_category",
            "supplier",
            "location",
        ],
        as_dict=True,
    )

    if not asset:
        frappe.throw(
            _("Fleet Number does not exist.")
        )

    if asset.asset_category != "ADT":
        frappe.throw(
            _("Only ADT Assets can be used."),
            frappe.PermissionError,
        )

    if (
        site_name
        and asset.location != site_name
    ):
        frappe.throw(
            _(
                "Fleet Number {0} is not assigned "
                "to Site {1}."
            ).format(
                asset.name,
                site_name,
            ),
            frappe.PermissionError,
        )

    return asset.supplier or ""


def _get_supplier_options():
    return [get_portal_supplier()]


def _validate_supplier(supplier):
    if supplier != get_portal_supplier():
        frappe.throw(
            _("You cannot capture surveys for another Supplier."),
            frappe.PermissionError,
        )

    supplier_record = frappe.db.get_value(
        "Supplier",
        supplier,
        [
            "name",
            "disabled",
        ],
        as_dict=True,
    )

    if not supplier_record:
        frappe.throw(_("Supplier Company does not exist."))

    if supplier_record.disabled:
        frappe.throw(
            _("The selected Supplier Company is disabled."),
            frappe.PermissionError,
        )


def _get_asset_options(site_name=None):
    """
    Shows ADT assets assigned to the selected Site.
    """

    if not site_name:
        return []

    return frappe.get_all(
        "Asset",
        filters={
            "asset_category": "ADT",
            "location": site_name,
        },
        pluck="name",
        order_by="name asc",
        limit_page_length=0,
    )


@frappe.whitelist(allow_guest=False)
def get_assets_for_site(site_name=None):
    _validate_portal_access()

    site_name = (
        site_name
        or frappe.form_dict.get("site_name")
        or ""
    ).strip()

    if not site_name:
        frappe.throw(_("Site is required."))

    _validate_supplier_site_access(site_name)

    return _get_asset_options(site_name)


@frappe.whitelist(allow_guest=False)
def get_tyre_master_by_serial(serial_number=None):
    """
    Returns the fixed Tyre Master values for one exact serial.

    Supplier portal users cannot list Tyre Master records.  This
    endpoint only returns the approved fields for the exact serial
    number that the user entered in a survey row.
    """

    _validate_portal_access()

    serial_number = (
        serial_number
        or frappe.form_dict.get("serial_number")
        or ""
    ).strip().upper()

    if not serial_number:
        return {
            "found": False,
            "serial_number": "",
        }

    tyre_master = frappe.db.get_value(
        "Tyre Master",
        {
            "serial_number": serial_number,
        },
        [
            "name",
            "serial_number",
            *TYRE_MASTER_PORTAL_FIELDS,
            "active",
        ],
        as_dict=True,
    )

    if not tyre_master:
        return {
            "found": False,
            "serial_number": serial_number,
        }

    return {
        "found": True,
        "name": tyre_master.name,
        "serial_number": tyre_master.serial_number,
        "active": bool(tyre_master.active),
        **{
            fieldname: tyre_master.get(fieldname)
            for fieldname in TYRE_MASTER_PORTAL_FIELDS
        },
    }


def _get_allowed_site_options():
    asset_locations = frappe.get_all(
        "Asset",
        filters={
            "asset_category": "ADT",
            "location": ["is", "set"],
        },
        pluck="location",
        limit_page_length=0,
    )

    available_sites = sorted(
        set(asset_locations).intersection(
            ALLOWED_SUPPLIER_SITES
        )
    )

    if not available_sites:
        return []

    return frappe.get_all(
        "Location",
        filters={
            "name": [
                "in",
                available_sites,
            ],
        },
        pluck="name",
        order_by="name asc",
        limit_page_length=0,
    )


def _validate_supplier_site_access(site_name):
    if site_name not in ALLOWED_SUPPLIER_SITES:
        frappe.throw(
            _(
                "The selected Site is not available "
                "for Tyre Surveys."
            ),
            frappe.PermissionError,
        )

    if not frappe.db.exists("Location", site_name):
        frappe.throw(
            _("The selected Site does not exist.")
        )


def _get_first_value(doc, fieldnames):
    meta = frappe.get_meta(doc.doctype)

    for fieldname in fieldnames:
        if not meta.has_field(fieldname):
            continue

        value = doc.get(fieldname)

        if value not in (None, ""):
            return value

    return ""


def _get_tyre_layout(model):
    model_code = "".join(
        character
        for character in str(model or "").upper()
        if character.isalnum()
    )

    if "B60" in model_code:
        return {
            "tyre_layout": "b60e",
            "tyre_layout_image": B60E_LAYOUT_IMAGE,
            "tyre_positions": B60E_TYRE_POSITIONS,
        }

    if any(
        model in model_code
        for model in STANDARD_ADT_MODEL_CODES
    ):
        return {
            "tyre_layout": "standard",
            "tyre_layout_image": STANDARD_LAYOUT_IMAGE,
            "tyre_positions": STANDARD_TYRE_POSITIONS,
        }

    return {
        "tyre_layout": "standard",
        "tyre_layout_image": STANDARD_LAYOUT_IMAGE,
        "tyre_positions": STANDARD_TYRE_POSITIONS,
    }


def _normalise_adt_model(model):
    model_text = str(model or "").strip()

    model_code = "".join(
        character
        for character in model_text.upper()
        if character.isalnum()
    )

    # Check longer/specific codes before shorter ones so
    # B60E is not reduced to B60.
    for known_model in (
        "740GC",
        "B60E",
        "B60",
        "B45E",
        "B40E",
        "B40D",
        "A40G",
    ):
        if known_model in model_code:
            return known_model

    return model_text


def _get_asset_information(asset_name):
    asset = frappe.get_doc("Asset", asset_name)

    item = None

    information = {
        "vehicle_make": "",
        "model": "",
        "machine_type": "",
    }

    for output_field, fieldnames in (
        ASSET_INFORMATION_FIELDS.items()
    ):
        information[output_field] = _get_first_value(
            asset,
            fieldnames,
        )

    # If information was not found directly on the Asset,
    # try its linked Item.
    if asset.get("item_code"):
        item = frappe.get_doc(
            "Item",
            asset.item_code,
        )

        for output_field, fieldnames in (
            ITEM_INFORMATION_FIELDS.items()
        ):
            if information[output_field]:
                continue

            information[output_field] = (
                _get_first_value(
                    item,
                    fieldnames,
                )
            )

    description_values = [
        asset.get("item_name"),
        asset.get("item_code"),
    ]

    if item:
        description_values.extend(
            [
                item.get("item_name"),
                item.get("item_code"),
                item.get("description"),
            ]
        )

    item_description = " ".join(
        str(value).strip()
        for value in description_values
        if value not in (None, "")
    )

    description_code = "".join(
        character
        for character in item_description.upper()
        if character.isalnum()
    )

    for model_code, vehicle_make in (
        ADT_MODEL_MAKES.items()
    ):
        if model_code not in description_code:
            continue

        information["model"] = model_code

        if not information["vehicle_make"]:
            information["vehicle_make"] = (
                vehicle_make
            )

        break

    if item_description:
        parts = item_description.split()

        if (
            not information["vehicle_make"]
            and parts
        ):
            information["vehicle_make"] = parts[0]

        if not information["model"]:
            upper_parts = [
                part.upper()
                for part in parts
            ]

            if "ADT" in upper_parts:
                adt_index = upper_parts.index("ADT")

                if adt_index + 1 < len(parts):
                    information["model"] = " ".join(
                        parts[adt_index + 1:]
                    )
            elif len(parts) > 1:
                information["model"] = parts[-1]

    if not information["machine_type"]:
        information["machine_type"] = (
            asset.get("asset_category") or ""
        )

    information.update(
        ASSET_INFORMATION_OVERRIDES.get(
            asset.name,
            {},
        )
    )

    information["model"] = _normalise_adt_model(
        information["model"]
    )

    if (
        not information["vehicle_make"]
        and information["model"] in ADT_MODEL_MAKES
    ):
        information["vehicle_make"] = ADT_MODEL_MAKES[
            information["model"]
        ]

    information.update(
        _get_tyre_layout(
            information["model"]
        )
    )

    return information


@frappe.whitelist(allow_guest=False)
def get_asset_information(
    asset_name=None,
    site_name=None,
):
    _validate_portal_access()

    asset_name = (
        asset_name
        or frappe.form_dict.get("asset_name")
        or ""
    ).strip()

    site_name = (
        site_name
        or frappe.form_dict.get("site_name")
        or ""
    ).strip()

    if not asset_name:
        frappe.throw(
            _("Fleet Number is required.")
        )

    if not site_name:
        frappe.throw(_("Site is required."))

    _validate_supplier_site_access(site_name)

    _validate_supplier_asset_access(
        asset_name,
        site_name,
    )

    return _get_asset_information(asset_name)


@frappe.whitelist(allow_guest=False)
def get_previous_adt_readings(
    asset_name=None,
    site_name=None,
):
    """Return the latest real readings without supplier-identifying fields."""

    _validate_portal_access()

    asset_name = (
        asset_name
        or frappe.form_dict.get("asset_name")
        or ""
    ).strip()
    site_name = (
        site_name
        or frappe.form_dict.get("site_name")
        or ""
    ).strip()

    if not asset_name:
        frappe.throw(_("Fleet Number is required."))

    if site_name:
        _validate_supplier_site_access(site_name)

    _validate_supplier_asset_access(asset_name, site_name or None)

    # Search a few recent records so development mock surveys can be skipped.
    surveys = frappe.get_all(
        "Tyre Survey",
        filters={
            "fleet_number": asset_name,
            "docstatus": ["<", 2],
        },
        fields=["name", "survey_date", "inspector_name"],
        order_by="survey_date desc, modified desc",
        limit_page_length=25,
    )
    survey = next(
        (
            row
            for row in surveys
            if row.inspector_name != "Mock Survey Generator"
        ),
        None,
    )

    if not survey:
        return {
            "found": False,
            "fleet_number": asset_name,
            "message": "No previous actual survey was found.",
        }

    document = frappe.get_doc("Tyre Survey", survey.name)
    approved_fields = (
        "position",
        "serial_number",
        "tyre_make",
        "tread_pattern",
        "otd",
        "rtd_1",
        "rtd_2",
        "rtd_percent",
        "recommended_pressure",
        "actual_pressure",
        "condition_notes",
        "required_action",
    )

    return {
        "found": True,
        "fleet_number": asset_name,
        "survey_date": survey.survey_date,
        "tyres": [
            {
                fieldname: tyre.get(fieldname)
                for fieldname in approved_fields
            }
            for tyre in document.tyres
        ],
        # Deliberately omitted: Supplier, inspector, portal user, remarks and
        # attachment. This is operating history, not competitor information.
        "anonymised": True,
    }


def _validate_uploaded_file(file_url):
    file_doc = frappe.db.get_value(
        "File",
        {
            "file_url": file_url,
        },
        [
            "name",
            "owner",
        ],
        as_dict=True,
    )

    if not file_doc:
        frappe.throw(
            _(
                "The attachment has not finished "
                "uploading. Please upload it again."
            )
        )

    if file_doc.owner != frappe.session.user:
        frappe.throw(
            _("You cannot use another user's file."),
            frappe.PermissionError,
        )


def _attach_file_to_document(
    file_url,
    doctype,
    document_name,
    fieldname,
):
    file_name = frappe.db.get_value(
        "File",
        {
            "file_url": file_url,
        },
        "name",
    )

    if not file_name:
        return

    frappe.db.set_value(
        "File",
        file_name,
        {
            "attached_to_doctype": doctype,
            "attached_to_name": document_name,
            "attached_to_field": fieldname,
        },
        update_modified=False,
    )

def _default_tyre_rows():
    return [
        {"position": position}
        for position in STANDARD_TYRE_POSITIONS
    ]
