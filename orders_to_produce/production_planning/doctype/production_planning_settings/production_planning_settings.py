import frappe  # pyright: ignore[reportMissingImports]
from frappe.model.document import Document  # pyright: ignore[reportMissingImports]


class ProductionPlanningSettings(Document):

    def validate(self):
        if not 0 <= (self.min_paid_percent or 0) <= 100:
            frappe.throw("Minimum Paid (%) must be between 0 and 100.")
