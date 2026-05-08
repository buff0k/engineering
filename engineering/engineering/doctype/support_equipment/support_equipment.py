# Copyright (c) 2026
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from frappe.utils.data import getdate
from frappe.utils import flt, add_days


SUPPORT_EQUIPMENT_CATEGORIES = [
    "Water Pump",
    "Lightning Plant",
    "Generator",
]


class SupportEquipment(Document):
    def before_validate(self):
        self._normalize_asset_links()
        self._fill_missing_child_values()
        self._populate_opening_hours_from_previous_shift()

    def before_save(self):
        if self.shift_date:
            self.shift_date = getdate(self.shift_date)

        self._populate_opening_hours_from_previous_shift()
        self._calculate_working_hours()
        self._evaluate_data_integrity()

    def on_update(self):
        self._update_next_shift_opening_hours()

    def _normalize_asset_links(self):
        rows = self.get("pre_use_assets") or []

        values = sorted({
            row.asset_name
            for row in rows
            if getattr(row, "asset_name", None)
        })

        if not values:
            return

        existing_names = set(
            frappe.get_all(
                "Asset",
                filters={"name": ["in", values]},
                pluck="name",
            )
        )

        unknown_values = [
            value for value in values
            if value not in existing_names
        ]

        if not unknown_values:
            return

        matches = frappe.get_all(
            "Asset",
            filters={"asset_name": ["in", unknown_values]},
            fields=["name", "asset_name"],
        )

        asset_name_to_real_name = {
            match.asset_name: match.name
            for match in matches
            if match.get("asset_name")
        }

        for row in rows:
            value = getattr(row, "asset_name", None)

            if value and value in asset_name_to_real_name:
                row.asset_name = asset_name_to_real_name[value]

    def _fill_missing_child_values(self):
        rows = self.get("pre_use_assets") or []

        asset_names = [
            row.asset_name
            for row in rows
            if getattr(row, "asset_name", None)
        ]

        if not asset_names:
            return

        assets = frappe.get_all(
            "Asset",
            filters={"name": ["in", asset_names]},
            fields=[
                "name",
                "asset_name",
                "item_name",
                "asset_category",
            ],
        )

        asset_map = {
            asset.name: asset
            for asset in assets
        }

        for row in rows:
            asset = asset_map.get(row.asset_name)

            if not asset:
                continue

            if not getattr(row, "plant_number", None):
                row.plant_number = asset.asset_name or ""

            if not getattr(row, "equipment_category", None):
                row.equipment_category = asset.asset_category or ""

            if not getattr(row, "model", None):
                row.model = asset.item_name or ""

    def _populate_opening_hours_from_previous_shift(self):
        if self.shift not in ["Day", "Night"]:
            return

        if not self.location or not self.shift_date:
            return

        asset_names = [
            row.asset_name
            for row in self.get("pre_use_assets") or []
            if getattr(row, "asset_name", None)
        ]

        if not asset_names:
            return

        opening_hours_map = get_previous_shift_closing_hours(
            location=self.location,
            shift_date=self.shift_date,
            shift=self.shift,
            asset_names=asset_names,
            current_docname=self.name,
        )

        for row in self.get("pre_use_assets") or []:
            if not row.asset_name:
                continue

            opening_hours = opening_hours_map.get(row.asset_name)

            if opening_hours is None:
                continue

            row.engine_start_hours = flt(opening_hours)

    def _calculate_working_hours(self):
        for row in self.get("pre_use_assets") or []:
            start_hours = row.engine_start_hours
            end_hours = row.engine_end_hours

            if start_hours in [None, ""]:
                row.working_hours = 0
                continue

            # End hours = 0 means not captured yet.
            # It must be allowed to save.
            if end_hours in [None, "", 0, "0"]:
                row.working_hours = 0
                continue

            start_hours = flt(start_hours)
            end_hours = flt(end_hours)

            working_hours = round(end_hours - start_hours, 0)

            if working_hours < 0:
                frappe.throw(
                    f"Negative working hours for asset {row.asset_name}. "
                    f"Engine End Hours cannot be less than Engine Start Hours."
                )

            if working_hours > 12:
                frappe.throw(
                    f"Working hours above 12 for asset {row.asset_name}. "
                    f"Please check engine start and end hours."
                )

            row.working_hours = working_hours

    def _evaluate_data_integrity(self):
        errors = []
        warnings = []

        selected_category = self.equipment_category

        if selected_category and selected_category not in SUPPORT_EQUIPMENT_CATEGORIES:
            errors.append(
                f"Invalid Equipment Category selected: {selected_category}"
            )

        for row in self.get("pre_use_assets") or []:
            if not row.asset_name:
                errors.append("Asset is missing on one or more rows.")
                continue

            if selected_category and row.equipment_category:
                if row.equipment_category != selected_category:
                    warnings.append(
                        f"{row.asset_name} category is {row.equipment_category}, "
                        f"but document category is {selected_category}."
                    )

            if not selected_category and not row.equipment_category:
                warnings.append(
                    f"Equipment Category is missing for {row.asset_name}."
                )

            start_hours = row.engine_start_hours
            end_hours = row.engine_end_hours

            if start_hours in [None, ""]:
                warnings.append(f"Missing start hours for {row.asset_name}.")

            if end_hours in [None, "", 0, "0"]:
                warnings.append(f"Missing end hours for {row.asset_name}.")

            if row.working_hours == 0:
                warnings.append(f"Zero working hours for {row.asset_name}.")

        if errors:
            self.data_integ_indicator = "🔴"
            self.data_integrity_summary = "<br>".join(errors + warnings)

        elif warnings:
            self.data_integ_indicator = "🟠"
            self.data_integrity_summary = "<br>".join(warnings)

        else:
            self.data_integ_indicator = "🟢"
            self.data_integrity_summary = "<p><b>All checks passed.</b></p>"

    def _update_next_shift_opening_hours(self):
        if self.shift not in ["Day", "Night"]:
            return

        if not self.location or not self.shift_date:
            return

        next_shift_details = get_next_shift_details(
            shift_date=self.shift_date,
            shift=self.shift,
        )

        if not next_shift_details:
            return

        next_docs = frappe.get_all(
            "Support Equipment",
            filters={
                "location": self.location,
                "shift_date": next_shift_details["shift_date"],
                "shift": next_shift_details["shift"],
                "docstatus": ["<", 2],
                "name": ["!=", self.name],
            },
            pluck="name",
        )

        if not next_docs:
            return

        current_end_hours = {}

        for row in self.get("pre_use_assets") or []:
            if not row.asset_name:
                continue

            if row.engine_end_hours in [None, "", 0, "0"]:
                continue

            current_end_hours[row.asset_name] = flt(row.engine_end_hours)

        if not current_end_hours:
            return

        for next_doc_name in next_docs:
            next_doc = frappe.get_doc("Support Equipment", next_doc_name)
            updated = False

            for next_row in next_doc.get("pre_use_assets") or []:
                if not next_row.asset_name:
                    continue

                if next_row.asset_name not in current_end_hours:
                    continue

                next_row.engine_start_hours = current_end_hours[next_row.asset_name]

                if next_row.engine_end_hours not in [None, "", 0, "0"]:
                    working_hours = round(
                        flt(next_row.engine_end_hours) - flt(next_row.engine_start_hours),
                        0,
                    )

                    if working_hours >= 0:
                        next_row.working_hours = working_hours
                else:
                    next_row.working_hours = 0

                updated = True

            if updated:
                next_doc.flags.ignore_validate_update_after_submit = True
                next_doc.save(ignore_permissions=True)


