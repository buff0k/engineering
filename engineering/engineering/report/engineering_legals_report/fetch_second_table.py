import frappe
from frappe.utils import getdate, add_days, today
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count


@frappe.whitelist()
def get_assets(site=None, section=None, as_at_date=None, bucket=None):
    from engineering.engineering.report.engineering_legals_report.engineering_legals_report import _assets_view

    as_at = getdate(as_at_date) if as_at_date else frappe.utils.getdate()
    cols, rows, msg, chart = _assets_view(as_at, site, section, bucket)
    return {"rows": rows}


@frappe.whitelist()
def get_asset_category_counts(site=None):
    """
    Returns counts of Assets per Asset Category for the selected Site (Location).
    Output: [{"category":"ADT","count":15}, ...]
    """
    asset_dt = "Asset"
    meta = frappe.get_meta(asset_dt)

    # choose which field holds site/location on Asset
    site_field = None
    for fn in ("location", "site", "custom_location", "custom_site"):
        if meta.has_field(fn):
            site_field = fn
            break

    # group by asset_category
    if not meta.has_field("asset_category"):
        return []

    Asset = DocType("Asset")

    excluded = ("All items group", "Lightning Plant", "Water pump")

    q = (
        frappe.qb.from_(Asset)
        .select(
            Asset.asset_category.as_("category"),
            Count(Asset.name).as_("count"),
        )
        .where(Asset.docstatus == 1)                 # only submitted
        .where(Asset.asset_category.notin(excluded)) # exclude categories
        .groupby(Asset.asset_category)
        .orderby(Count(Asset.name), order=frappe.qb.desc)
    )

    if site and site_field:
        q = q.where(getattr(Asset, site_field) == site)

    rows = q.run(as_dict=True)

    out = []
    for r in rows:
        if r.get("category"):
            out.append({"category": r["category"], "count": int(r.get("count") or 0)})

    return out




@frappe.whitelist()
def get_recent_submitted_legals(site=None, days=10, as_at_date=None):
    base = getdate(as_at_date) if as_at_date else today()
    cutoff = add_days(base, -int(days or 10))
    """
    Returns last N days submitted Engineering Legals (docstatus=1),
    for the selected Site (if provided).
    """
    cutoff = add_days(today(), -int(days or 10))

    filters = {
        "docstatus": 1,
        "modified": (">=", cutoff),
    }
    if site:
        filters["site"] = site

    rows = frappe.get_all(
        "Engineering Legals",
        filters=filters,
        fields=["name", "fleet_number", "modified"],
        order_by="modified desc",
        limit_page_length=200,
    )

    # Keep it simple: return in modified-desc order
    out = [{"name": r["name"], "fleet_number": r.get("fleet_number")} for r in rows if r.get("fleet_number")]
    return out