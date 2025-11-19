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
		"name": "ir",
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
        {"dt": "Asset Category", "filters": [["name", "in", ["Dozer", "ADT", "Rigid", "Excavator"]]]}
        ]

# ────────────────────────────────────────────────────────────────────────────
doctype_js = {
    "Plant Breakdown": "engineering/doctype/plant_breakdown/plant_breakdown.js"
}

scheduler_events = {
    "cron": {
        # Run every day at 05:40 AM
        "0 6 * * *": [
            "engineering.engineering.doctype.availability_and_utilisation.availability_and_utilisation.run_daily"
        ],
        # Run every day at 18:00
        "0 18 * * *": [
            "engineering.engineering.doctype.availability_and_utilisation.availability_and_utilisation.run_daily"
        ]
    }
}

doc_events = {
    "Plant Breakdown or Maintenance": {
        "on_update": "engineering.engineering.doctype.plant_breakdown_or_maintenance.plant_breakdown_or_maintenance.on_update"
    }
}

doctype_js = {
    "Engineering Control Panel": "engineering/doctype/engineering_control_panel/engineering_control_panel.js"
}

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/engineering/css/engineering.css"
# app_include_js = "/assets/engineering/js/engineering.js"

# include js, css files in header of web template
# web_include_css = "/assets/engineering/css/engineering.css"
# web_include_js = "/assets/engineering/js/engineering.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "engineering/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "engineering/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "engineering.utils.jinja_methods",
# 	"filters": "engineering.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "engineering.install.before_install"
# after_install = "engineering.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "engineering.uninstall.before_uninstall"
# after_uninstall = "engineering.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "engineering.utils.before_app_install"
# after_app_install = "engineering.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "engineering.utils.before_app_uninstall"
# after_app_uninstall = "engineering.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "engineering.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"engineering.tasks.all"
# 	],
# 	"daily": [
# 		"engineering.tasks.daily"
# 	],
# 	"hourly": [
# 		"engineering.tasks.hourly"
# 	],
# 	"weekly": [
# 		"engineering.tasks.weekly"
# 	],
# 	"monthly": [
# 		"engineering.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "engineering.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "engineering.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "engineering.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["engineering.utils.before_request"]
# after_request = ["engineering.utils.after_request"]

# Job Events
# ----------
# before_job = ["engineering.utils.before_job"]
# after_job = ["engineering.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"engineering.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


