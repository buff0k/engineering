from collections import OrderedDict

import frappe


def execute(filters=None):
    columns = [
        {"label": "Default Account / Item", "fieldname": "account_item", "fieldtype": "Data", "width": 520},
        {"label": "Default Type", "fieldname": "default_type", "fieldtype": "Data", "width": 140},
        {"label": "Account", "fieldname": "account", "fieldtype": "Link", "options": "Account", "width": 280},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 260},
        {"label": "Item Group", "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 220},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 220},
        {"label": "Items", "fieldname": "item_count", "fieldtype": "Int", "width": 90},
        {"label": "Row Type", "fieldname": "row_type", "fieldtype": "Data", "hidden": 1},
    ]

    rows = frappe.db.sql("""
        select
            i.name as item_code,
            i.item_name,
            i.item_group,
            d.company,
            d.income_account,
            d.expense_account
        from `tabItem` i
        left join `tabItem Default` d on d.parent = i.name
        where i.disabled = 0
        order by d.company, d.expense_account, d.income_account, i.item_group, i.item_name
    """, as_dict=True)

    accounts = OrderedDict()

    for row in rows:
        default_accounts = []

        if row.expense_account:
            default_accounts.append(("Expense Account", row.expense_account))

        if row.income_account:
            default_accounts.append(("Income Account", row.income_account))

        if not default_accounts:
            default_accounts.append(("No Default Account", "No Default Account"))

        for default_type, account in default_accounts:
            key = f"{default_type}::{account}"

            if key not in accounts:
                accounts[key] = {
                    "default_type": default_type,
                    "account": account,
                    "company": row.company,
                    "item_groups": OrderedDict(),
                }

            item_group = row.item_group or "No Item Group"
            accounts[key]["item_groups"].setdefault(item_group, [])
            accounts[key]["item_groups"][item_group].append(row)

    data = []

    for key, account_data in accounts.items():
        total_items = sum(len(items) for items in account_data["item_groups"].values())

        data.append({
            "account_item": account_data["account"],
            "default_type": account_data["default_type"],
            "account": account_data["account"] if account_data["account"] != "No Default Account" else "",
            "item_code": "",
            "item_group": "",
            "company": account_data["company"],
            "item_count": total_items,
            "row_type": "account",
            "indent": 0,
            "is_group": 1,
        })

        for item_group, items in account_data["item_groups"].items():
            data.append({
                "account_item": item_group,
                "default_type": "",
                "account": "",
                "item_code": "",
                "item_group": item_group if item_group != "No Item Group" else "",
                "company": "",
                "item_count": len(items),
                "row_type": "item_group",
                "indent": 1,
                "is_group": 1,
            })

            for item in items:
                data.append({
                    "account_item": item.item_name,
                    "default_type": "",
                    "account": account_data["account"] if account_data["account"] != "No Default Account" else "",
                    "item_code": item.item_code,
                    "item_group": item.item_group,
                    "company": item.company,
                    "item_count": "",
                    "row_type": "item",
                    "indent": 2,
                    "is_group": 0,
                })

    return columns, data