def get_previous_shift_details(shift_date, shift):
    shift_date = getdate(shift_date)

    if shift == "Night":
        return {
            "shift_date": shift_date,
            "shift": "Day",
        }

    if shift == "Day":
        return {
            "shift_date": add_days(shift_date, -1),
            "shift": "Night",
        }

    return None


def get_next_shift_details(shift_date, shift):
    shift_date = getdate(shift_date)

    if shift == "Day":
        return {
            "shift_date": shift_date,
            "shift": "Night",
        }

    if shift == "Night":
        return {
            "shift_date": add_days(shift_date, 1),
            "shift": "Day",
        }

    return None


def get_previous_shift_closing_hours(
    location,
    shift_date,
    shift,
    asset_names,
    current_docname=None,
):
    if not asset_names:
        return {}

    previous_shift = get_previous_shift_details(
        shift_date=shift_date,
        shift=shift,
    )

    if not previous_shift:
        return {}

    conditions = [
        "parent.location = %(location)s",
        "parent.shift_date = %(previous_shift_date)s",
        "parent.shift = %(previous_shift)s",
        "parent.docstatus < 2",
        "child.asset_name in %(asset_names)s",
    ]

    values = {
        "location": location,
        "previous_shift_date": previous_shift["shift_date"],
        "previous_shift": previous_shift["shift"],
        "asset_names": tuple(asset_names),
    }

    if current_docname and current_docname != "New Support Equipment":
        conditions.append("parent.name != %(current_docname)s")
        values["current_docname"] = current_docname

    where_clause = " and ".join(conditions)

    records = frappe.db.sql(
        f"""
        select
            child.asset_name,
            child.engine_end_hours
        from `tabSupport Equipment` parent
        inner join `tabSupport Equipment Assets` child
            on child.parent = parent.name
        where {where_clause}
        order by parent.modified desc
        """,
        values,
        as_dict=True,
    )

    result = {}

    for record in records:
        if record.asset_name not in result:
            result[record.asset_name] = record.engine_end_hours

    return result


@frappe.whitelist()
def get_support_equipment_assets(location=None, equipment_category=None):
    if not location:
        frappe.throw("Site is required.")

    filters = {
        "location": location,
        "asset_category": ["in", SUPPORT_EQUIPMENT_CATEGORIES],
        "docstatus": 1,
    }

    if equipment_category:
        if equipment_category not in SUPPORT_EQUIPMENT_CATEGORIES:
            frappe.throw(f"Invalid Equipment Category: {equipment_category}")

        filters["asset_category"] = equipment_category

    return frappe.get_all(
        "Asset",
        filters=filters,
        fields=[
            "name",
            "asset_name",
            "item_name",
            "asset_category",
        ],
        order_by="asset_category asc, asset_name asc",
        limit_page_length=1000,
    )


@frappe.whitelist()
def get_opening_hours_from_previous_shift(
    location=None,
    shift_date=None,
    shift=None,
    asset_names=None,
):
    if not location:
        frappe.throw("Site is required.")

    if not shift_date:
        frappe.throw("Shift Date is required.")

    if not shift:
        frappe.throw("Shift is required.")

    if isinstance(asset_names, str):
        asset_names = json.loads(asset_names)

    asset_names = asset_names or []

    return get_previous_shift_closing_hours(
        location=location,
        shift_date=shift_date,
        shift=shift,
        asset_names=asset_names,
    )