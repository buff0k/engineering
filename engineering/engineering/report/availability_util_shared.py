import frappe
from datetime import timedelta


def dashboard_date_range():
    # Always: last 7 days excluding today (yesterday back 6 days)
    today = frappe.utils.getdate(frappe.utils.nowdate())
    to_date = today - timedelta(days=1)
    from_date = to_date - timedelta(days=6)
    return from_date, to_date


def dashboard_sites(filters):
    filters = filters or {}

    SERITI_SITES = [
        "Klipfontein",
        "Gwab",
        "Kriel Rehabilitation",
    ]

    OTHER_SITES = [
        "Uitgevallen",
        "Koppie",
        "Bankfontein",
    ]

    group = (filters.get("site_group") or "All").strip()

    if group == "Seriti Sites":
        return SERITI_SITES

    if group == "Other":
        return OTHER_SITES

    # All (default)
    return SERITI_SITES + OTHER_SITES
