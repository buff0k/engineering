# Copyright (c) 2026, Isambane Mining (Pty) Ltd
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, now_datetime, time_diff_in_hours, format_datetime
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file
from datetime import timedelta


START_LOOKUP_DATETIME = get_datetime("2026-05-01 00:00:00")


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 110},
        {"label": _("Site"), "fieldname": "site", "fieldtype": "Data", "width": 140},
        {"label": _("Plant No."), "fieldname": "plant_no", "fieldtype": "Data", "width": 120},
        {"label": _("Open/Closed"), "fieldname": "open_closed", "fieldtype": "Data", "width": 120},
        {"label": _("Breakdown/Maintenance Reason"), "fieldname": "breakdown_reason", "fieldtype": "Small Text", "width": 260},
        {"label": _("Resolution Summary"), "fieldname": "resolution_summary", "fieldtype": "Small Text", "width": 220},
        {"label": _("Breakdown/Maintenance Start Time"), "fieldname": "breakdown_start_datetime", "fieldtype": "Datetime", "width": 230},
        {"label": _("Datetime back in production"), "fieldname": "resolved_datetime", "fieldtype": "Datetime", "width": 220},
        {"label": _("Plant Category"), "fieldname": "asset_category", "fieldtype": "Data", "width": 160},
        {"label": _("Breakdown/Maintenance Hours"), "fieldname": "breakdown_hours", "fieldtype": "Float", "precision": 2, "width": 210},
    ]


def is_filter_set(value):
    value = str(value or "").strip()

    if not value:
        return False

    if value.lower() in ("all", "all sites", "undefined", "none", "null", "site"):
        return False

    return True


def normalise_shift(shift):
    shift = (shift or "").strip().lower()

    if shift in ("day", "day shift"):
        return "Day"

    if shift in ("night", "night shift"):
        return "Night"

    return ""


def get_report_windows(report_date, shift=None):
    shift = normalise_shift(shift)

    day_start = get_datetime(str(report_date) + " 06:00:00")
    day_end = get_datetime(str(report_date) + " 18:00:00")

    night_start = get_datetime(str(report_date) + " 18:00:00")
    night_end = get_datetime(str(report_date + timedelta(days=1)) + " 06:00:00")

    if shift == "Day":
        return [("Day", day_start, day_end)]

    if shift == "Night":
        return [("Night", night_start, night_end)]

    return [
        ("Day", day_start, day_end),
        ("Night", night_start, night_end),
    ]


def overlap_hours(a_start, a_end, b_start, b_end):
    start = max(a_start, b_start)
    end = min(a_end, b_end)

    if end <= start:
        return 0.0

    return float(time_diff_in_hours(end, start))


def exclusion_windows(shift, window_start, window_end):
    shift = normalise_shift(shift)
    windows = []

    shift_date = getdate(window_start)
    next_date = getdate(window_end)

    if shift == "Day":
        windows.append((
            get_datetime(str(shift_date) + " 06:00:00"),
            get_datetime(str(shift_date) + " 08:00:00"),
        ))
        windows.append((
            get_datetime(str(shift_date) + " 13:00:00"),
            get_datetime(str(shift_date) + " 14:00:00"),
        ))

    if shift == "Night":
        windows.append((
            get_datetime(str(shift_date) + " 18:00:00"),
            get_datetime(str(shift_date) + " 20:00:00"),
        ))
        windows.append((
            get_datetime(str(next_date) + " 01:00:00"),
            get_datetime(str(next_date) + " 02:00:00"),
        ))

    filtered = []

    for start, end in windows:
        if end <= window_start or start >= window_end:
            continue

        filtered.append((max(start, window_start), min(end, window_end)))

    return filtered


def get_breakdown_history_intervals(site, plant_no, window_start, window_end):
    effective_window_start = max(window_start, START_LOOKUP_DATETIME)

    if window_end <= START_LOOKUP_DATETIME:
        return []

    base_filters = {
        "location": site,
        "asset_name": plant_no,
        "exclude_from_au": 0,
    }

    last_before = frappe.get_all(
        "Breakdown History",
        filters={**base_filters, "update_date_time": ["<", effective_window_start]},
        fields=["update_date_time", "breakdown_status"],
        order_by="update_date_time desc",
        limit=1,
    )

    events_in_window = frappe.get_all(
        "Breakdown History",
        filters={**base_filters, "update_date_time": ["between", [effective_window_start, window_end]]},
        fields=["update_date_time", "breakdown_status"],
        order_by="update_date_time asc",
    )

    intervals = []
    in_breakdown = False
    current_start = None

    if last_before and str(last_before[0].get("breakdown_status")) != "3":
        in_breakdown = True
        current_start = effective_window_start

    for event in events_in_window:
        event_time = get_datetime(event.get("update_date_time"))
        event_status = str(event.get("breakdown_status") or "")

        if event_status != "3" and not in_breakdown:
            in_breakdown = True
            current_start = event_time

        elif event_status == "3" and in_breakdown:
            clip_start = max(current_start, effective_window_start)
            clip_end = min(event_time, window_end)

            if clip_end > clip_start:
                intervals.append((clip_start, clip_end))

            in_breakdown = False
            current_start = None

    if in_breakdown and current_start:
        clip_start = max(current_start, effective_window_start)
        clip_end = window_end

        if clip_end > clip_start:
            intervals.append((clip_start, clip_end))

    return intervals


