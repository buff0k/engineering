import frappe
from frappe.utils import add_days, getdate, today


def execute():
    start_date = add_days(getdate(today()), -30)
    end_date = getdate(today())

    frappe.db.sql(
        """
        UPDATE `tabAvailability and Utilisation`
        SET
            shift_available_hours_above_100 =
                GREATEST(
                    COALESCE(shift_working_hours, 0),
                    COALESCE(shift_available_hours, 0)
                ),

            plant_shift_availability_above_100 =
                CASE
                    WHEN COALESCE(pre_use_avail_status, '') IN ('3', '6')
                        THEN 100

                    WHEN COALESCE(shift_required_hours, 0) > 0
                        THEN (
                            GREATEST(
                                COALESCE(shift_working_hours, 0),
                                COALESCE(shift_available_hours, 0)
                            )
                            / shift_required_hours
                        ) * 100

                    ELSE 0
                END

        WHERE shift_date BETWEEN %(start_date)s AND %(end_date)s
        """,
        {
            "start_date": start_date,
            "end_date": end_date,
        },
    )

    frappe.db.commit()

    updated_count = frappe.db.count(
        "Availability and Utilisation",
        filters={
            "shift_date": ["between", [start_date, end_date]],
        },
    )

    frappe.logger().info(
        "Backfilled uncapped availability fields for "
        f"{updated_count} A&U records from {start_date} to {end_date}"
    )
