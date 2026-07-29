import frappe
from frappe.utils import add_days, getdate, today


def execute():
    start_date = add_days(getdate(today()), -30)
    end_date = getdate(today())

    frappe.db.sql(
        """
        UPDATE `tabAvailability and Utilisation`
        SET
            available_hours_above_100_capped =
                CASE
                    WHEN COALESCE(shift_working_hours, 0) > 9
                        THEN LEAST(
                            COALESCE(shift_available_hours_above_100, 0),
                            9
                        )
                    ELSE COALESCE(shift_available_hours_above_100, 0)
                END,

            plant_shift_utilisation_above_100 =
                CASE
                    WHEN (
                        CASE
                            WHEN COALESCE(shift_working_hours, 0) > 9
                                THEN LEAST(
                                    COALESCE(
                                        shift_available_hours_above_100,
                                        0
                                    ),
                                    9
                                )
                            ELSE COALESCE(
                                shift_available_hours_above_100,
                                0
                            )
                        END
                    ) > 0
                    THEN (
                        COALESCE(shift_working_hours, 0)
                        /
                        CASE
                            WHEN COALESCE(shift_working_hours, 0) > 9
                                THEN LEAST(
                                    COALESCE(
                                        shift_available_hours_above_100,
                                        0
                                    ),
                                    9
                                )
                            ELSE COALESCE(
                                shift_available_hours_above_100,
                                0
                            )
                        END
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