def calculate_availability_engine_breakdown_hours(site, plant_no, shift, window_start, window_end):
    if window_end <= START_LOOKUP_DATETIME:
        return 0.0

    effective_window_start = max(window_start, START_LOOKUP_DATETIME)

    intervals = get_breakdown_history_intervals(site, plant_no, effective_window_start, window_end)
    excluded = exclusion_windows(shift, effective_window_start, window_end)

    effective_hours = 0.0

    for interval_start, interval_end in intervals:
        interval_hours = float(time_diff_in_hours(interval_end, interval_start))
        excluded_hours = 0.0

        for excluded_start, excluded_end in excluded:
            excluded_hours += overlap_hours(interval_start, interval_end, excluded_start, excluded_end)

        excluded_hours = min(excluded_hours, interval_hours)
        effective_hours += max(interval_hours - excluded_hours, 0.0)

    return round(max(effective_hours, 0), 2)


def get_availability_engine_hours(site, plant_no, report_date, shift=None):
    total_hours = 0.0

    for shift_name, window_start, window_end in get_report_windows(report_date, shift):
        total_hours += calculate_availability_engine_breakdown_hours(
            site,
            plant_no,
            shift_name,
            window_start,
            window_end,
        )

    return round(min(total_hours, 24), 2)


def get_open_closed_value(row):
    value = str(row.open_closed or "").strip()

    if value:
        return value

    if row.resolved_datetime:
        return "Closed"

    return "Open"


def get_data(filters):
    report_date = getdate(filters.get("report_date")) if filters.get("report_date") else getdate(now_datetime())

    windows = get_report_windows(report_date, filters.get("shift"))
    window_start = windows[0][1]
    window_end = windows[-1][2]

    if window_end <= START_LOOKUP_DATETIME:
        return []

    conditions = [
        """
        (
            (
                pbm.breakdown_start_datetime is not null
                and pbm.breakdown_start_datetime != ''
                and pbm.breakdown_start_datetime >= %(start_lookup_datetime)s
                and pbm.breakdown_start_datetime < %(window_end)s
            )
            or
            (
                pbm.resolved_datetime is not null
                and pbm.resolved_datetime != ''
                and pbm.resolved_datetime >= %(start_lookup_datetime)s
                and pbm.resolved_datetime < %(window_end)s
            )
            or
            (
                (
                    pbm.breakdown_start_datetime is null
                    or pbm.breakdown_start_datetime = ''
                )
                and
                (
                    pbm.resolved_datetime is null
                    or pbm.resolved_datetime = ''
                )
                and pbm.creation >= %(start_lookup_datetime)s
                and pbm.creation < %(window_end)s
            )
        )
        """,
    ]

    values = {
        "window_start": window_start,
        "window_end": window_end,
        "start_lookup_datetime": START_LOOKUP_DATETIME,
    }

    if is_filter_set(filters.get("site")):
        conditions.append("pbm.location = %(site)s")
        values["site"] = filters.get("site")

    if is_filter_set(filters.get("asset_category")):
        conditions.append("pbm.asset_category = %(asset_category)s")
        values["asset_category"] = filters.get("asset_category")

    rows = frappe.db.sql(
        f"""
        select
            pbm.location as site,
            pbm.asset_name as plant_no,
            pbm.open_closed as open_closed,
            pbm.breakdown_reason as breakdown_reason,
            pbm.resolution_summary as resolution_summary,
            pbm.breakdown_start_datetime as breakdown_start_datetime,
            pbm.resolved_datetime as resolved_datetime,
            pbm.asset_category as asset_category,
            pbm.creation as creation
        from `tabPlant Breakdown or Maintenance` pbm
        where {" and ".join(conditions)}
        order by
            case
                when pbm.breakdown_start_datetime is not null then pbm.breakdown_start_datetime
                when pbm.resolved_datetime is not null then pbm.resolved_datetime
                else pbm.creation
            end desc,
            pbm.modified desc
        """,
        values,
        as_dict=True,
    )

    data = []
    hours_cache = {}

    for row in rows:
        cache_key = (row.site, row.plant_no)

        if cache_key not in hours_cache:
            hours_cache[cache_key] = get_availability_engine_hours(
                row.site,
                row.plant_no,
                report_date,
                filters.get("shift"),
            )

        data.append({
            "date": report_date,
            "site": row.site,
            "plant_no": row.plant_no,
            "open_closed": get_open_closed_value(row),
            "breakdown_reason": row.breakdown_reason,
            "resolution_summary": row.resolution_summary,
            "breakdown_start_datetime": row.breakdown_start_datetime,
            "resolved_datetime": row.resolved_datetime,
            "asset_category": row.asset_category,
            "breakdown_hours": hours_cache[cache_key],
        })

    return data


