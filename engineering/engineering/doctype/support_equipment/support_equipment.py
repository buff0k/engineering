# Copyright (c) 2026
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.data import getdate
from frappe.utils import flt


SUPPORT_EQUIPMENT_CATEGORIES = [
    "Water Pump",
    "Lightning Plant",
    "Generator",
]


class SupportEquipment(Document):
    def before_validate(self):
        self._normalize_asset_links()
        self._fill_missing_child_values()

    def before_save(self):
        if self.shift_date:
            self.shift_date = getdate(self.shift_date)

        self._calculate_working_hours()
        self._evaluate_data_integrity()

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

    def _calculate_working_hours(self):
        for row in self.get("pre_use_assets") or []:
            if row.engine_start_hours is None or row.engine_end_hours is None:
                continue

            working_hours = round(
                flt(row.engine_end_hours) - flt(row.engine_start_hours),
                1,
            )

            if working_hours < 0:
                frappe.throw(
                    f"Negative working hours for asset {row.asset_name}. "
                    f"Start hours cannot be greater than end hours."
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

            if row.engine_start_hours is None:
                warnings.append(f"Missing start hours for {row.asset_name}.")

            if row.engine_end_hours is None:
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