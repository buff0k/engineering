import frappe


def execute(filters=None):
    filters = filters or {}

    asset = filters.get("asset")
    service_breakdown = filters.get("service_breakdown")

    columns = [
        {
            "label": "MSR",
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Mechanical Service Report",
            "width": 280,
        },
        {
            "label": "Service Date",
            "fieldname": "service_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "Hours at Service",
            "fieldname": "current_hours",
            "fieldtype": "Float",
            "width": 150,
        },
        {
            "label": "Description of Breakdown",
            "fieldname": "description_of_breakdown",
            "fieldtype": "Data",
            "width": 560,
        },
    ]

    if not asset:
        return columns, []

    query_filters = {"asset": asset}
    if service_breakdown:
        query_filters["service_breakdown"] = service_breakdown

    data = frappe.get_all(
        "Mechanical Service Report",
        filters=query_filters,
        fields=[
            "name",
            "service_date",
            "current_hours",
            "description_of_breakdown",
            "service_breakdown",
        ],
        order_by="service_date desc, creation desc",
        limit_page_length=200,
    )

    return columns, data