@frappe.whitelist()
def save_downtime_signoff(report_date, site, asset_category, shift, signature):
    report_date = getdate(report_date)
    signoff_shift = shift or ""
    report_shift = shift or "All Shifts"
    user = frappe.session.user
    roles = frappe.get_roles(user)
    full_name = frappe.db.get_value("User", user, "full_name") or user

    production_roles = ["Production Supervisor", "Production Foreman"]
    engineering_roles = ["Engineering Supervisor", "Engineering Foreman"]

    is_production_user = any(role in roles for role in production_roles)
    is_engineering_user = any(role in roles for role in engineering_roles)

    if is_production_user and is_engineering_user:
        frappe.throw(_("You cannot sign both Production and Engineering sections."))

    if not is_production_user and not is_engineering_user:
        frappe.throw(_("Only Production Supervisor, Production Foreman, Engineering Supervisor, or Engineering Foreman can sign this report."))

    parent = get_or_create_signoff_parent(report_date, signoff_shift)
    row = get_or_create_signoff_row(parent, report_date, signoff_shift)

    if is_production_user:
        row.data_date_p = report_date
        row.date_time_p = now_datetime()
        row.shift_p = signoff_shift
        row.production_user = full_name
        row.production_signature = signature

    if is_engineering_user:
        row.data_date_e = report_date
        row.date_time_e = now_datetime()
        row.shift_e = signoff_shift
        row.engineering_user = full_name
        row.engineering_signature = signature

    parent.site = site
    parent.status = get_signoff_status(row)
    parent.save(ignore_permissions=True)

    new_name = make_signoff_name(row, report_date, report_shift, site)

    if parent.name != new_name:
        if frappe.db.exists("Mechanical Downtime sign-off", new_name):
            frappe.throw(_("A sign-off already exists with this name: {0}").format(new_name))

        frappe.rename_doc("Mechanical Downtime sign-off", parent.name, new_name, force=True)
        parent = frappe.get_doc("Mechanical Downtime sign-off", new_name)

    attach_signed_report_pdf(parent, report_date, site, asset_category, signoff_shift)

    return _("Downtime sign-off saved. Status: {0}").format(parent.status)


def get_or_create_signoff_parent(report_date, shift):
    existing_parent = frappe.db.sql(
        """
        select parent
        from `tabMechanical Downtime sign-off child`
        where parenttype = 'Mechanical Downtime sign-off'
            and (
                (data_date_p = %(report_date)s and ifnull(shift_p, '') in (%(shift)s, ''))
                or
                (data_date_e = %(report_date)s and ifnull(shift_e, '') in (%(shift)s, ''))
            )
        order by modified desc
        limit 1
        """,
        {
            "report_date": report_date,
            "shift": shift,
        },
    )

    if existing_parent:
        return frappe.get_doc("Mechanical Downtime sign-off", existing_parent[0][0])

    parent = frappe.new_doc("Mechanical Downtime sign-off")
    parent.status = "Open"
    parent.insert(ignore_permissions=True)

    return parent


def get_or_create_signoff_row(parent, report_date, shift):
    for row in parent.signoff_information:
        same_production = row.data_date_p and getdate(row.data_date_p) == report_date and (row.shift_p in (shift, None, ""))
        same_engineering = row.data_date_e and getdate(row.data_date_e) == report_date and (row.shift_e in (shift, None, ""))

        if same_production or same_engineering:
            return row

    row = parent.append("signoff_information", {})
    row.data_date_p = report_date
    row.data_date_e = report_date
    row.shift_p = shift
    row.shift_e = shift

    return row


