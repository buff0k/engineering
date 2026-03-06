import frappe
from frappe.utils import getdate, add_days, today
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count
from collections import defaultdict


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

    included = (
        "LDV",
        "ADT",
        "Excavator",
        "Dozer",
        "Diesel Bowsers",
        "Drills",
        "Water Bowser",
        "Service Truck",
        "Grader",
        "TLB",
        "Loader",
    )

    q = (
        frappe.qb.from_(Asset)
        .select(
            Asset.asset_category.as_("category"),
            Count(Asset.name).as_("count"),
        )
        .where(Asset.docstatus == 1)                 # only submitted
        .where(Asset.asset_category.isin(included))  # include only these categories
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


@frappe.whitelist()
def get_doc_history_tree_meta(site=None, section=None):
    """
    FAST: returns ONLY counts (no doc rows)
      Site -> Section -> Fleet (+count)
    """
    filters = [["docstatus", "<", 2]]
    if site:
        filters.append(["site", "=", site])
    if section:
        filters.append(["sections", "=", section])

    rows = frappe.get_all(
        "Engineering Legals",
        filters=filters,
        fields=["site", "sections", "fleet_number"],
        order_by="site asc, sections asc, fleet_number asc",
        limit_page_length=0,  # let DB return all; still fast because fields are tiny
    )

    # site -> section -> fleet -> count
    counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for r in rows:
        st = (r.get("site") or "Unknown").strip()
        sec = (r.get("sections") or "Unknown").strip()
        fleet = (r.get("fleet_number") or "Unknown").strip()
        counts[st][sec][fleet] += 1

    out_sites = []
    for st in sorted(counts.keys()):
        st_node = {"label": st, "count": 0, "children": []}
        for sec in sorted(counts[st].keys()):
            sec_node = {"label": sec, "count": 0, "children": []}
            for fleet in sorted(counts[st][sec].keys()):
                n = int(counts[st][sec][fleet])
                sec_node["children"].append({"label": fleet, "count": n})
                sec_node["count"] += n
                st_node["count"] += n
            st_node["children"].append(sec_node)
        out_sites.append(st_node)

    return {"tree": out_sites}


@frappe.whitelist()
def get_doc_history_docs(site=None, section=None, fleet_number=None, limit=50, offset=0):
    """
    FAST: fetch docs for ONE fleet only (paged)
    """
    if not fleet_number:
        return {"rows": [], "limit": int(limit or 50), "offset": int(offset or 0)}

    filters = [["docstatus", "<", 2], ["fleet_number", "=", fleet_number]]
    if site:
        filters.append(["site", "=", site])
    if section:
        filters.append(["sections", "=", section])

    rows = frappe.get_all(
        "Engineering Legals",
        filters=filters,
        fields=["name", "fleet_number", "start_date", "expiry_date", "modified"],
        order_by="start_date desc, modified desc",
        limit_start=int(offset or 0),
        limit_page_length=int(limit or 50),
    )

    return {"rows": rows, "limit": int(limit or 50), "offset": int(offset or 0)}


@frappe.whitelist()
def get_doc_history_tree(site=None, section=None):
    """
    Doc History tree (ALL records):
      Site (filtered) -> Sections -> Fleet -> Docs
    """
    filters = [["docstatus", "<", 2]]
    if site:
        filters.append(["site", "=", site])
    if section:
        filters.append(["sections", "=", section])

    rows = frappe.get_all(
        "Engineering Legals",
        filters=filters,
        fields=[
            "name",
            "site",
            "sections",
            "fleet_number",
            "start_date",
            "expiry_date",
            "modified",
        ],
        order_by="site asc, sections asc, fleet_number asc, modified desc",
        limit_page_length=5000,
    )

    # Site -> Section -> Fleet -> Docs
    tree = {}
    for r in rows:
        st = (r.get("site") or "Unknown").strip()
        sec = (r.get("sections") or "Unknown").strip()
        fleet = (r.get("fleet_number") or "Unknown").strip()

        tree.setdefault(st, {}).setdefault(sec, {}).setdefault(fleet, []).append(
            {
                "name": r.get("name"),
                "fleet_number": r.get("fleet_number"),
                "start_date": r.get("start_date"),
                "expiry_date": r.get("expiry_date"),
                "modified": r.get("modified"),
                "site": st,
                "section": sec,
            }
        )

    out_sites = []
    for st, sections in tree.items():
        st_count = sum(len(docs) for fleets in sections.values() for docs in fleets.values())
        st_node = {"label": st, "count": st_count, "children": []}

        for sec, fleets in sections.items():
            sec_count = sum(len(docs) for docs in fleets.values())
            sec_node = {"label": sec, "count": sec_count, "children": []}

            for fleet, docs in fleets.items():
                sec_node["children"].append({"label": fleet, "count": len(docs), "rows": docs})

            sec_node["children"].sort(key=lambda x: x["label"])
            st_node["children"].append(sec_node)

        st_node["children"].sort(key=lambda x: x["label"])
        out_sites.append(st_node)

    out_sites.sort(key=lambda x: x["label"])

    return {"tree": out_sites}