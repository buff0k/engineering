# Server path:
# apps/engineering/engineering/templates/pages/tyre_survey_list.py
# v11: Create missing Tyre Master records only when a reviewed
# supplier draft is permanently sent to ERP.

import json

import frappe
from frappe import _
from frappe.utils import now

from engineering.templates.pages.tyre_portal_security import (
    assert_draft_access,
    get_portal_supplier,
    is_supplier_manager,
    validate_portal_access,
)


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


# Permanent specification values copied from a reviewed survey
# row when its serial number does not yet exist in Tyre Master.
TYRE_MASTER_SOURCE_FIELDS = [
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


# These values do not identify a physical tyre and must never
# become permanent Tyre Master names.
INVALID_TYRE_MASTER_SERIALS = {
    "",
    "NSN",
    "DEFACED",
    "N/A",
    "NA",
    "UNKNOWN",
    "NO SERIAL",
}


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    context.title = "My Tyre Surveys"

    _validate_portal_access()

    supplier = get_portal_supplier()
    context.is_supplier_manager = is_supplier_manager()

    filters = {"supplier": supplier}
    if not context.is_supplier_manager:
        filters["portal_user"] = frappe.session.user

    context.records = frappe.get_all(
        "Tyre Survey Supplier Portal Draft",
        filters=filters,
        fields=[
            "name",
            "portal_user",
            "site",
            "fleet_number",
            "survey_date",
            "sent_to_erp",
            "erp_document",
            "modified",
        ],
        order_by="modified desc",
        limit_page_length=200,
    )

    for row in context.records:
        row.status = (
            "Submitted"
            if row.sent_to_erp
            else "Draft"
        )
        row.can_edit = (
            not row.sent_to_erp
            and row.portal_user == frappe.session.user
        )
        row.can_send = (
            not row.sent_to_erp
            and (
                row.portal_user == frappe.session.user
                or context.is_supplier_manager
            )
        )
        row.captured_by = frappe.db.get_value(
            "User",
            row.portal_user,
            "full_name",
        ) or row.portal_user


def _validate_portal_access():
    validate_portal_access("/tyre_survey_list")


def _validate_draft_supplier(supplier):
    if not supplier or supplier != get_portal_supplier():
        frappe.throw(
            _("The draft does not belong to your Supplier."),
            frappe.PermissionError,
        )


def _validate_supplier_asset_access(
    asset_name,
):
    """
    Temporary testing version.

    Allows all ADT Assets, regardless of asset owner or the
    Supplier linked to the logged-in portal user.
    """

    asset = frappe.db.get_value(
        "Asset",
        asset_name,
        [
            "name",
            "asset_category",
        ],
        as_dict=True,
    )

    if not asset:
        frappe.throw(
            _("Fleet Number does not exist.")
        )

    if asset.asset_category != "ADT":
        frappe.throw(
            _(
                "Only ADT Assets can be used."
            ),
            frappe.PermissionError,
        )

    return asset


def _normalise_serial_number(serial_number):
    return str(serial_number or "").strip().upper()


def _get_tyre_master_values(
    tyre,
    draft,
    supplier,
):
    """
    Builds a Tyre Master using only fields that exist on the
    installed Tyre Master DocType.  This keeps the send flow
    compatible with optional lifecycle fields.
    """

    meta = frappe.get_meta("Tyre Master")

    values = {
        "doctype": "Tyre Master",
        "serial_number": _normalise_serial_number(
            tyre.get("serial_number")
        ),
    }

    for fieldname in TYRE_MASTER_SOURCE_FIELDS:
        if meta.has_field(fieldname):
            values[fieldname] = tyre.get(fieldname)

    optional_values = {
        "supplier": supplier,
        "active": 1,
        "current_asset": draft.fleet_number,
        "current_position": tyre.get("position"),
    }

    for fieldname, value in optional_values.items():
        if meta.has_field(fieldname):
            values[fieldname] = value

    status_field = meta.get_field("status")

    if status_field:
        status_options = {
            option.strip()
            for option in str(
                status_field.options or ""
            ).splitlines()
            if option.strip()
        }

        if "In Service" in status_options:
            values["status"] = "In Service"

    return values


def _create_missing_tyre_masters(
    draft,
    supplier,
):
    """
    Creates one Tyre Master for each valid unknown serial in a
    reviewed draft.  Existing masters are deliberately left
    unchanged.
    """

    created = []

    for row_number, tyre in enumerate(
        draft.tyres,
        start=1,
    ):
        serial_number = _normalise_serial_number(
            tyre.get("serial_number")
        )

        if serial_number in INVALID_TYRE_MASTER_SERIALS:
            continue

        if frappe.db.exists(
            "Tyre Master",
            {
                "serial_number": serial_number,
            },
        ):
            continue

        missing_fields = []

        if not str(
            tyre.get("tyre_make") or ""
        ).strip():
            missing_fields.append("Tyre Make")

        if not str(
            tyre.get("tyre_size") or ""
        ).strip():
            missing_fields.append("Tyre Size")

        if not tyre.get("otd"):
            missing_fields.append(
                "Original Tread Depth"
            )

        if missing_fields:
            frappe.throw(
                _(
                    "Cannot create Tyre Master {0} from "
                    "tyre row {1}. Complete: {2}."
                ).format(
                    serial_number,
                    row_number,
                    ", ".join(missing_fields),
                )
            )

        tyre_master = frappe.get_doc(
            _get_tyre_master_values(
                tyre,
                draft,
                supplier,
            )
        )

        tyre_master.insert(
            ignore_permissions=True
        )

        created.append(tyre_master.name)

    return created


def _move_attachment_to_erp(
    file_url,
    document_name,
):
    if not file_url:
        return

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
            "attached_to_doctype":
                "Tyre Survey",
            "attached_to_name":
                document_name,
            "attached_to_field":
                "survey_attachment",
        },
        update_modified=False,
    )