def get_signoff_status(row):
    if row.production_signature and row.engineering_signature:
        return "Closed"

    return "Open"


def make_signoff_name(row, report_date, shift, site):
    production_user = row.production_user or "Pending Production"
    engineering_user = row.engineering_user or "Pending Engineering"
    data_date = row.data_date_p or row.data_date_e or report_date
    shift = row.shift_p or row.shift_e or shift or "All Shifts"
    site = site or "All Sites"

    return clean_docname("{0}-{1}-{2}-{3}-{4}".format(
        site,
        production_user,
        engineering_user,
        data_date,
        shift,
    ))


def clean_docname(value):
    value = str(value or "").strip()
    value = value.replace("/", "-")
    value = value.replace("\\", "-")
    value = value.replace(":", "-")
    value = value.replace("\n", " ")
    value = " ".join(value.split())

    return value


def attach_signed_report_pdf(parent, report_date, site, asset_category, shift):
    filters = frappe._dict({
        "report_date": report_date,
        "site": site,
        "asset_category": asset_category,
        "shift": shift,
    })

    columns = get_columns()
    data = get_data(filters)

    signoff_row = parent.signoff_information[0] if parent.signoff_information else None

    html = get_signed_report_html(
        parent=parent,
        report_date=report_date,
        site=site,
        asset_category=asset_category,
        shift=shift,
        columns=columns,
        data=data,
        signoff_row=signoff_row,
    )

    file_name = "Down Time {0} {1}.pdf".format(
        report_date,
        shift or "All Shifts",
    )

    pdf_file = get_pdf(html)

    file_doc = save_file(
        file_name,
        pdf_file,
        "Mechanical Downtime sign-off",
        parent.name,
        is_private=1,
    )

    parent.db_set("signed_report_excel", file_doc.file_url, update_modified=False)




def get_signed_report_html(parent, report_date, site, asset_category, shift, columns, data, signoff_row):
    production_signature = signoff_row.production_signature if signoff_row else ""
    engineering_signature = signoff_row.engineering_signature if signoff_row else ""

    production_user = signoff_row.production_user if signoff_row else ""
    engineering_user = signoff_row.engineering_user if signoff_row else ""

    production_date_time = format_datetime(signoff_row.date_time_p) if signoff_row and signoff_row.date_time_p else ""
    engineering_date_time = format_datetime(signoff_row.date_time_e) if signoff_row and signoff_row.date_time_e else ""

    letter_head = get_default_letter_head_html()

    return """
    <html>
        <head>
            <style>
                @page {{
                    size: A4 portrait;
                    margin: 10mm 10mm 12mm 10mm;
                }}

                body {{
                    font-family: Arial, sans-serif;
                    font-size: 9px;
                    color: #111;
                }}

                .iso-letterhead {{
                    margin-bottom: 12px;
                }}

                .report-title {{
                    text-align: center;
                    font-size: 15px;
                    font-weight: 800;
                    text-transform: uppercase;
                    border: 1.5px solid #111;
                    background: #f2f2f2;
                    padding: 6px;
                    margin-bottom: 8px;
                }}

                .meta-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 10px;
                }}

                .meta-table td {{
                    border: 1px solid #111;
                    padding: 5px 7px;
                    font-size: 9px;
                }}

                .signatures {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 12px;
                    page-break-inside: avoid;
                }}

                .signature-box {{
                    width: 50%;
                    border: 1px solid #111;
                    padding: 7px;
                    height: 78px;
                    vertical-align: top;
                }}

                .signature-title {{
                    font-weight: 800;
                    text-transform: uppercase;
                    margin-bottom: 6px;
                }}

                .signature-img {{
                    max-height: 42px;
                    max-width: 230px;
                    margin-top: 4px;
                }}

                .pending {{
                    font-style: italic;
                    margin-top: 18px;
                }}

                .downtime-card {{
                    border: 1px solid #111;
                    margin-bottom: 9px;
                    page-break-inside: avoid;
                }}

                .downtime-card-title {{
                    font-weight: 800;
                    background: #e9e9e9;
                    border-bottom: 1px solid #111;
                    padding: 5px 7px;
                    font-size: 9px;
                }}

                .downtime-grid {{
                    width: 100%;
                    border-collapse: collapse;
                }}

                .downtime-grid td {{
                    border: 1px solid #ccc;
                    padding: 5px 7px;
                    vertical-align: top;
                    line-height: 1.25;
                    word-wrap: break-word;
                    overflow-wrap: break-word;
                }}

                .label {{
                    width: 18%;
                    font-weight: 800;
                    background: #fafafa;
                }}

                .value {{
                    width: 32%;
                }}

                .full-value {{
                    white-space: pre-wrap;
                }}

                .footer {{
                    margin-top: 10px;
                    border-top: 1.5px solid #111;
                    padding-top: 5px;
                    font-size: 8px;
                    page-break-inside: avoid;
                }}

                .footer-left {{
                    float: left;
                }}

                .footer-right {{
                    float: right;
                }}
            </style>
        </head>

        <body>
            <div class="iso-letterhead">
                {letter_head}
            </div>

            <div class="report-title">Mechanical Downtime Sign-off Report</div>

            <table class="meta-table">
                <tr>
                    <td><b>Date:</b> {report_date}</td>
                    <td><b>Site:</b> {site}</td>
                    <td><b>Shift:</b> {shift}</td>
                    <td><b>Status:</b> {status}</td>
                </tr>
            </table>

            <table class="signatures">
                <tr>
                    <td class="signature-box">
                        <div class="signature-title">Production Sign-off</div>
                        <b>User:</b> {production_user}<br>
                        <b>Date/Time:</b> {production_date_time}<br>
                        {production_signature_html}
                    </td>
                    <td class="signature-box">
                        <div class="signature-title">Engineering Sign-off</div>
                        <b>User:</b> {engineering_user}<br>
                        <b>Date/Time:</b> {engineering_date_time}<br>
                        {engineering_signature_html}
                    </td>
                </tr>
            </table>

            {downtime_cards}

            <div class="footer">
                <div class="footer-left">
                    Directors: JP Jordaan, B Giyose, JG Venter<br>
                    Non-Executive Director: R Lakhoo
                </div>
                <div class="footer-right">Page 1 of 1</div>
                <div style="clear: both;"></div>
            </div>
        </body>
    </html>
    """.format(
        letter_head=letter_head,
        report_date=frappe.utils.escape_html(str(report_date)),
        site=frappe.utils.escape_html(site or "All Sites"),
        shift=frappe.utils.escape_html(shift or "All Shifts"),
        status=frappe.utils.escape_html(parent.status or ""),
        production_user=frappe.utils.escape_html(production_user or ""),
        engineering_user=frappe.utils.escape_html(engineering_user or ""),
        production_date_time=frappe.utils.escape_html(production_date_time or ""),
        engineering_date_time=frappe.utils.escape_html(engineering_date_time or ""),
        production_signature_html=get_signature_html(production_signature),
        engineering_signature_html=get_signature_html(engineering_signature),
        downtime_cards=get_downtime_cards_html(data),
    )


