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
    site = filters.get("site")
    if site:
        return [site]

    # Default sites (same as your current dashboard)
    return [
        "Klipfontein",
        "Uitgevallen",
        "Gwab",
        "Koppie",
        "Kriel Rehabilitation",
        "Bankfontein",
    ]
