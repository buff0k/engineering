import requests
import frappe
from frappe.utils import now


def _to_float(v):
    if v in (None, "", "null"):
        return None
    try:
        return float(v)
    except Exception:
        return None


def _to_int(v):
    if v in (None, "", "null"):
        return None
    try:
        return int(float(v))
    except Exception:
        return None


@frappe.whitelist()
def fetch_and_sync():
    settings = frappe.get_single("API Wearcheck Settings")
    if not getattr(settings, "enabled", 1):
        return {"ok": True, "skipped": "disabled"}

    url = getattr(settings, "endpoint_url", None)
    if not url:
        frappe.throw("API Wearcheck Settings: endpoint_url is required")

    res = requests.get(url, timeout=90)
    res.raise_for_status()
    rows = res.json() or []

    import json
    import hashlib

    def _checksum(row: dict) -> str:
        raw = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    # store checksum in a hidden custom field (or reuse a Data field)
    # We'll add a field "checksum" (Data) to API Wearcheck in the next tiny step.
    created = 0
    updated = 0
    skipped = 0

    for r in rows:
        if not isinstance(r, dict):
            continue

        sampno = _to_int(r.get("sampno"))
        if not sampno:
            continue

        name = frappe.db.get_value("API Wearcheck", {"sampno": sampno}, "name")
        doc = frappe.get_doc("API Wearcheck", name) if name else frappe.new_doc("API Wearcheck")

        doc.sampno = sampno
        doc.bottleno = _to_int(r.get("bottleno"))
        doc.customer = r.get("customer") or ""
        doc.site = r.get("site") or ""
        doc.machine = r.get("machine") or ""
        doc.component = r.get("component") or ""
        doc.profileid = _to_int(r.get("profileid"))
        doc.status = _to_int(r.get("status"))

        doc.sampledate = r.get("sampledate") or None
        doc.registerdate = r.get("registerdate") or None

        doc.machread = _to_int(r.get("machread"))
        doc.oilread = _to_float(r.get("oilread"))
        doc.perwater = _to_float(r.get("perwater"))
        doc.fueldilution = _to_float(r.get("fueldilution"))

        doc.oilsupplier = r.get("oilsupplier") or ""
        doc.oilbrand = r.get("oilbrand") or ""
        doc.samp_taker = r.get("samp_taker") or ""

        doc.commentstext = r.get("commentstext") or ""
        doc.actiontext = r.get("actiontext") or ""
        doc.feedbacktext = r.get("feedbacktext") or ""

        doc.tan = _to_float(r.get("tan"))
        doc.tbn = _to_float(r.get("tbn"))

        for k in ("fe","ag","al","ca","cr","cu","mg","na","ni","pb","si","sn","p","b","ba","mo","v","zn","ti"):
            setattr(doc, k, _to_int(r.get(k)))

        doc.v40 = _to_float(r.get("v40"))
        doc.v100 = _to_float(r.get("v100"))
        doc.oxi = _to_float(r.get("oxi"))
        doc.soot = _to_float(r.get("soot"))

        doc.iso4 = _to_int(r.get("iso4"))
        doc.iso6 = _to_int(r.get("iso6"))
        doc.iso14 = _to_int(r.get("iso14"))
        doc.pq = _to_int(r.get("pq"))

        new_cs = _checksum(r)

        if name:
            old_cs = frappe.db.get_value("API Wearcheck", name, "checksum")
            if old_cs == new_cs:
                skipped += 1
                continue

            doc.checksum = new_cs
            doc.save(ignore_permissions=True)
            updated += 1
        else:
            doc.checksum = new_cs
            doc.insert(ignore_permissions=True)
            created += 1

    frappe.db.commit()
    return {"ok": True, "count": len(rows), "created": created, "updated": updated, "skipped": skipped, "ts": now()}