def get_default_letter_head_html():
    letter_head = frappe.db.get_value("Letter Head", {"is_default": 1}, "content")

    if letter_head:
        return letter_head

    return ""


def get_downtime_cards_html(data):
    if not data:
        return '<div class="downtime-card"><div class="downtime-card-title">No downtime records found.</div></div>'

    cards = []

    for row in data:
        cards.append("""
            <div class="downtime-card">
                <div class="downtime-card-title">
                    {plant_no} | {asset_category} | {status} | {hours} hrs
                </div>
                <table class="downtime-grid">
                    <tr>
                        <td class="label">Start</td>
                        <td class="value">{start}</td>
                        <td class="label">Back In Production</td>
                        <td class="value">{resolved}</td>
                    </tr>
                    <tr>
                        <td class="label">Reason</td>
                        <td colspan="3" class="full-value">{reason}</td>
                    </tr>
                    <tr>
                        <td class="label">Resolution</td>
                        <td colspan="3" class="full-value">{resolution}</td>
                    </tr>
                </table>
            </div>
        """.format(
            plant_no=frappe.utils.escape_html(str(row.get("plant_no") or "")),
            asset_category=frappe.utils.escape_html(str(row.get("asset_category") or "")),
            status=frappe.utils.escape_html(str(row.get("open_closed") or "")),
            hours=frappe.utils.escape_html(str(row.get("breakdown_hours") or "")),
            start=frappe.utils.escape_html(str(row.get("breakdown_start_datetime") or "")),
            resolved=frappe.utils.escape_html(str(row.get("resolved_datetime") or "")),
            reason=frappe.utils.escape_html(str(row.get("breakdown_reason") or "")),
            resolution=frappe.utils.escape_html(str(row.get("resolution_summary") or "")),
        ))

    return "".join(cards)


def get_signature_html(signature):
    if not signature:
        return '<div class="pending">Pending signature</div>'

    if str(signature).startswith("data:image"):
        return '<img class="signature-img" src="{0}">'.format(signature)

    return '<img class="signature-img" src="{0}">'.format(frappe.utils.escape_html(signature))