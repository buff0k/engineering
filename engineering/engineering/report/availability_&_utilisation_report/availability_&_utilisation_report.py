import frappe
from frappe.utils import getdate, add_days


def _label_to_hhmm(label: str) -> str:
    if not label:
        return ""
    return label.split(" ")[0].strip()


def _parse_two_hourly(label: str):
    if not label or " To " not in label:
        return "", ""
    parts = label.split(" To ", 1)
    start_hhmm = _label_to_hhmm(parts[0].strip())
    end_hhmm = _label_to_hhmm(parts[1].strip())
    return start_hhmm, end_hhmm


def _day_anchor_offset(start_hhmm: str, is_next_day_variant: bool) -> int:
    if not start_hhmm:
        return 0
    if is_next_day_variant and start_hhmm == "06:00":
        return -1
    hh = int(start_hhmm.split(":")[0])
    if 0 <= hh <= 5:
        return -1
    return 0


def _r1(x):
    try:
        return round(float(x or 0), 1)
    except Exception:
        return 0.0


def _round_row_1dp(r: dict) -> dict:
    # Round values (data-side) - and column precision will enforce display-side.
    for k in ("required_hrs", "worked_hrs", "brkdwn_hrs", "avail_hrs", "lost_hrs", "availability", "utilisation"):
        r[k] = _r1(r.get(k))
    return r


def _new_totals():
    return {
        "req": 0.0,
        "work": 0.0,
        "brkdwn": 0.0,
        "avail_hrs": 0.0,
        "lost": 0.0,
        "w_req": 0.0,
        "w_av": 0.0,
        "w_ut": 0.0,
    }


def _add_to_totals(t, rr):
    req = float(rr.get("required_hrs") or 0)
    t["req"] += req
    t["work"] += float(rr.get("worked_hrs") or 0)
    t["brkdwn"] += float(rr.get("brkdwn_hrs") or 0)
    t["avail_hrs"] += float(rr.get("avail_hrs") or 0)
    t["lost"] += float(rr.get("lost_hrs") or 0)

    t["w_req"] += req
    t["w_av"] += float(rr.get("availability") or 0) * req
    t["w_ut"] += float(rr.get("utilisation") or 0) * req


def _finalise_pct(t):
    if t["w_req"] > 0:
        av = t["w_av"] / t["w_req"]
        ut = t["w_ut"] / t["w_req"]
    else:
        av = 0.0
        ut = 0.0
    return _r1(av), _r1(ut)


def _agg_rows(rows):
    t = _new_totals()
    for rr in rows:
        _add_to_totals(t, rr)
    av, ut = _finalise_pct(t)
    return {
        "required_hrs": _r1(t["req"]),
        "worked_hrs": _r1(t["work"]),
        "brkdwn_hrs": _r1(t["brkdwn"]),
        "avail_hrs": _r1(t["avail_hrs"]),
        "lost_hrs": _r1(t["lost"]),
        "availability": av,
        "utilisation": ut,
    }


def _merge_comments(rows):
    seen = set()
    out = []
    for r in rows:
        c = (r.get("comment") or "").strip()
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return " | ".join(out)


