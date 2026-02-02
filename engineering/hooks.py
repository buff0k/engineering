app_name = "engineering"
app_title = "Engineering"
app_publisher = "BuFf0k"
app_description = "Engineering Workflows and Maintenance Tasks"
app_email = "buff0k@buff0k.co.za"
app_license = "mit"
required_apps = ["frappe/erpnext"]
source_link = "http://github.com/buff0k/engineering"
app_logo_url = "/assets/engineering/images/is-logo.svg"
app_home = "/app/engineering"

add_to_apps_screen = [
    {
        "name": "engineering",
        "logo": "/assets/engineering/images/is-logo.svg",
        "title": "Engineering",
        "route": "/app/engineering",
        "has_permission": "engineering.engineering.utils.check_app_permission",
    }
]

fixtures = [
    {"dt": "Role", "filters": [["name", "in", ["Engineering Manager", "Engineering User"]]]},
    {"dt": "Custom DocPerm", "filters": [["role", "in", ["Engineering Manager", "Engineering User"]]]},
    {"dt": "Custom Field", "filters": [["dt", "in", ["Asset Movement"]]]},
    {"dt": "Asset Category", "filters": [["name", "in", ["Dozer", "ADT", "Rigid", "Excavator"]]]},
    {"dt": "Service Interval", "filters": [["name", "in", ["250 Hours", "500 Hours", "750 Hours", "1000 Hours", "2000 Hours"]]]}
]

# ---------------------------------------------------------------------
# Doctype-specific client JS
# ---------------------------------------------------------------------
doctype_js = {
    "Plant Breakdown": "engineering/doctype/plant_breakdown/plant_breakdown.js",
    "Engineering Control Panel": "engineering/doctype/engineering_control_panel/engineering_control_panel.js",
    "Service Schedule": "engineering/engineering/doctype/service_schedule/service_schedule.js",
}

# ---------------------------------------------------------------------
# Scheduled jobs
# ---------------------------------------------------------------------
scheduler_events = {
    "cron": {
        # Run every day at 06:00
        "0 6 * * *": [
            "engineering.engineering.doctype.availability_and_utilisation.availability_and_utilisation.run_daily"
        ],
        # Run every day at 18:00
        "0 18 * * *": [
            "engineering.engineering.doctype.availability_and_utilisation.availability_and_utilisation.run_daily"
        ],


         # ==========================================================
        # NEW — SERVICE SCHEDULE DAILY UPDATE (Runs at 01:00)
        # ==========================================================
        "0 1 * * *": [
            "engineering.engineering.doctype.service_schedule.service_schedule.queue_service_schedule_update"
        ]
    }
}

# ---------------------------------------------------------------------
# DocType event hooks
# ---------------------------------------------------------------------
doc_events = {
    "Plant Breakdown or Maintenance": {
        "on_update": "engineering.engineering.doctype.plant_breakdown_or_maintenance.plant_breakdown_or_maintenance.on_update"
    },
    "Engineering Legals": {
        "on_update": "engineering.engineering.doctype.engineering_legals.engineering_legals.on_update",
        "on_trash": "engineering.engineering.doctype.engineering_legals.engineering_legals.on_trash",
    }
}

# ---------------------------------------------------------------------
# Whitelisted method overrides
# ---------------------------------------------------------------------
override_whitelisted_methods = {
    "custom_checkin": "engineering.checkin.custom_checkin"
}

