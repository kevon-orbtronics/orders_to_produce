"""Keep Klaes Production Batches up to date with their Work Orders.

Klaes scripts create the Work Orders and link them to the Sales Orders. Whenever a
Work Order, or anything that moves one forward (Stock Entry, Job Card), changes,
the batches containing that Sales Order are refreshed:

- each Production Item gets its Work Order, Work Order status and produced qty
- the batch status follows the Work Orders: In Progress once one has started,
  Completed once all are done

ERPNext updates Work Order status/qty with db_set(), which does not fire Work Order
events, so we also listen to Stock Entry and Job Card, and run an hourly sync.
"""

import frappe
from frappe.utils import flt

# Batches whose progress is tracked (Cancelled batches are left alone).
TRACKED_BATCH_STATUSES = ("Draft", "Ready", "In Progress", "Completed")

STARTED_WO_STATUSES = ("In Process", "Completed", "Closed")
DONE_WO_STATUSES = ("Completed", "Closed")


# ---------------------------------------------------------------- doc_events


def on_work_order_change(doc, method=None):
	if doc.sales_order:
		refresh_batches_for_sales_orders([doc.sales_order])


def on_work_order_trash(doc, method=None):
	"""Unlink a Work Order that is being deleted, so our Link does not block the delete."""

	frappe.db.sql(
		"""
		UPDATE `tabProduction Batch Items`
		SET work_order = NULL, work_order_status = NULL, produced_qty = 0
		WHERE work_order = %s
		""",
		doc.name,
	)


def on_stock_entry_change(doc, method=None):
	if doc.work_order:
		refresh_batches_for_work_order(doc.work_order)


def on_job_card_change(doc, method=None):
	if doc.work_order:
		refresh_batches_for_work_order(doc.work_order)


# ---------------------------------------------------------------- scheduler / button


def sync_active_batches():
	"""Hourly: refresh every tracked batch (catches changes made without events)."""

	for batch in frappe.get_all(
		"Klaes Production Batch", filters={"status": ["in", TRACKED_BATCH_STATUSES]}, pluck="name"
	):
		safe_refresh(batch)
	frappe.db.commit()


@frappe.whitelist()
def refresh_batch_progress(batch):
	"""Refresh one batch now (for a "Refresh Progress" button on the batch form)."""

	frappe.get_doc("Klaes Production Batch", batch).check_permission("read")
	refresh_batch(batch)


# ---------------------------------------------------------------- refresh logic


def refresh_batches_for_work_order(work_order):
	sales_order = frappe.db.get_value("Work Order", work_order, "sales_order")
	if sales_order:
		refresh_batches_for_sales_orders([sales_order])


def refresh_batches_for_sales_orders(sales_orders):
	batches = frappe.db.sql(
		"""
		SELECT DISTINCT kpb.name
		FROM `tabProduction Batch Orders` pbo
		JOIN `tabKlaes Production Batch` kpb ON kpb.name = pbo.parent
		WHERE pbo.parenttype = 'Klaes Production Batch'
			AND pbo.sales_order IN %(sales_orders)s
			AND kpb.status IN %(statuses)s
		""",
		{"sales_orders": tuple(sales_orders), "statuses": TRACKED_BATCH_STATUSES},
		pluck=True,
	)
	for batch in batches:
		safe_refresh(batch)


def safe_refresh(batch):
	"""Refresh a batch without ever blocking the Stock Entry / Job Card / Work Order being saved.

	If the refresh fails, only its own changes are undone (savepoint) and the error is logged.
	"""

	frappe.db.savepoint("batch_refresh")
	try:
		refresh_batch(batch)
	except Exception:
		frappe.db.rollback(save_point="batch_refresh")
		frappe.log_error(title=f"Production batch refresh failed: {batch}")


def refresh_batch(batch):
	"""Recalculate Production Items and the batch status from the current Work Orders."""

	doc = frappe.get_doc("Klaes Production Batch", batch)
	if doc.status not in TRACKED_BATCH_STATUSES:
		return

	work_orders = frappe.get_all(
		"Work Order",
		filters={"sales_order": ["in", doc.get_sales_orders()], "docstatus": ["<", 2]},
		fields=["name", "sales_order", "sales_order_item", "production_item", "status", "produced_qty"],
		order_by="creation asc",
	)

	changed = False
	for row in doc.items:
		matches = [wo for wo in work_orders if matches_item(wo, row)]
		new_values = {
			"work_order": matches[0].name if matches else None,
			"work_order_status": combined_status(matches),
			"produced_qty": sum(flt(wo.produced_qty) for wo in matches),
		}
		for field, value in new_values.items():
			if (row.get(field) or None) != (value or None):
				row.set(field, value)
				changed = True

	new_status = get_batch_status(doc)
	if new_status != doc.status:
		doc.status = new_status
		changed = True

	if changed:
		doc.flags.ignore_permissions = True  # system update, whoever triggered it
		doc.save()


def matches_item(work_order, row):
	"""Does this Work Order belong to this Production Item row?

	Use the exact Sales Order line when the Work Order has it, otherwise the item code.
	"""

	if work_order.sales_order != row.sales_order:
		return False
	if work_order.sales_order_item:
		return work_order.sales_order_item == row.sales_order_item
	return work_order.production_item == row.item_code


def combined_status(work_orders):
	"""One status for an item, even if it was split over several Work Orders."""

	if not work_orders:
		return None
	statuses = [wo.status for wo in work_orders]
	if len(statuses) == 1:
		return statuses[0]
	if all(s in DONE_WO_STATUSES for s in statuses):
		return "Completed"
	if any(s in STARTED_WO_STATUSES for s in statuses):
		return "In Process"
	return statuses[0]


def get_batch_status(doc):
	"""Draft/Ready are set by people; In Progress/Completed follow the Work Orders."""

	if not doc.items:
		return doc.status

	all_done = all(row.work_order_status in DONE_WO_STATUSES for row in doc.items)
	started = any(
		row.work_order_status in STARTED_WO_STATUSES or flt(row.produced_qty) > 0 for row in doc.items
	)

	if all_done:
		return "Completed"
	if started:
		return "In Progress"
	if doc.status in ("In Progress", "Completed"):
		return "Ready"  # work was undone (e.g. Stock Entry cancelled)
	return doc.status