def execute(filters=None):
    filters = frappe._dict(filters or {})

    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    if not from_date or not to_date:
        frappe.throw("Start Date and End Date are required")
    if from_date > to_date:
        frappe.throw("Start Date cannot be after End Date")

    site = (filters.get("site") or "").strip()
    all_sites = int(filters.get("all_sites") or 0)

    hourly = (filters.get("hourly") or "").strip()
    two_hourly = (filters.get("two_hourly") or "").strip()

    chosen = hourly or two_hourly
    chosen_mode = "hourly" if hourly else ("two_hourly" if two_hourly else "")
    is_next_day_variant = "(next day)" in chosen if chosen else False

    start_hhmm = ""
    if chosen:
        clean = chosen.replace("(next day)", "").strip()
        if chosen_mode == "hourly":
            start_hhmm = _label_to_hhmm(clean)
        else:
            start_hhmm, _end = _parse_two_hourly(clean)

    anchor_offset = _day_anchor_offset(start_hhmm, is_next_day_variant)

    q_from = add_days(from_date, anchor_offset)
    q_to = add_days(to_date, anchor_offset)

    # ✅ IMPORTANT: precision=1 forces the grid to display 1 decimal (instead of 3)
    columns = [
        {"label": "Category", "fieldname": "category", "fieldtype": "Data", "width": 140},
        {"label": "Date", "fieldname": "shift_date", "fieldtype": "Date", "width": 110},
        {"label": "Asset", "fieldname": "asset", "fieldtype": "Data", "width": 120},
        {"label": "Shift", "fieldname": "shift", "fieldtype": "Data", "width": 70},
        {"label": "Site", "fieldname": "site", "fieldtype": "Data", "width": 110},

        {"label": "Req Hrs", "fieldname": "required_hrs", "fieldtype": "Float", "precision": 1, "width": 90},
        {"label": "Work Hrs", "fieldname": "worked_hrs", "fieldtype": "Float", "precision": 1, "width": 90},
        {"label": "Brkdwn", "fieldname": "brkdwn_hrs", "fieldtype": "Float", "precision": 1, "width": 90},
        {"label": "Avail Hrs", "fieldname": "avail_hrs", "fieldtype": "Float", "precision": 1, "width": 90},
        {"label": "Lost Hrs", "fieldname": "lost_hrs", "fieldtype": "Float", "precision": 1, "width": 90},

        {"label": "Avail %", "fieldname": "availability", "fieldtype": "Percent", "precision": 1, "width": 90},
        {"label": "Util %", "fieldname": "utilisation", "fieldtype": "Percent", "precision": 1, "width": 90},

        {"label": "Comment", "fieldname": "comment", "fieldtype": "Data", "width": 260},
    ]

    conditions = ["au.shift_date BETWEEN %(from_date)s AND %(to_date)s"]
    params = {"from_date": q_from, "to_date": q_to}

    if site and not all_sites:
        conditions.append("au.location LIKE %(site)s")
        params["site"] = f"%{site}%"

    sql = f"""
        SELECT
            IFNULL(au.asset_category, 'Uncategorised') AS category,
            au.shift_date,
            au.shift,
            au.asset_name AS asset,
            au.location AS site,

            IFNULL(au.shift_required_hours, 0) AS required_hrs,
            IFNULL(au.shift_working_hours, 0) AS worked_hrs,
            IFNULL(au.shift_breakdown_hours, 0) AS brkdwn_hrs,
            IFNULL(au.shift_available_hours, 0) AS avail_hrs,
            IFNULL(au.shift_other_lost_hours, 0) AS lost_hrs,
            IFNULL(au.plant_shift_availability, 0) AS availability,
            IFNULL(au.plant_shift_utilisation, 0) AS utilisation,

            (
                SELECT GROUP_CONCAT(bh.breakdown_reason_updates SEPARATOR ' | ')
                FROM `tabBreakdown History` bh
                WHERE
                    bh.location = au.location
                    AND bh.asset_name = au.asset_name
                    AND DATE(bh.update_date_time) = au.shift_date
                    AND IFNULL(bh.exclude_from_au, 0) = 0
            ) AS comment

        FROM `tabAvailability and Utilisation` au
        WHERE {" AND ".join(conditions)}
        ORDER BY
            category ASC,
            au.shift_date ASC,
            au.asset_name ASC,
            FIELD(au.shift, 'Day', 'Night') ASC
    """

    raw = frappe.db.sql(sql, params, as_dict=True)

    # Round leaf rows too (data-side)
    for r in raw:
        _round_row_1dp(r)

    # Tree: category -> date -> asset -> shift
    tree = {}
    for r in raw:
        cat = r["category"]
        dt = r["shift_date"]
        ass = r["asset"]
        sh = r["shift"]
        tree.setdefault(cat, {}).setdefault(dt, {}).setdefault(ass, {}).setdefault(sh, []).append(r)

    out = []

    for cat in sorted(tree.keys()):
        for dt in sorted(tree[cat].keys()):
            # Level 0: Category+Date totals
            cat_date_rows = []
            site_val = site if (site and not all_sites) else ""

            for ass in tree[cat][dt]:
                for sh in tree[cat][dt][ass]:
                    cat_date_rows.extend(tree[cat][dt][ass][sh])
                    if not site_val and tree[cat][dt][ass][sh]:
                        site_val = tree[cat][dt][ass][sh][0].get("site") or ""

            cat_date_tot = _agg_rows(cat_date_rows)

            out.append({
                "indent": 0,
                "is_group": 1,
                "category": cat,
                "shift_date": dt,
                "asset": "",
                "shift": "",
                "site": site_val,
                "comment": "",
                **cat_date_tot,
            })

            # Level 1: Asset totals
            for ass in sorted(tree[cat][dt].keys()):
                all_shift_rows = []
                asset_site = ""

                for sh in tree[cat][dt][ass]:
                    all_shift_rows.extend(tree[cat][dt][ass][sh])
                    if not asset_site and tree[cat][dt][ass][sh]:
                        asset_site = tree[cat][dt][ass][sh][0].get("site") or ""

                asset_tot = _agg_rows(all_shift_rows)
                asset_comment = _merge_comments(all_shift_rows)

                out.append({
                    "indent": 1,
                    "is_group": 1,
                    "category": cat,
                    "shift_date": dt,
                    "asset": ass,
                    "shift": "",
                    "site": asset_site,
                    "comment": asset_comment,
                    **asset_tot,
                })

                # Level 2: Day/Night leaf rows
                for sh in ["Day", "Night"]:
                    if sh not in tree[cat][dt][ass]:
                        continue

                    leaf_rows = tree[cat][dt][ass][sh]
                    leaf_tot = _agg_rows(leaf_rows)
                    leaf_comment = _merge_comments(leaf_rows)

                    out.append({
                        "indent": 2,
                        "is_group": 0,
                        "category": cat,
                        "shift_date": dt,
                        "asset": ass,
                        "shift": sh,
                        "site": asset_site,
                        "comment": leaf_comment,
                        **leaf_tot,
                    })

    return columns, out