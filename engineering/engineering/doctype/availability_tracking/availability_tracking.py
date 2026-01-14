# your_app/your_app/doctype/availability_tracking/availability_tracking.py

import frappe
from frappe.model.document import Document
from frappe.utils import getdate
import calendar


class AvailabilityTracking(Document):
    def autoname(self):
        if not self.site or not self.month:
            return

        month_date = getdate(self.month)
        month_name = month_date.strftime("%B")  # January, February, etc
        year = month_date.year

        self.name = f"{self.site}-{month_name}-{year}"

def validate(self):
    if not self.site or not self.month:
        return

    month_date = getdate(self.month)
    month_start = month_date.replace(day=1)
    month_end = month_date.replace(day=calendar.monthrange(month_date.year, month_date.month)[1])

    exists = frappe.db.exists(
        "Availability Tracking",
        {
            "site": self.site,
            "month": ["between", [month_start, month_end]],
            "name": ["!=", self.name],
        },
    )
    if exists:
        frappe.throw("A record already exists for this Site and Month.")



def _safe_float(val):
    try:
        if val is None or val == "":
            return None
        return float(val)
    except Exception:
        return None


def _avg(values):
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


@frappe.whitelist()
def get_yearly_availability(year: int):
    """
    Returns monthly averages for each site for the given year.
    Averaging is done per month document over its child table rows.
    """
    try:
        year = int(year)
    except Exception:
        frappe.throw("Year must be a number")

    start = f"{year}-01-01"
    end = f"{year}-12-31"

    docs = frappe.get_all(
        "Availability Tracking",
        filters={"month": ["between", [start, end]]},
        fields=["name", "month"],
        order_by="month asc",
    )

    # Prepare 12 slots
    labels = [calendar.month_abbr[m] for m in range(1, 13)]
    uit_vals = [None] * 12
    kop_vals = [None] * 12
    ban_vals = [None] * 12

    for d in docs:
        mdate = getdate(d.month)
        if not mdate:
            continue
        idx = mdate.month - 1  # 0..11

        doc = frappe.get_doc("Availability Tracking", d.name)

        week_uit = []
        week_kop = []
        week_ban = []

        for row in (doc.weekly_entries or []):
            week_uit.append(_safe_float(row.uitgevallen))
            week_kop.append(_safe_float(row.koppie))
            week_ban.append(_safe_float(row.bankfontein))

        uit_vals[idx] = _avg(week_uit)
        kop_vals[idx] = _avg(week_kop)
        ban_vals[idx] = _avg(week_ban)

    return {
        "labels": labels,
        "uitgevallen": uit_vals,
        "koppie": kop_vals,
        "bankfontein": ban_vals,
    }
