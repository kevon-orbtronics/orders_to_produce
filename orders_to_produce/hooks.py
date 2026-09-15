app_name = "orders_to_produce"
app_title = "Orders To Produce"
app_publisher = "Orbtonics Ltd"
app_description = "This app is meant to get all the orders that needs to be sent to production including sales orders and manufacture requests to be combined in an xml file to be sent to klaes. Klaes will then take that file and create a batch order. A production order can be started. When it has started workers track progress on erpnext. til completion. All we need from klaes is how to consume the stock, but not how much stock to consume."
app_email = "kevon@orbtronicsltd.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "orders_to_produce",
# 		"logo": "/assets/orders_to_produce/logo.png",
# 		"title": "Orders To Produce",
# 		"route": "/orders_to_produce",
# 		"has_permission": "orders_to_produce.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/orders_to_produce/css/orders_to_produce.css"
# app_include_js = "/assets/orders_to_produce/js/orders_to_produce.js"

# include js, css files in header of web template
# web_include_css = "/assets/orders_to_produce/css/orders_to_produce.css"
# web_include_js = "/assets/orders_to_produce/js/orders_to_produce.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "orders_to_produce/public/scss/website"

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
# app_include_icons = "orders_to_produce/public/icons.svg"

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

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "orders_to_produce.utils.jinja_methods",
# 	"filters": "orders_to_produce.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "orders_to_produce.install.before_install"
# after_install = "orders_to_produce.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "orders_to_produce.uninstall.before_uninstall"
# after_uninstall = "orders_to_produce.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "orders_to_produce.utils.before_app_install"
# after_app_install = "orders_to_produce.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "orders_to_produce.utils.before_app_uninstall"
# after_app_uninstall = "orders_to_produce.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "orders_to_produce.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "orders_to_produce.notifications.get_notification_config"

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
# 		"orders_to_produce.tasks.all"
# 	],
# 	"daily": [
# 		"orders_to_produce.tasks.daily"
# 	],
# 	"hourly": [
# 		"orders_to_produce.tasks.hourly"
# 	],
# 	"weekly": [
# 		"orders_to_produce.tasks.weekly"
# 	],
# 	"monthly": [
# 		"orders_to_produce.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "orders_to_produce.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "orders_to_produce.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "orders_to_produce.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "orders_to_produce.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["orders_to_produce.utils.before_request"]
# after_request = ["orders_to_produce.utils.after_request"]

# Job Events
# ----------
# before_job = ["orders_to_produce.utils.before_job"]
# after_job = ["orders_to_produce.utils.after_job"]

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
# 	"orders_to_produce.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

