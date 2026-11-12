"""Create Klaes Production Batches and export them to Klaes as XML.

The batch rules (orders ready, enough materials, not in another batch) live in the
Klaes Production Batch controller, so they apply however a batch is created.
"""

import frappe

from orders_to_produce.api.klaes_db import get_connection
from orders_to_produce.api.sales_orders_to_xml import build_sales_orders_xml

PLANNER_ROLES = ("Manufacturing User", "Manufacturing Manager", "System Manager")


@frappe.whitelist(methods=["POST"])
def create_batch(sales_orders, production_deadline, production_notes=None):
	"""Create a batch from the orders the manager confirmed. Returns the batch name."""

	frappe.only_for(PLANNER_ROLES)

	sales_orders = frappe.parse_json(sales_orders) if isinstance(sales_orders, str) else sales_orders

	batch = frappe.get_doc(
		{
			"doctype": "Klaes Production Batch",
			"production_deadline": production_deadline,
			"production_notes": production_notes,
			"orders": [{"sales_order": so} for so in sales_orders or []],
		}
	)
	batch.insert()  # runs all checks in KlaesProductionBatch.validate()

	return batch.name


@frappe.whitelist()
def download_klaes_xml(batch):
	"""Download the batch as a Klaes order-batch XML file, ready to import into Klaes."""

	frappe.only_for(PLANNER_ROLES)

	doc = frappe.get_doc("Klaes Production Batch", batch)
	doc.check_permission("read")

	if doc.status == "Cancelled":
		frappe.throw("This batch is cancelled.")

	klaes_numbers = get_klaes_numbers(doc.get_sales_orders())
	stub_ids = get_klaes_stub_ids(list(klaes_numbers.values()))

	missing = [so for so, number in klaes_numbers.items() if number not in stub_ids]
	if missing:
		frappe.throw(f"Not found in Klaes: {', '.join(missing)}")

	# One entry per Klaes order (two Sales Orders can share a Klaes number).
	unique_numbers = list(dict.fromkeys(klaes_numbers.values()))
	xml = build_sales_orders_xml(
		[{"BSX_ID": stub_ids[number], "BSX_BELEGNR": number} for number in unique_numbers]
	)

	# Downloading the XML is the hand-over to Klaes, so the batch is now Ready.
	if doc.status == "Draft":
		doc.db_set("status", "Ready")
		doc.add_comment("Info", "Klaes XML downloaded; status set to Ready.")

	frappe.local.response.filename = f"{doc.name}.xml"
	frappe.local.response.filecontent = xml.encode("utf-8")
	frappe.local.response.type = "download"


def get_klaes_numbers(sales_orders):
	"""{sales_order: Klaes document number}, in the batch's order."""

	numbers = dict(
		frappe.get_all(
			"Sales Order",
			filters={"name": ["in", sales_orders]},
			fields=["name", "custom_klaes_document_number"],
			as_list=True,
		)
	)
	return {so: numbers.get(so) for so in sales_orders}


def get_klaes_stub_ids(doc_numbers):
	"""{Klaes document number: BSX_ID}. Klaes identifies documents in the XML by BSX_ID."""

	doc_numbers = [number for number in doc_numbers if number]
	if not doc_numbers:
		return {}

	placeholders = ", ".join("?" for _ in doc_numbers)
	try:
		with get_connection() as cnxn:
			cursor = cnxn.cursor()
			cursor.execute(
				f"""
				SELECT [BSX_BELEGNR], [BSX_ID]
				FROM [dbo].[VKBELEGSTUB]
				WHERE [BSX_BELEGNR] IN ({placeholders})
				""",
				doc_numbers,
			)
			return {number: stub_id for number, stub_id in cursor.fetchall()}
	except Exception as e:
		frappe.log_error(title="Klaes BSX_ID lookup failed", message=str(e))
		frappe.throw(f"Could not read orders from Klaes: {e}")
