frappe.ui.form.on("Mechanical Daily Worksheet", {
    refresh(frm) {
        frm.trigger("calculate_all_times");
    },

    validate(frm) {
        frm.trigger("calculate_all_times");
    },

    clock_in_time(frm) {
        frm.trigger("calculate_total_hours");
    },

    clock_out_time(frm) {
        frm.trigger("calculate_total_hours");
    },

    calculate_all_times(frm) {
        frm.trigger("calculate_total_hours");
        frm.trigger("calculate_child_hours");
        frm.trigger("calculate_total_work_time");
    },

    calculate_total_hours(frm) {
        let total_hours = calculate_hours(
            frm.doc.clock_in_time,
            frm.doc.clock_out_time
        );

        frm.set_value("total_hours", total_hours);
    },

    calculate_child_hours(frm) {
        (frm.doc.work_details || []).forEach(row => {
            let hours = calculate_hours(row.time_started, row.time_done);

            frappe.model.set_value(
                row.doctype,
                row.name,
                "hours",
                hours
            );
        });

        frm.refresh_field("work_details");
    },

    calculate_total_work_time(frm) {
        let total_work_time = 0;

        (frm.doc.work_details || []).forEach(row => {
            total_work_time += flt(row.hours);
        });

        frm.set_value("total_work_time", flt(total_work_time, 2));
    }
});


frappe.ui.form.on("Mechanical Daily Worksheet Detail", {
    time_started(frm, cdt, cdn) {
        calculate_child_row_hours(frm, cdt, cdn);
    },

    time_done(frm, cdt, cdn) {
        calculate_child_row_hours(frm, cdt, cdn);
    },

    hours(frm) {
        frm.trigger("calculate_total_work_time");
    },

    work_details_remove(frm) {
        frm.trigger("calculate_total_work_time");
    }
});


function calculate_child_row_hours(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    let hours = calculate_hours(
        row.time_started,
        row.time_done
    );

    frappe.model.set_value(cdt, cdn, "hours", hours);

    setTimeout(() => {
        frm.trigger("calculate_total_work_time");
    }, 100);
}


function calculate_hours(start_time, end_time) {
    if (!start_time || !end_time) {
        return 0;
    }

    let start_seconds = time_to_seconds(start_time);
    let end_seconds = time_to_seconds(end_time);

    if (start_seconds === null || end_seconds === null) {
        return 0;
    }

    // Handles work passing midnight, example 22:00 to 02:00
    if (end_seconds < start_seconds) {
        end_seconds += 24 * 60 * 60;
    }

    let difference_seconds = end_seconds - start_seconds;
    let hours = difference_seconds / 3600;

    return flt(hours, 2);
}


function time_to_seconds(time_value) {
    if (!time_value) {
        return null;
    }

    let parts = time_value.toString().split(":");

    if (parts.length < 2) {
        return null;
    }

    let hours = cint(parts[0]);
    let minutes = cint(parts[1]);
    let seconds = parts.length >= 3 ? cint(parts[2]) : 0;

    return (hours * 3600) + (minutes * 60) + seconds;
}