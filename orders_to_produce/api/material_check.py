"""Check whether a selection of Sales Orders can be manufactured from available stock.

Raw-material needs come from each item's BOM, like ERPNext's "BOM Stock Analysis"
report. Unlike that report, all selected orders are checked together: two orders
that each fit on their own may not both fit at once.

We read BOM lines directly instead of reusing the report's `get_bom_data()`:
that query joins BOM lines to Bin rows before summing, so qty per unit is
multiplied by the number of warehouses that hold the material.

Available = actual stock - reserved for production - reserved stock,
summed over the Raw Material Warehouse in Production Planning Settings
(including every warehouse under it, if it is a group).
"""

from collections import defaultdict

import frappe
from frappe.utils import flt

PLANNER_ROLES = ("Manufacturing User", "Manufacturing Manager", "System Manager")


@frappe.whitelist()
def check_materials(sales_orders):
	"""Check the selected Sales Orders together. `sales_orders` is a list of names."""

	frappe.only_for(PLANNER_ROLES)

	sales_orders = frappe.parse_json(sales_orders) if isinstance(sales_orders, str) else sales_orders
	sales_orders = list(dict.fromkeys(sales_orders or []))  # remove duplicates, keep order
	if not sales_orders:
		frappe.throw("Select at least one Sales Order.")

	warehouse = frappe.db.get_single_value("Production Planning Settings", "raw_material_warehouse")
	if not warehouse:
		frappe.throw("Set the Raw Material Warehouse in Production Planning Settings.")

	# required[raw_material][sales_order] = qty that order needs
	required, missing_boms = get_requirements(sales_orders)
	available = get_available_qty(list(required), warehouse)
	item_details = get_item_details(list(required))

	materials, shortages = [], []
	for item_code, per_order in required.items():
		total_required = flt(sum(per_order.values()), 3)
		item_available = flt(available.get(item_code, 0), 3)
		row = {
			"item_code": item_code,
			"item_name": item_details.get(item_code, {}).get("item_name"),
			"uom": item_details.get(item_code, {}).get("stock_uom"),
			"required": total_required,
			"available": item_available,
			"short": flt(max(total_required - item_available, 0), 3),
			"sales_orders": list(per_order),
		}
		materials.append(row)
		if row["short"] > 0:
			shortages.append(row)

	short_items = {row["item_code"] for row in shortages}
	orders = []
	for so in sales_orders:
		# Which shortages this order is part of, and whether it would fit on its own.
		uses_short = sorted(i for i in short_items if so in required[i])
		fits_alone = all(
			required[i][so] <= available.get(i, 0) for i in required if so in required[i]
		)
		problem = bool(uses_short or missing_boms.get(so))
		orders.append(
			{
				"sales_order": so,
				"material_availability": "Insufficient Materials" if problem else "Available",
				"short_items": uses_short,
				"missing_boms": missing_boms.get(so, []),
				"fits_alone": fits_alone and not missing_boms.get(so),
			}
		)

	return {
		"feasible": not shortages and not missing_boms,
		"warehouse": warehouse,
		"orders": orders,
		"shortages": sorted(shortages, key=lambda r: r["item_code"]),
		"materials": sorted(materials, key=lambda r: r["item_code"]),
	}


def get_requirements(sales_orders):
	"""Raw materials needed per Sales Order, from the BOM of every stock item on it.

	Returns (required, missing_boms):
	  required[raw_material][sales_order] = qty
	  missing_boms[sales_order] = [item codes that are stock items but have no BOM]
	"""

	lines = frappe.db.sql(
		"""
		SELECT soi.parent AS sales_order, soi.item_code, soi.stock_qty,
			IFNULL(NULLIF(soi.bom_no, ''), i.default_bom) AS bom
		FROM `tabSales Order Item` soi
		JOIN `tabItem` i ON i.name = soi.item_code
		WHERE soi.parent IN %(sales_orders)s AND i.is_stock_item = 1
		ORDER BY soi.parent, soi.idx
		""",
		{"sales_orders": tuple(sales_orders)},
		as_dict=True,
	)

	required = defaultdict(lambda: defaultdict(float))
	missing_boms = defaultdict(list)
	bom_cache = {}

	for line in lines:
		if not line.bom:
			missing_boms[line.sales_order].append(line.item_code)
			continue

		if line.bom not in bom_cache:
			bom_cache[line.bom] = get_bom_materials(line.bom)

		for item_code, qty_per_unit in bom_cache[line.bom].items():
			required[item_code][line.sales_order] += qty_per_unit * flt(line.stock_qty)

	return required, dict(missing_boms)


def get_bom_materials(bom, multiplier=1.0, depth=0):
	"""{raw material: qty per 1 unit of the BOM's item}.

	`qty_consumed_per_unit` is already divided by the BOM quantity. Phantom items
	are not stocked, so they are replaced by the materials of their own BOM.
	"""

	if depth > 10:
		frappe.throw(f"BOM {bom} has phantom items nested more than 10 levels deep.")

	materials = defaultdict(float)
	lines = frappe.db.sql(
		"""
		SELECT bi.item_code, bi.qty_consumed_per_unit, bi.is_phantom_item, bi.bom_no,
			i.is_stock_item
		FROM `tabBOM Item` bi
		JOIN `tabItem` i ON i.name = bi.item_code
		WHERE bi.parent = %(bom)s AND bi.parenttype = 'BOM'
		""",
		{"bom": bom},
		as_dict=True,
	)

	for line in lines:
		qty = flt(line.qty_consumed_per_unit) * multiplier
		if line.is_phantom_item and line.bom_no:
			for item_code, sub_qty in get_bom_materials(line.bom_no, qty, depth + 1).items():
				materials[item_code] += sub_qty
		elif line.is_stock_item:
			# Non-stock lines (e.g. pricing-only items) need no stock.
			materials[line.item_code] += qty

	return materials


def get_available_qty(item_codes, warehouse):
	"""Usable stock per item across the warehouse (and its children, if it is a group)."""

	if not item_codes:
		return {}

	lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])

	rows = frappe.db.sql(
		"""
		SELECT bin.item_code,
			SUM(bin.actual_qty - bin.reserved_qty_for_production - bin.reserved_stock) AS available
		FROM `tabBin` bin
		JOIN `tabWarehouse` wh ON wh.name = bin.warehouse
		WHERE bin.item_code IN %(item_codes)s AND wh.lft >= %(lft)s AND wh.rgt <= %(rgt)s
		GROUP BY bin.item_code
		""",
		{"item_codes": tuple(item_codes), "lft": lft, "rgt": rgt},
		as_dict=True,
	)

	return {row.item_code: max(flt(row.available), 0) for row in rows}


def get_item_details(item_codes):
	if not item_codes:
		return {}

	return {
		row.name: row
		for row in frappe.get_all(
			"Item",
			filters={"name": ["in", item_codes]},
			fields=["name", "item_name", "stock_uom"],
		)
	}
