import frappe  # pyright: ignore[reportMissingImports]
from frappe.model.document import Document  # pyright: ignore[reportMissingImports]


class KlaesProductionBatch(Document):

    def validate(self):
        """Validate the production batch before saving."""

        self.validate_orders()
        self.validate_production_deadline()
        self.validate_duplicate_orders()

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
