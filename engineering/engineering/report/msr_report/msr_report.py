import frappe

def execute(filters=None):
    filters = filters or {}
    asset = filters.get("asset")

    # Safety check: if no asset, return nothing
    if not asset:
        return [], []

    columns = [
        {
            "label": "MSR",
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Mechanical Service Report",
            "width": 180,
        },
        {
            "label": "Service Date",
            "fieldname": "service_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "Hours at Service",
            "fieldname": "smr",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": "Description of Breakdown",
            "fieldname": "description_of_breakdown",
            "fieldtype": "Data",
            "width": 300,
        },
    ]

    # Get last 20 records for this asset ordered by latest service date,
    # and then by creation as a tie-breaker
    msr_list = frappe.get_all(
        "Mechanical Service Report",
        filters={"asset": asset},
        fields=["name", "service_date", "smr", "description_of_breakdown"],
        order_by="service_date desc, creation desc",
        limit_page_length=20,
    )

    return columns, msr_list