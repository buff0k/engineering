import frappe
from frappe import _


def _norm_asset(value):
  return (value or "").strip().replace(" ", "").upper()


ALLOWED_SUPPLIER_SITES = ["Gwab", "Klipfontein"]


def get_context(context):
  if frappe.session.user == "Guest":
    frappe.local.flags.redirect_location = "/login"
    raise frappe.Redirect

  context.title = "Engineering Checklist Supplier List"
  context.registers = _get_registers()
  return context


def _get_supplier_asset_values(site):
  rows = frappe.get_all(
    "Asset",
    filters={
      "asset_owner": "Supplier",
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


def _get_registers():
  child_table_fieldname = _get_child_table_fieldname()

  meta = frappe.get_meta("Engineering Checklist Register")
  fields = ["name", "site", "month", "year", "modified"]
  if meta.has_field("checklist_submission_average"):
    fields.append("checklist_submission_average")

  registers = frappe.get_all(
    "Engineering Checklist Register",
    filters={
      "site": ["in", ALLOWED_SUPPLIER_SITES],
    },
    fields=fields,
    order_by="modified desc",
    limit_page_length=100,
  )

  result = []

  for reg in registers:
    supplier_assets = _get_supplier_asset_values(reg.site)
    if not supplier_assets:
      continue

    doc = frappe.get_doc("Engineering Checklist Register", reg.name)
    rows = doc.get(child_table_fieldname) or []

    supplier_row_count = 0
    for row in rows:
      fleet_no = row.get("fleet_no")
      if fleet_no in supplier_assets or _norm_asset(fleet_no) in supplier_assets:
        supplier_row_count += 1

    if supplier_row_count <= 0:
      continue

    reg["supplier_row_count"] = supplier_row_count
    result.append(reg)

  return result
