import json

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.controllers.website_list_for_contact import (
    get_customers_suppliers,
)


ALLOWED_SUPPLIER_SITES = [
    "GWAB",
    "Klipfontein",
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

    if frappe.request.method == "POST":
        _handle_post()

    context.site_options = _get_allowed_site_options()
    context.asset_options = _get_asset_options()

    draft = _get_editable_draft()

    context.form_values = {
        "draft_name": draft.name if draft else "",
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
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = (
            "/login?redirect-to=/tyre_survey_sup"
        )
        raise frappe.Redirect

    if "Supplier" not in frappe.get_roles(frappe.session.user):
        frappe.throw(
            _("Not permitted."),
            frappe.PermissionError,
        )


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

    if draft.portal_user != frappe.session.user:
        frappe.throw(
            _("You can only edit your own draft."),
            frappe.PermissionError,
        )

    if draft.sent_to_erp:
        frappe.throw(
            _("Submitted records cannot be edited."),
            frappe.PermissionError,
        )

    return draft


def _handle_post():
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

    if not site:
        frappe.throw(_("Site is required."))

    if not fleet_number:
        frappe.throw(_("Fleet Number is required."))

    if not survey_date:
        frappe.throw(_("Survey Date is required."))

    _validate_supplier_site_access(site)

    supplier = _validate_supplier_asset_access(
        fleet_number
    )

    tyre_rows = _parse_tyre_rows()

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

        if doc.portal_user != frappe.session.user:
            frappe.throw(
                _("You can only edit your own draft."),
                frappe.PermissionError,
            )

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


def _parse_tyre_rows():
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

    cleaned_rows = []

    for row_number, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue

        position = str(
            row.get("position") or ""
        ).strip()

        tyre_make = str(
            row.get("tyre_make") or ""
        ).strip()

        tyre_size = str(
            row.get("tyre_size") or ""
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

        otd = flt(row.get("otd"))
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
                "tread_pattern": str(
                    row.get("tread_pattern") or ""
                ).strip(),
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


def _get_user_suppliers():
    customers, suppliers = get_customers_suppliers(
        "Request for Quotation Supplier",
        frappe.session.user,
    )

    return suppliers or []


def _validate_supplier_asset_access(asset_name):
    """
    Temporary testing version.

    Allows any supplier-owned asset to be selected without
    checking the supplier linked to the portal user.
    """

    asset = frappe.db.get_value(
        "Asset",
        asset_name,
        [
            "name",
            "asset_owner",
            "supplier",
        ],
        as_dict=True,
    )

    if not asset:
        frappe.throw(
            _("Fleet Number does not exist.")
        )

    if asset.asset_owner != "Supplier":
        frappe.throw(
            _("Only supplier-owned Assets can be used."),
            frappe.PermissionError,
        )

    if not asset.supplier:
        frappe.throw(
            _("The selected Asset has no Supplier assigned.")
        )

    return asset.supplier


def _get_asset_options():
    """
    Temporary testing version.

    Shows all supplier-owned assets without checking whether
    the logged-in portal user is linked to that supplier.
    """

    return frappe.get_all(
        "Asset",
        filters={
            "asset_owner": "Supplier",
            "supplier": ["is", "set"],
        },
        pluck="name",
        order_by="name asc",
        limit_page_length=0,
    )

def _get_allowed_site_options():
    return frappe.get_all(
        "Location",
        filters={
            "name": [
                "in",
                ALLOWED_SUPPLIER_SITES,
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
                "You can only create records for "
                "GWAB or Klipfontein."
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


def _get_asset_information(asset_name):
    asset = frappe.get_doc("Asset", asset_name)

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

    return information


@frappe.whitelist(allow_guest=False)
def get_asset_information(asset_name=None):
    _validate_portal_access()

    asset_name = (
        asset_name
        or frappe.form_dict.get("asset_name")
        or ""
    ).strip()

    if not asset_name:
        frappe.throw(
            _("Fleet Number is required.")
        )

    _validate_supplier_asset_access(asset_name)

    return _get_asset_information(asset_name)


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
        {"position": "1 LF"},
        {"position": "2 RF"},
        {"position": "3 RM"},
        {"position": "4 RR"},
        {"position": "5 LR"},
        {"position": "6 LM"},
    ]