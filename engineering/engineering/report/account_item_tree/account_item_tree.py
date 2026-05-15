import re
from collections import OrderedDict

import frappe


def execute(filters=None):
    columns = [
        {"label": "Account / Item", "fieldname": "account_item", "fieldtype": "Data", "width": 520},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 260},
        {"label": "Item Group", "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 240},
        {"label": "Items", "fieldname": "item_count", "fieldtype": "Int", "width": 90},
        {"label": "Row Type", "fieldname": "row_type", "fieldtype": "Data", "hidden": 1},
    ]

    items = frappe.db.sql("""
        select item_code, item_name, item_group
        from `tabItem`
        where disabled = 0
        order by item_code, item_group, item_name
    """, as_dict=True)

    accounts = OrderedDict()

    for item in items:
        match = re.match(r"^(\d+)\s*-\s*(.+)$", item.item_code or "")
        if not match:
            continue

        account_code = match.group(1)
        account_name = match.group(2).strip()
        item_code = item.item_code
        item_group = item.item_group or "No Item Group"

        if account_code not in accounts:
            accounts[account_code] = {
                "label": f"{account_code} - {account_name}",
                "codes": OrderedDict(),
            }

        accounts[account_code]["codes"].setdefault(item_code, OrderedDict())
        accounts[account_code]["codes"][item_code].setdefault(item_group, [])
        accounts[account_code]["codes"][item_code][item_group].append(item)

    data = []

    for account_code, account in accounts.items():
        total_items = sum(
            len(group_items)
            for code_groups in account["codes"].values()
            for group_items in code_groups.values()
        )

        data.append({
            "account_item": account["label"],
            "item_code": "",
            "item_group": "",
            "item_count": total_items,
            "row_type": "account",
            "indent": 0,
            "is_group": 1,
        })

        for item_code, groups in account["codes"].items():
            code_item_count = sum(len(group_items) for group_items in groups.values())

            data.append({
                "account_item": item_code,
                "item_code": item_code,
                "item_group": "",
                "item_count": code_item_count,
                "row_type": "account_code",
                "indent": 1,
                "is_group": 1,
            })

            for item_group, group_items in groups.items():
                data.append({
                    "account_item": item_group,
                    "item_code": "",
                    "item_group": item_group,
                    "item_count": len(group_items),
                    "row_type": "item_group",
                    "indent": 2,
                    "is_group": 1,
                })

                for item in group_items:
                    data.append({
                        "account_item": item.item_name,
                        "item_code": item.item_code,
                        "item_group": item.item_group,
                        "item_count": "",
                        "row_type": "item",
                        "indent": 3,
                        "is_group": 0,
                    })

    return columns, data