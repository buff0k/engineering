import frappe
from frappe.utils import getdate, add_days, today
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count
from collections import defaultdict


@frappe.whitelist()
def get_assets(site=None, section=None, asset=None, as_at_date=None, bucket=None):
    from engineering.engineering.report.engineering_legals_report.engineering_legals_report import _assets_view

    as_at = getdate(as_at_date) if as_at_date else frappe.utils.getdate()
    cols, rows, msg, chart = _assets_view(as_at, site, section, asset, bucket)
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
        "Lightning Plant",
        "Water pump",
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





RECENTLY_DONE_EARLY_DAYS = 10
RECENTLY_DONE_LATE_DAYS = 15


def _get_expiry_bucket(expiry_date, as_at):
    if not expiry_date:
        return ""

    days_left = (getdate(expiry_date) - as_at).days

    if days_left < 0:
        return "Overdue"
    if days_left <= 7:
        return "0-7 days"
    if days_left <= 14:
        return "8-14 days"
    if days_left <= 21:
        return "15-21 days"
    if days_left <= 28:
        return "22-28 days"

    return ""


def _is_recently_done(previous_expiry_date, latest_start_date):
    if not previous_expiry_date or not latest_start_date:
        return False

    previous_expiry_date = getdate(previous_expiry_date)
    latest_start_date = getdate(latest_start_date)

    window_start = add_days(previous_expiry_date, -RECENTLY_DONE_EARLY_DAYS)
    window_end = add_days(previous_expiry_date, RECENTLY_DONE_LATE_DAYS)

    return window_start <= latest_start_date <= window_end


def _build_combined_status(latest_doc, previous_doc, as_at):
    statuses = []

    prev_expiry = previous_doc.get("expiry_date") if previous_doc else None
    latest_start = latest_doc.get("start_date")
    latest_expiry = latest_doc.get("expiry_date")

    is_recent = _is_recently_done(prev_expiry, latest_start)
    expiry_bucket = _get_expiry_bucket(latest_expiry, as_at)

    if is_recent:
        statuses.append("✅ Recently done")

    if expiry_bucket and not (is_recent and expiry_bucket == "Overdue"):
        if expiry_bucket == "Overdue":
            statuses.append("❌ Overdue")
        else:
            statuses.append(expiry_bucket)

    return " | ".join(statuses) if statuses else "-"


@frappe.whitelist()
def get_category_summary(site=None, asset_category=None, section=None):
    """
    Returns latest Engineering Legals rows for one Asset Category,
    optionally filtered by Site and Section.

    Status rules:
    - Recently done = latest start_date is between 10 days before and 15 days after
      the PREVIOUS expiry_date for the same fleet + section
    - Also include expiry bucket if latest expiry falls in overdue / 0-28 day window
    - Example: "Recently done | 22-28 days"
    """
    if not asset_category:
        return {"rows": [], "sections": []}

    asset_dt = "Asset"
    meta = frappe.get_meta(asset_dt)

    site_field = None
    for fn in ("location", "site", "custom_location", "custom_site"):
        if meta.has_field(fn):
            site_field = fn
            break

    asset_filters = {
        "docstatus": 1,
        "asset_category": asset_category,
    }
    if site and site_field:
        asset_filters[site_field] = site

    fleet_numbers = frappe.get_all(
        "Asset",
        filters=asset_filters,
        pluck="name",
        limit_page_length=0,
    )

    if not fleet_numbers:
        return {"rows": [], "sections": []}

    legal_filters = [
        ["docstatus", "<", 2],
        ["fleet_number", "in", fleet_numbers],
    ]
    if site:
        legal_filters.append(["site", "=", site])
    if section:
        legal_filters.append(["sections", "=", section])

    docs = frappe.get_all(
        "Engineering Legals",
        filters=legal_filters,
        fields=[
            "name",
            "site",
            "sections",
            "fleet_number",
            "start_date",
            "expiry_date",
            "modified",
            "attach_paper",
        ],
        order_by="fleet_number asc, sections asc, start_date desc, expiry_date desc, modified desc",
        limit_page_length=0,
    )

    grouped = defaultdict(list)
    for d in docs:
        fleet = (d.get("fleet_number") or "").strip()
        sec = (d.get("sections") or "").strip()
        key = (fleet, sec)
        grouped[key].append(d)

    as_at = getdate(today())

    out = []
    for key, group_docs in grouped.items():
        latest_doc = group_docs[0]
        previous_doc = group_docs[1] if len(group_docs) > 1 else None

        out.append({
            "name": latest_doc.get("name"),
            "site": latest_doc.get("site"),
            "section": latest_doc.get("sections"),
            "fleet_number": latest_doc.get("fleet_number"),
            "start_date": latest_doc.get("start_date"),
            "expiry_date": latest_doc.get("expiry_date"),
            "modified": latest_doc.get("modified"),
            "attach_paper": latest_doc.get("attach_paper"),
            "status": _build_combined_status(latest_doc, previous_doc, as_at),
        })

    out.sort(key=lambda x: (
        (x.get("section") or "").lower(),
        (x.get("fleet_number") or "").lower(),
        str(x.get("expiry_date") or "")
    ))

    sections = sorted({
        (r.get("section") or "").strip()
        for r in out
        if (r.get("section") or "").strip()
    })

    return {
        "rows": out,
        "sections": sections,
    }




@frappe.whitelist()
def get_recent_submitted_legals(site=None, asset=None, days=10, as_at_date=None):
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
    if asset:
        filters["fleet_number"] = asset


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
def get_doc_history_tree_meta(site=None, section=None, asset=None):
    """
    FAST: returns ONLY counts (no doc rows)
      Site -> Section -> Fleet (+count)
    """
    filters = [["docstatus", "<", 2]]
    if site:
        filters.append(["site", "=", site])
    if section:
        filters.append(["sections", "=", section])
    if asset:
        filters.append(["fleet_number", "=", asset])



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
def get_doc_history_docs(site=None, section=None, fleet_number=None, asset=None, limit=50, offset=0):
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
    if asset:
        filters.append(["fleet_number", "=", asset])


        
    rows = frappe.get_all(
        "Engineering Legals",
        filters=filters,
        fields=["name", "fleet_number", "start_date", "expiry_date", "modified", "attach_paper"],
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