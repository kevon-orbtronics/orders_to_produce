import frappe  # pyright: ignore[reportMissingImports]
from frappe.model.document import Document  # pyright: ignore[reportMissingImports]

from orders_to_produce.api.klaes_orders import (
    ACTIVE_BATCH_STATUSES,
    get_active_batches,
    get_orders_for_planning,
)
from orders_to_produce.api.material_check import check_materials


class KlaesProductionBatch(Document):

    def validate(self):
        """Validate the production batch before saving."""

        self.validate_orders()
        self.validate_production_deadline()
        self.validate_duplicate_orders()
        self.validate_not_in_other_batch()

        # Readiness and materials are only checked when the batch is created.
        # Later, stock gets consumed by this very batch, so re-checking would fail.
        if self.is_new():
            self.validate_orders_are_ready()
            self.validate_materials()

        self.set_items_from_sales_orders()

    def validate_orders(self):
        """Ensure the batch contains valid Sales Orders."""

        if not self.orders:
            frappe.throw("A production batch must contain at least one Sales Order.")

        for order in self.orders:
            if not order.sales_order:
                frappe.throw("Every production batch row must have a Sales Order.")

    def validate_production_deadline(self):
        """Ensure a production deadline has been provided."""

        if not self.production_deadline:
            frappe.throw("Please specify a Production Deadline.")

    def validate_duplicate_orders(self):
        """Prevent duplicate Sales Orders within the same batch."""

        sales_orders = [order.sales_order for order in self.orders]

        if len(sales_orders) != len(set(sales_orders)):
            frappe.throw("Duplicate Sales Orders are not allowed in a batch.")

    def validate_not_in_other_batch(self):
        """A Sales Order can only be in one active batch at a time."""

        if self.status not in ACTIVE_BATCH_STATUSES:
            return  # a Cancelled/Completed batch does not hold on to its orders

        in_other = get_active_batches(self.get_sales_orders(), exclude_batch=self.name)
        if in_other:
            details = ", ".join(f"{so} ({batch})" for so, batch in in_other.items())
            frappe.throw(f"Already in another active batch: {details}")

    def validate_orders_are_ready(self):
        """Every order must pass the Production Planner filters (Klaes, payment, no Work Order)."""

        planning = get_orders_for_planning()
        ready = {row["sales_order"] for row in planning["orders"]}
        reasons = {row["sales_order"]: row["reason"] for row in planning["skipped"]}

        problems = [
            f"{so}: {reasons.get(so, 'not a submitted Klaes production order')}"
            for so in self.get_sales_orders()
            if so not in ready
        ]
        if problems:
            frappe.throw(
                "These Sales Orders are not ready for production:<br>" + "<br>".join(problems)
            )

    def validate_materials(self):
        """Block the batch if the selected orders together cannot be made from stock."""

        result = check_materials(self.get_sales_orders())
        availability = {row["sales_order"]: row["material_availability"] for row in result["orders"]}

        for order in self.orders:
            order.material_availability = availability.get(order.sales_order, "Pending")

        if not result["feasible"]:
            lines = [
                f"{row['item_code']}: need {row['required']}, have {row['available']} {row['uom'] or ''}"
                for row in result["shortages"][:10]
            ]
            for so, items in ((r["sales_order"], r["missing_boms"]) for r in result["orders"]):
                if items:
                    lines.append(f"{so}: no BOM for {', '.join(items)}")

            frappe.throw(
                "Not enough materials for this batch:<br>" + "<br>".join(lines),
                title="Insufficient Materials",
            )

    def set_items_from_sales_orders(self):
        """Keep Production Items in step with the orders: one row per stock-item line.

        Rows that already exist are kept, so Work Order progress is not lost.
        Non-stock lines (e.g. installation charges) never get a Work Order, so they are skipped.
        """

        sales_orders = self.get_sales_orders()
        if not sales_orders:
            return

        # Drop rows for Sales Orders that were removed from the batch.
        kept = [row for row in self.items if row.sales_order in sales_orders]
        self.set("items", kept)
        existing = {row.sales_order_item for row in kept}

        lines = frappe.db.sql(
            """
            SELECT soi.name, soi.parent, soi.item_code, soi.qty
            FROM `tabSales Order Item` soi
            JOIN `tabItem` i ON i.name = soi.item_code
            WHERE soi.parent IN %(sales_orders)s AND i.is_stock_item = 1
            ORDER BY soi.idx
            """,
            {"sales_orders": tuple(sales_orders)},
            as_dict=True,
        )
        # Same order as the Production Orders table.
        lines.sort(key=lambda line: sales_orders.index(line.parent))

        for line in lines:
            if line.name not in existing:
                self.append(
                    "items",
                    {
                        "sales_order": line.parent,
                        "sales_order_item": line.name,
                        "item_code": line.item_code,
                        "qty": line.qty,
                    },
                )

    def get_sales_orders(self):
        return [order.sales_order for order in self.orders if order.sales_order]
