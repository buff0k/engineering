# Tyre Survey Supplier Portal v12 — secure company access

This release replaces the temporary open Supplier selector with server-enforced
supplier isolation.

## Access model

- Every portal account has its own Frappe login.
- Every portal account must have exactly one standard **User Permission** where
  **Allow = Supplier** and **For Value = its supplier company**.
- A user with the **Supplier** role sees, edits and submits only their own
  drafts and submissions.
- A user with the **Supplier Manager** role sees every draft/submission for the
  same Supplier and may submit a company draft, but cannot edit another
  surveyor's captured readings.
- Supplier identity is derived on the server. Changing browser fields or API
  arguments cannot switch companies.
- Internal ERP users retain their normal Desk access; these portal rules do not
  modify internal report permissions.

## Previous ADT readings

After an ADT is selected, the portal shows the latest **actual** tyre readings.
The response deliberately excludes Supplier, inspector, portal user, general
remarks and attachments. Mock Survey Generator records are also excluded.

## Server destinations

Extract the packaged ZIP into `apps/engineering/engineering/`. It installs:

- `templates/pages/tyre_survey_sup.py`
- `templates/pages/tyre_survey_sup.html`
- `templates/pages/tyre_survey_list.py`
- `templates/pages/tyre_survey_list.html`
- `templates/pages/tyre_portal_security.py`
- `install_supplier_portal_security.py`

## One-time setup

Create the manager role:

```bash
bench --site jorrie.isambane.co.za execute \
engineering.install_supplier_portal_security.install
```

Then link each user. Example surveyor:

```bash
bench --site jorrie.isambane.co.za execute \
engineering.install_supplier_portal_security.assign_user \
--kwargs "{'user':'surveyor@example.com','supplier':'SUPPLIER EXACT NAME'}"
```

Example supplier manager:

```bash
bench --site jorrie.isambane.co.za execute \
engineering.install_supplier_portal_security.assign_user \
--kwargs "{'user':'manager@example.com','supplier':'SUPPLIER EXACT NAME','manager':True}"
```

Alternatively add the role and User Permission in ERP. Do not give one portal
user more than one Supplier User Permission.

Audit all portal assignments without changing data:

```bash
bench --site jorrie.isambane.co.za execute \
engineering.install_supplier_portal_security.audit
```

Finish deployment:

```bash
bench --site jorrie.isambane.co.za clear-cache
bench --site jorrie.isambane.co.za clear-website-cache
bench restart
```

