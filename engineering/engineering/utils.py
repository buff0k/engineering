import frappe
from frappe.utils import today, flt


def check_app_permission():
    """Check if the user has permission to access the app (for showing it on the app screen)"""
    # Administrator always has access
    if frappe.session.user == "Administrator":
        return True

    # Check if the user has any of the required roles
    required_roles = ["System Manager", "Engineering Manager", "Engineering User"]
    user_roles = frappe.get_roles(frappe.session.user)

    # Grant access if the user has at least one of the required roles
    if any(role in user_roles for role in required_roles):
        return True

    return False


@frappe.whitelist()
def get_assets_for_site(site):
    """
    Returns a list of dicts for the Service Schedule child table:
    [
      {
        "asset": "<Asset name>",
        "date": "<latest shift_date or today>",
        "hour_meter": <latest eng_hrs_end>,
        "service_interval": <next service interval>
      },
      ...
    ]
    """

    # 1) Assets at this site (no 'disabled' filter – your Asset doctype doesn't have that field)
    assets = frappe.get_all(
        "Asset",
        filters={
            "location": site
        },
        fields=["name", "asset_name", "asset_category"]
    )

    result = []

    for a in assets:
        asset_name = a.name

        # 2) Latest Pre-use reading for this asset
        latest = frappe.db.sql(
            """
            SELECT
                p.shift_date,
                c.eng_hrs_end
            FROM `tabPre-use Assets` c
            INNER JOIN `tabPre-Use Hours` p
                ON c.parent = p.name
            WHERE
                c.asset_name = %s
                AND p.location = %s
                AND p.docstatus = 1
            ORDER BY
                p.shift_date DESC,
                p.creation DESC
            LIMIT 1
            """,
            (asset_name, site),
            as_dict=True,
        )

        if latest:
            row = latest[0]
            date = row.shift_date
            hour_meter = flt(row.eng_hrs_end)
        else:
            date = today()
            hour_meter = 0

        # 3) Choose next service interval
        intervals = [250, 500, 750, 1000, 2000]
        next_interval = intervals[-1]
        for i in intervals:
            if hour_meter <= i:
                next_interval = i
                break

        result.append({
            "asset": asset_name,
            "date": date,
            "hour_meter": hour_meter,
            "service_interval": next_interval
        })

    return result