@frappe.whitelist(
    allow_guest=False
)
def send_tyre_surveys(
    names=None,
):
    _validate_portal_access()

    if names is None:
        names = frappe.form_dict.get(
            "names"
        )

    if isinstance(names, str):
        try:
            names = json.loads(names)
        except (TypeError, ValueError):
            names = [names]

    if not isinstance(names, list):
        names = [names]

    names = [
        str(name).strip()
        for name in names
        if str(name).strip()
    ]

    if not names:
        frappe.throw(
            _("No records selected.")
        )

    sent = []

    for name in names:
        draft = frappe.get_doc(
            "Tyre Survey Supplier Portal Draft",
            name,
        )

        assert_draft_access(draft, write=False)

        if draft.sent_to_erp:
            continue

        _validate_supplier_asset_access(
            draft.fleet_number
        )

        _validate_draft_supplier(
            draft.supplier
        )

        supplier = draft.supplier

        if not draft.tyres:
            frappe.throw(
                _(
                    "Draft {0} does not "
                    "contain any tyres."
                ).format(draft.name)
            )

        existing_document = (
            frappe.db.exists(
                "Tyre Survey",
                {
                    "supplier": supplier,
                    "fleet_number":
                        draft.fleet_number,
                    "survey_date":
                        draft.survey_date,
                },
            )
        )

        if existing_document:
            frappe.throw(
                _(
                    "A Tyre Survey already "
                    "exists for {0} on {1}: {2}"
                ).format(
                    draft.fleet_number,
                    draft.survey_date,
                    existing_document,
                )
            )

        erp_doc = frappe.get_doc(
            {
                "doctype": "Tyre Survey",
                "supplier": supplier,
                "site": draft.site,
                "fleet_number":
                    draft.fleet_number,
                "survey_date":
                    draft.survey_date,
                "survey_attachment":
                    draft.survey_attachment,
                "general_remarks":
                    draft.general_remarks,
                "inspector_name":
                    draft.get("inspector_name"),
                "portal_user": draft.portal_user,
            }
        )

        for tyre in draft.tyres:
            tyre_values = {
                fieldname:
                    tyre.get(fieldname)
                for fieldname
                in TYRE_ITEM_FIELDS
            }

            tyre_values["serial_number"] = (
                _normalise_serial_number(
                    tyre.get("serial_number")
                )
            )

            erp_doc.append(
                "tyres",
                tyre_values,
            )

        erp_doc.insert(
            ignore_permissions=True
        )

        created_tyre_masters = (
            _create_missing_tyre_masters(
                draft,
                supplier,
            )
        )

        _move_attachment_to_erp(
            draft.survey_attachment,
            erp_doc.name,
        )

        draft.db_set(
            "sent_to_erp",
            1,
            update_modified=False,
        )

        draft.db_set(
            "sent_on",
            now(),
            update_modified=False,
        )

        draft.db_set(
            "erp_document",
            erp_doc.name,
            update_modified=False,
        )

        sent.append(
            {
                "draft": draft.name,
                "erp_document":
                    erp_doc.name,
                "created_tyre_masters":
                    created_tyre_masters,
            }
        )

    frappe.db.commit()

    return {
        "ok": True,
        "sent": sent,
    }
