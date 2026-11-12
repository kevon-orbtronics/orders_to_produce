"""Find the Klaes orders that are ready for production planning.

An ERPNext Sales Order is ready when:
1. It is submitted, has a Klaes production order number (O...), and is not
   Closed/Completed/On Hold.
2. That document number exists in Klaes (VKBELEGSTUB).
3. No Work Order (Draft or submitted) is linked to it yet.
4. At least MIN_PAID_PERCENT of it has been paid (advances + invoice payments).
"""

import frappe
from frappe.utils import flt

from orders_to_produce.api.klaes_db import get_connection

MIN_PAID_PERCENT = 50

# SQL Server allows ~2100 parameters per query, so look numbers up in chunks.
KLAES_CHUNK_SIZE = 500


@frappe.whitelist()
def get_orders_for_planning():
	"""Return Sales Orders ready for planning, plus skipped ones with the reason."""

	candidates = get_candidate_sales_orders()
	if not candidates:
		return {"orders": [], "skipped": []}

	so_names = [so.name for so in candidates]
	klaes_orders = get_klaes_orders([so.custom_klaes_document_number for so in candidates])
	with_work_orders = get_sales_orders_with_work_orders(so_names)
	paid_amounts = get_paid_amounts(candidates)

	orders, skipped = [], []

	for so in candidates:
		klaes = klaes_orders.get(so.custom_klaes_document_number)
		so_total = flt(so.rounded_total) or flt(so.grand_total)
		paid = paid_amounts.get(so.name, 0)
		paid_percent = flt(paid / so_total * 100, 1) if so_total else 0

		if not klaes:
			reason = "Klaes document number not found in Klaes"
		elif so.name in with_work_orders:
			reason = "Work Order already exists"
		elif paid_percent < MIN_PAID_PERCENT:
			reason = f"Only {paid_percent}% paid"
		else:
			reason = None

		row = {
			"sales_order": so.name,
			"klaes_document_number": so.custom_klaes_document_number,
			"customer": so.customer,
			"customer_name": so.customer_name,
			"transaction_date": so.transaction_date,
			"delivery_date": so.delivery_date,
			"total": so_total,
			"paid": paid,
			"paid_percent": paid_percent,
		}

		if reason:
			skipped.append({**row, "reason": reason})
		else:
			row["klaes_delivery_date"] = klaes["delivery_date"]
			orders.append(row)

	return {"orders": orders, "skipped": skipped}


def get_candidate_sales_orders():
	"""Submitted, still-open ERPNext Sales Orders that carry a Klaes document number."""

	return frappe.get_all(
		"Sales Order",
		filters={
			"docstatus": 1,
			# Klaes production orders start with "O"; "Q" numbers are only quotations.
			"custom_klaes_document_number": ["like", "O%"],
			"status": ["not in", ["Closed", "Completed", "On Hold"]],
		},
		fields=[
			"name",
			"custom_klaes_document_number",
			"customer",
			"customer_name",
			"transaction_date",
			"delivery_date",
			"grand_total",
			"rounded_total",
			"advance_paid",
		],
		order_by="delivery_date asc",
	)


def get_klaes_orders(doc_numbers):
	"""Look up document numbers in Klaes. Returns {doc_number: {...}} for those found."""

	doc_numbers = list(set(doc_numbers))
	found = {}

	try:
		with get_connection() as cnxn:
			cursor = cnxn.cursor()
			for start in range(0, len(doc_numbers), KLAES_CHUNK_SIZE):
				chunk = doc_numbers[start : start + KLAES_CHUNK_SIZE]
				placeholders = ", ".join("?" for _ in chunk)
				cursor.execute(
					f"""
					SELECT [BSX_BELEGNR], [BSX_LIEFERDATUM]
					FROM [dbo].[VKBELEGSTUB]
					WHERE [BSX_BELEGNR] IN ({placeholders})
					""",
					chunk,
				)
				for doc_number, delivery_date in cursor.fetchall():
					found[doc_number] = {
						"delivery_date": delivery_date.date().isoformat() if delivery_date else None,
					}
	except Exception as e:
		frappe.log_error(title="Klaes order lookup failed", message=str(e))
		frappe.throw(f"Could not read orders from Klaes: {e}")

	return found


def get_sales_orders_with_work_orders(so_names):
	"""Sales Orders that already have a Draft or submitted (not cancelled) Work Order."""

	return set(
		frappe.get_all(
			"Work Order",
			filters={"sales_order": ["in", so_names], "docstatus": ["<", 2]},
			pluck="sales_order",
		)
	)


def get_paid_amounts(sales_orders):
	"""Total paid per Sales Order: advances on the order + payments made on its invoices.

	Advances paid on the Sales Order also appear on its invoice as `total_advance`,
	so they are subtracted from the invoice to avoid counting them twice.
	"""

	paid = {so.name: flt(so.advance_paid) for so in sales_orders}

	invoice_rows = frappe.db.sql(
		"""
		SELECT
			sii.sales_order,
			si.total, si.grand_total, si.rounded_total,
			si.outstanding_amount, si.total_advance, si.write_off_amount,
			SUM(sii.amount) AS so_amount
		FROM `tabSales Invoice Item` sii
		JOIN `tabSales Invoice` si ON si.name = sii.parent
		WHERE si.docstatus = 1
			AND si.is_return = 0
			AND sii.sales_order IN %(sales_orders)s
		GROUP BY si.name, sii.sales_order
		""",
		{"sales_orders": tuple(paid)},
		as_dict=True,
	)

	for row in invoice_rows:
		invoice_total = flt(row.rounded_total) or flt(row.grand_total)
		paid_on_invoice = (
			invoice_total - flt(row.outstanding_amount) - flt(row.total_advance) - flt(row.write_off_amount)
		)

		# An invoice can cover several Sales Orders: give each its share.
		share = flt(row.so_amount) / flt(row.total) if flt(row.total) else 1
		paid[row.sales_order] += paid_on_invoice * share

	return {name: flt(amount, 2) for name, amount in paid.items()}
