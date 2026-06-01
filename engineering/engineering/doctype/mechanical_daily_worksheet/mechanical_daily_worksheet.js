frappe.ui.form.on("Mechanical Daily Worksheet", {
    refresh(frm) {
        frm.trigger("calculate_all_times");
        style_fetch_msrs_button(frm);
        style_total_unallocated_field(frm);
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



    fetch_msrs(frm) {
        if (!frm.doc.date) {
            frappe.msgprint("Please select Date first.");
            return;
        }

        if (!frm.doc.mechanic_company_no) {
            frappe.msgprint("Please select Mechanic Company No first.");
            return;
        }

        frappe.call({
            method: "engineering.engineering.doctype.mechanical_daily_worksheet.mechanical_daily_worksheet.get_msrs_for_daily_worksheet",
            args: {
                worksheet_date: frm.doc.date,
                mechanic_company_no: frm.doc.mechanic_company_no
            },
            callback: function(r) {
                if (r.exc) {
                    return;
                }

                const msrs = r.message || [];

                frm.clear_table("work_details");

                if (!msrs.length) {
                    frm.refresh_field("work_details");
                    frm.trigger("calculate_total_work_time");
                    frappe.msgprint("No MSR's found for this Date and Mechanic.");
                    return;
                }

                msrs.forEach(msr => {
                    let row = frm.add_child("work_details");

                    row.msr_number = msr.name;
                    row.date = msr.service_date;
                    row.site = msr.site;
                    row.machine_fleet_no = msr.asset;
                    row.fault_work_type = msr.service_breakdown;
                    row.km_hours = msr.current_hours;
                    row.description_of_work_carried_out = msr.description_of_work_done;
                    row.start_time_msr = msr.start_time;
                    row.end_time_msr = msr.end_time;
                });

                frm.refresh_field("work_details");
                frm.trigger("calculate_total_work_time");

                frappe.msgprint(msrs.length + " MSR row(s) fetched.");
            }
        });
    },





    calculate_all_times(frm) {
        frm.trigger("calculate_total_hours");
        frm.trigger("calculate_child_hours");
        frm.trigger("calculate_total_work_time");
        frm.trigger("calculate_total_non_msr_time");
        frm.trigger("calculate_sum_total");
    },

    calculate_total_hours(frm) {
        let total_hours = calculate_hours(
            frm.doc.clock_in_time,
            frm.doc.clock_out_time
        );

        frm.set_value("total_hours", total_hours);
    },

    calculate_child_hours(frm) {
        frm.trigger("calculate_total_work_time");
    },

    calculate_total_work_time(frm) {
        let total_work_time = 0;

        (frm.doc.work_details || []).forEach(row => {
            let row_total = calculate_datetime_hours(
                row.start_time_msr,
                row.end_time_msr
            );

            frappe.model.set_value(row.doctype, row.name, "total_time_entry", flt(row_total, 2));
            total_work_time += row_total;
        });

        frm.set_value("total_work_time", flt(total_work_time, 2));
        frm.trigger("calculate_sum_total");
    },

    calculate_total_non_msr_time(frm) {
        let total_non_msr_time = 0;

        (frm.doc.non_msr || []).forEach(row => {
            let row_total = calculate_datetime_hours(
                row.start_time,
                row.end_time
            );

            frappe.model.set_value(row.doctype, row.name, "total_per_entry", flt(row_total, 2));
            total_non_msr_time += row_total;
        });

        frm.set_value("total_non_msr_time", flt(total_non_msr_time, 2));
        frm.trigger("calculate_sum_total");
    },

    calculate_sum_total(frm) {
        let total_work_time = flt(frm.doc.total_work_time || 0);
        let total_non_msr_time = flt(frm.doc.total_non_msr_time || 0);
        let total_hours = flt(frm.doc.total_hours || 0);

        let sum_total = flt(total_work_time + total_non_msr_time, 2);

        frm.set_value("sum_total", sum_total);
        frm.set_value("total_unallocated", flt(total_hours - sum_total, 2));

        style_total_unallocated_field(frm);
    }
});


frappe.ui.form.on("Mechanical Daily Worksheet Detail", {
    msr_number(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (!row.msr_number) {
            frappe.model.set_value(cdt, cdn, "date", "");
            frappe.model.set_value(cdt, cdn, "site", "");
            frappe.model.set_value(cdt, cdn, "machine_fleet_no", "");
            frappe.model.set_value(cdt, cdn, "fault_work_type", "");
            frappe.model.set_value(cdt, cdn, "km_hours", "");
            frappe.model.set_value(cdt, cdn, "description_of_work_carried_out", "");
            frappe.model.set_value(cdt, cdn, "start_time_msr", "");
            frappe.model.set_value(cdt, cdn, "end_time_msr", "");

            setTimeout(() => {
                frm.trigger("calculate_total_work_time");
            }, 100);

            return;
        }

        frappe.db.get_value("Mechanical Service Report", row.msr_number, [
            "service_date",
            "site",
            "asset",
            "service_breakdown",
            "current_hours",
            "description_of_work_done",
            "start_time",
            "end_time"
        ]).then(r => {
            if (r.message) {
                frappe.model.set_value(cdt, cdn, "date", r.message.service_date);
                frappe.model.set_value(cdt, cdn, "site", r.message.site);
                frappe.model.set_value(cdt, cdn, "machine_fleet_no", r.message.asset);
                frappe.model.set_value(cdt, cdn, "fault_work_type", r.message.service_breakdown);
                frappe.model.set_value(cdt, cdn, "km_hours", r.message.current_hours);
                frappe.model.set_value(cdt, cdn, "description_of_work_carried_out", r.message.description_of_work_done);
                frappe.model.set_value(cdt, cdn, "start_time_msr", r.message.start_time);
                frappe.model.set_value(cdt, cdn, "end_time_msr", r.message.end_time);

                setTimeout(() => {
                    frm.trigger("calculate_total_work_time");
                }, 100);
            }
        });
    },

    start_time_msr(frm) {
        frm.trigger("calculate_total_work_time");
    },

    end_time_msr(frm) {
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


frappe.ui.form.on("Non MSR Work", {
    start_time(frm) {
        frm.trigger("calculate_total_non_msr_time");
    },

    end_time(frm) {
        frm.trigger("calculate_total_non_msr_time");
    },

    non_msr_remove(frm) {
        frm.trigger("calculate_total_non_msr_time");
    }
});

function calculate_datetime_hours(start_datetime, end_datetime) {
    if (!start_datetime || !end_datetime) {
        return 0;
    }

    let start = frappe.datetime.str_to_obj(start_datetime);
    let end = frappe.datetime.str_to_obj(end_datetime);

    if (!start || !end) {
        return 0;
    }

    let diff_seconds = (end - start) / 1000;

    if (diff_seconds < 0) {
        diff_seconds = 0;
    }

    return flt(diff_seconds / 3600, 2);
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



function style_fetch_msrs_button(frm) {
    setTimeout(() => {
        const button = frm.fields_dict.fetch_msrs && frm.fields_dict.fetch_msrs.$wrapper.find("button");

        if (!button || !button.length) {
            return;
        }

        button.css({
            "background-color": "#f59e0b",
            "border-color": "#d97706",
            "color": "#111827",
            "font-weight": "700",
            "box-shadow": "0 0 0 3px rgba(245, 158, 11, 0.25)"
        });
    }, 300);
}


function style_total_unallocated_field(frm) {
    setTimeout(() => {
        const field = frm.fields_dict.total_unallocated;

        if (!field || !field.$wrapper) {
            return;
        }

        const input = field.$wrapper.find("input, .control-value");

        if (!input || !input.length) {
            return;
        }

        let total_hours = flt(frm.doc.total_hours || 0);
        let sum_total = flt(frm.doc.sum_total || 0);

        let is_equal = Math.abs(total_hours - sum_total) < 0.01;

        input.css({
            "background-color": is_equal ? "#dcfce7" : "#fee2e2",
            "color": is_equal ? "#166534" : "#991b1b",
            "font-weight": "700",
            "border": is_equal ? "1px solid #16a34a" : "1px solid #dc2626"
        });
    }, 300);
}