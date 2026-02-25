import requests
import frappe
from frappe.utils import now
import json
import hashlib

# WearCheck critical recipients per Site/Location
# NOTE: msani@isambane.co.za must always be included
WEARCHECK_SITE_RECIPIENTS = {
    "Koppie": ["wimpie@isambane.co.za", "dian@isambane.co.za", "msani@isambane.co.za", "juan@isambane.co.za"],
    "Klipfontein": ["kobus@isambane.co.za", "richard@isambane.co.za", "werner.french@isambane.co.za", "msani@isambane.co.za"],
    "Uitgevallen": ["charles@excavo.co.za", "saul@isambane.co.za", "msani@isambane.co.za"],
    "Gwab": ["shawn@isambane.co.za", "matimba@isambane.co.za", "msani@isambane.co.za"],
    "Bankfontein": ["noel@isambane.co.za", "j.semelane@excavo.co.za", "msani@isambane.co.za"],
    "Kriel Rehabilitation": ["carel@isambane.co.za", "xolani@isambane.co.za", "ishmael@isambane.co.za", "msani@isambane.co.za"],
}
WEARCHECK_DEFAULT_RECIPIENTS = ["msani@isambane.co.za"]

def _recipients_for_location(location_name: str):
    location_name = (location_name or "").strip()
    recipients = WEARCHECK_SITE_RECIPIENTS.get(location_name) or WEARCHECK_DEFAULT_RECIPIENTS
    # ensure msani always present
    if "msani@isambane.co.za" not in recipients:
        recipients = list(recipients) + ["msani@isambane.co.za"]
    # de-dupe keep order
    seen = set()
    out = []
    for r in recipients:
        if r and r not in seen:
            out.append(r)
            seen.add(r)
    return out

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


def _checksum(row: dict) -> str:
    # stable JSON => stable SHA1
    raw = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _queue_critical_email(doc):
    subject, message = _build_critical_email(doc)

    recipients = _recipients_for_location(getattr(doc, "location", None))

    eq = frappe.get_doc({
        "doctype": "Email Queue",
        "message": message,
        "send_now": 0,
        "recipients": [{"recipient": r} for r in recipients],
    })
    eq.insert(ignore_permissions=True)
    return eq.name


def _build_critical_email(doc):
    asset = (getattr(doc, "asset", None) or "").strip() or "Unknown Asset"
    sampno = getattr(doc, "sampno", None)
    machine = (getattr(doc, "machine", None) or "").strip()
    site = (getattr(doc, "location", None) or "").strip()

    subject = f"‼️ CRITICAL oil sample — {asset} !!"
    message = f"""
    <h2>{frappe.utils.escape_html(asset)}</h2>
    <p>‼️‼️ The machine oil sample is flagged critical, and it requires immediate attention! !!</p>
    <p><b>Sample:</b> {frappe.utils.escape_html(str(sampno) if sampno is not None else "")}
       | <b>Machine:</b> {frappe.utils.escape_html(machine)}
       | <b>Site:</b> {frappe.utils.escape_html(site)}</p>
    """
    return subject, message


def _send_critical_email(doc):
    subject, message = _build_critical_email(doc)
    frappe.sendmail(
        recipients=["juan@isambane.co.za"],
        subject=subject,
        message=message,
    )

@frappe.whitelist()
def fetch_and_sync():
    settings = frappe.get_single("API Wearcheck Settings")
    if not getattr(settings, "enabled", 1):
        return {"ok": True, "skipped": "disabled"}
    
    # Build mapping from child table (table_jqnq)
    # item_type: Company / Location / Asset
    def _norm(s):
        return (s or "").strip()

    def _key(s):
        return (s or "").strip().lower()

    mapping = {"Company": {}, "Location": {}, "Asset": {}}
    for m in (settings.get("table_jqnq") or []):
        it = _norm(getattr(m, "item_type", ""))
        jv = _key(getattr(m, "json_value", ""))
        fv = _norm(getattr(m, "frappe_value", ""))
        if it and jv and fv:
            mapping.setdefault(it, {})[jv] = fv



    url = getattr(settings, "endpoint_url", None)
    if not url:
        frappe.throw("API Wearcheck Settings: endpoint_url is required")

    res = requests.get(url, timeout=90)
    res.raise_for_status()
    rows = res.json() or []

    # store checksum in a hidden custom field (or reuse a Data field)
    created = 0
    updated = 0
    skipped = 0

    BATCH = 200
    n = 0

    for r in rows:
        if not isinstance(r, dict):
            continue

        sampno = _to_int(r.get("sampno"))
        if not sampno:
            continue

        # because autoname is field:sampno
        name = str(sampno)

        new_cs = _checksum(r)
        old_cs = frappe.db.get_value("WearCheck Results", name, "checksum")

        # unchanged => skip without loading full doc
        if old_cs and old_cs == new_cs:
            skipped += 1
            continue

        exists = frappe.db.exists("WearCheck Results", name)

        doc = frappe.get_doc("WearCheck Results", name) if exists else frappe.new_doc("WearCheck Results")

        doc.sampno = sampno
        doc.bottleno = _to_int(r.get("bottleno"))
        raw_customer = r.get("customer") or ""
        raw_site = r.get("site") or ""
        raw_machine = r.get("machine") or ""

        # display/raw fields: trimmed
        raw_customer_s = raw_customer.strip()
        raw_site_s = raw_site.strip()
        raw_machine_s = raw_machine.strip()


        # Keep raw JSON source fields (optional, but nice for traceability)
        doc.customer = raw_customer_s
        doc.site = raw_site_s
        doc.machine = raw_machine_s

        # Save mapped values into ERP link fields
        # First try mapping (json_value -> frappe_value). If no match, pass raw JSON through.
        # Map using normalized keys, but fall back to trimmed raw
        doc.company = mapping.get("Company", {}).get(_key(raw_customer)) or (raw_customer_s or None)
        doc.location = mapping.get("Location", {}).get(_key(raw_site)) or (raw_site_s or None)
        doc.asset = mapping.get("Asset", {}).get(_key(raw_machine)) or (raw_machine_s or None)



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

        doc.iso4 = _to_int(r.get("iso4"))
        doc.iso6 = _to_int(r.get("iso6"))
        doc.iso14 = _to_int(r.get("iso14"))
        doc.pq = _to_int(r.get("pq"))

        doc.checksum = new_cs


        if exists:
            doc.save(ignore_permissions=True, ignore_links=True)
            updated += 1
        else:
            doc.insert(ignore_permissions=True, ignore_links=True)
            created += 1

            if (doc.status or 0) == 4:
                _queue_critical_email(doc)



        n += 1
        if n % BATCH == 0:
            frappe.db.commit()



    frappe.db.commit()
    return {"ok": True, "count": len(rows), "created": created, "updated": updated, "skipped": skipped, "ts": now()}
