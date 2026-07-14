import frappe
import traceback
from frappe import _

ALLOWED_SUPPLIER_SITES = ["Gwab", "Klipfontein"]


def _norm_asset(value):
  return (value or "").strip().replace(" ", "").upper()


def _fmt_percent(value):
  if value in (None, "", 0, 0.0):
    return "0%"
  try:
    num = float(value)
    if num.is_integer():
      return f"{int(num)}%"
    return f"{num:.1f}%"
  except Exception:
    return f"{value}%"


def get_context(context):
  if frappe.session.user == "Guest":
    frappe.local.flags.redirect_location = "/login"
    raise frappe.Redirect

  context.saved_message = ""
  context.save_error = ""
  context.csrf_token = frappe.sessions.get_csrf_token()

  name = frappe.form_dict.get("name")
  if not name:
    frappe.throw(_("Checklist Register name is required."))

  if frappe.request.method == "POST":
    try:
      _save_supplier_rows(name)
      context.saved_message = "Checklist saved successfully."
    except Exception:
      context.save_error = frappe.get_traceback()
      frappe.log_error(context.save_error, "Engineering Checklist Supplier Save Error")

  doc = frappe.get_doc("Engineering Checklist Register", name)

  if doc.site not in ALLOWED_SUPPLIER_SITES:
    frappe.throw(_("This site is not available on supplier portal."), frappe.PermissionError)

  child_table_fieldname = _get_child_table_fieldname()
  status_fields = _get_status_fields()
  supplier_assets = _get_supplier_asset_values(doc.site)

  rows = []
  for row in doc.get(child_table_fieldname) or []:
    fleet_no = row.get("fleet_no")

    if float(row.get("checklist_submission") or 0) <= 0:
      continue

    if fleet_no not in supplier_assets and _norm_asset(fleet_no) not in supplier_assets:
      continue

    rows.append({
      "name": row.name,
      "fleet_no": row.get("fleet_no") or "",
      "machine_type": row.get("machine_type") or "",
      "item_name": row.get("item_name") or "",
      "target": row.get("target") or "",
      "formatted_target": _fmt_percent(row.get("target") or 0),
      "checklist_submission": row.get("checklist_submission") or "",
      "formatted_submission": _fmt_percent(row.get("checklist_submission") or 0),
      "status_values": {field["fieldname"]: row.get(field["fieldname"]) or "" for field in status_fields},
    })

  context.title = "Engineering Checklist Supplier"
  context.doc = doc
  context.rows = rows
  context.status_fields = status_fields

  return context


def _save_supplier_rows(name):
  doc = frappe.get_doc("Engineering Checklist Register", name)

  if doc.site not in ALLOWED_SUPPLIER_SITES:
    frappe.throw(_("This site is not available on supplier portal."), frappe.PermissionError)

  child_table_fieldname = _get_child_table_fieldname()
  status_fields = _get_status_fields()
  allowed_fields = {field["fieldname"] for field in status_fields}
  supplier_assets = _get_supplier_asset_values(doc.site)

  child_doctype = "Engineering Checklist Register Row"

  for row in doc.get(child_table_fieldname) or []:
    fleet_no = row.get("fleet_no")
    if fleet_no not in supplier_assets and _norm_asset(fleet_no) not in supplier_assets:
      continue

    updates = {}

    for fieldname in allowed_fields:
      form_key = f"{row.name}__{fieldname}"
      if form_key in frappe.form_dict:
        updates[fieldname] = frappe.form_dict.get(form_key) or ""

    if updates:
      frappe.db.set_value(
        child_doctype,
        row.name,
        updates,
        update_modified=False,
      )

  frappe.db.commit()



def _get_supplier_asset_values(site):

  supplier = frappe.db.get_value(
      "Portal User",
      {
          "user": frappe.session.user
      },
      "parent"
  )

  if not supplier:
    return set()

  rows = frappe.get_all(
    "Asset",
    filters={
      "supplier": supplier,
      "location": site,
    },
    fields=["name", "asset_name"],
    limit_page_length=0,
  )

  values = set()

  for row in rows:
    for key in ("name", "asset_name"):
      val = row.get(key)
      if val:
        values.add(val)
        values.add(_norm_asset(val))

  return values


def _get_child_table_fieldname():
  meta = frappe.get_meta("Engineering Checklist Register")
  for df in meta.fields:
    if df.fieldtype == "Table" and df.options == "Engineering Checklist Register Row":
      return df.fieldname

  return "rows"


def _get_status_fields():
  meta = frappe.get_meta("Engineering Checklist Register Row")
  result = []

  for df in meta.fields:
    label = (df.label or "").lower()
    fieldname = (df.fieldname or "").lower()

    if df.fieldtype != "Select":
      continue

    if (
      "day" not in label
      and "night" not in label
      and "day" not in fieldname
      and "night" not in fieldname
    ):
      continue

    options = []
    for opt in (df.options or "").split("\n"):
      opt = opt.strip()
      if opt:
        options.append(opt)

    result.append({
      "fieldname": df.fieldname,
      "label": df.label or df.fieldname,
      "options": options,
    })

  return result
