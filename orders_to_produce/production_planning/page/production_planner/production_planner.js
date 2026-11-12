// Production Planner: pick ready Sales Orders, check materials for the whole
// selection, then create a Klaes Production Batch.
//
// Nothing is saved until "Create Batch" is confirmed, so opening this page
// never creates an empty batch.

const PLANNER_API = {
	orders: "orders_to_produce.api.klaes_orders.get_orders_for_planning",
	check: "orders_to_produce.api.material_check.check_materials",
	create: "orders_to_produce.api.batch.create_batch",
};

frappe.pages["production-planner"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Production Planner"),
		single_column: true,
	});
	wrapper.production_planner = new ProductionPlanner(page);
};

frappe.pages["production-planner"].on_page_show = function (wrapper) {
	// Coming back to the page (e.g. after creating a batch): reload the orders.
	const planner = wrapper.production_planner;
	if (planner && planner.loaded_once) planner.load_orders();
};

class ProductionPlanner {
	constructor(page) {
		this.page = page;
		this.orders = []; // ready Sales Orders
		this.skipped = []; // not ready, with a reason
		this.selected = new Set(); // Sales Order names ticked by the manager
		this.check = null; // last material check result (for the current selection only)
		this.loaded_once = false;

		this.setup_actions();
		this.make_layout();
		this.load_orders();
	}

	// ------------------------------------------------------------------ setup

	setup_actions() {
		this.page.set_primary_action(__("Create Batch"), () => this.create_batch(), "add");
		this.page.set_secondary_action(__("Check Materials"), () => this.check_materials());
		this.page.add_inner_button(__("Refresh"), () => this.load_orders());
		this.page.add_menu_item(__("Production Planning Settings"), () =>
			frappe.set_route("Form", "Production Planning Settings")
		);
		this.page.add_menu_item(__("Production Batches"), () =>
			frappe.set_route("List", "Klaes Production Batch")
		);
	}

	make_layout() {
		this.$body = $(`
			<div class="production-planner">
				<style>
					.production-planner { padding: var(--padding-md) 0; }
					.production-planner .pp-section { margin-bottom: var(--margin-xl); }
					.production-planner .pp-head {
						display: flex; align-items: baseline; justify-content: space-between;
						gap: var(--margin-md); margin-bottom: var(--margin-sm);
					}
					.production-planner .pp-head h5 { margin: 0; }
					.production-planner .pp-muted { color: var(--text-muted); }
					.production-planner .table-wrap { overflow-x: auto; }
					.production-planner table { margin-bottom: 0; }
					.production-planner th { white-space: nowrap; color: var(--text-muted); font-weight: 500; }
					.production-planner td.num, .production-planner th.num { text-align: right; white-space: nowrap; }
					.production-planner tr.pp-problem td { background: var(--subtle-fg); }
					.production-planner .pp-box {
						border: 1px solid var(--border-color); border-left-width: 4px;
						border-radius: var(--border-radius-md); padding: var(--padding-md);
						margin-bottom: var(--margin-md); background: var(--card-bg);
					}
					.production-planner .pp-box.ok { border-left-color: var(--green-500); }
					.production-planner .pp-box.bad { border-left-color: var(--red-500); }
					.production-planner .pp-box.info { border-left-color: var(--blue-500); }
					.production-planner .pp-empty { padding: var(--padding-lg); text-align: center; }
					.production-planner details summary { cursor: pointer; font-weight: 600; }
					.production-planner .pp-small { font-size: var(--text-sm); }
				</style>

				<div class="pp-section">
					<div class="pp-head">
						<h5>${__("Ready for production")}</h5>
						<span class="pp-muted pp-selected-count"></span>
					</div>
					<div class="pp-orders"></div>
				</div>

				<div class="pp-section pp-check"></div>

				<div class="pp-section">
					<details class="pp-skipped">
						<summary>${__("Not ready")} (<span class="pp-skipped-count">0</span>)</summary>
						<div class="pp-skipped-body" style="margin-top: var(--margin-sm)"></div>
					</details>
				</div>
			</div>
		`).appendTo(this.page.main);

		this.$orders = this.$body.find(".pp-orders");
		this.$check = this.$body.find(".pp-check");
		this.$skipped = this.$body.find(".pp-skipped-body");

		// Ticking orders. Any change makes the previous material check out of date.
		this.$orders.on("change", ".pp-select", (e) => {
			const so = $(e.currentTarget).attr("data-so");
			e.currentTarget.checked ? this.selected.add(so) : this.selected.delete(so);
			this.selection_changed();
		});
		this.$orders.on("change", ".pp-select-all", (e) => {
			this.selected = e.currentTarget.checked
				? new Set(this.orders.map((o) => o.sales_order))
				: new Set();
			this.selection_changed();
		});
	}

	// ------------------------------------------------------------------ data

	load_orders() {
		this.$orders.html(`<div class="pp-empty pp-muted">${__("Loading orders from Klaes...")}</div>`);

		return frappe.call({ method: PLANNER_API.orders }).then((r) => {
			const data = r.message || {};
			this.orders = data.orders || [];
			this.skipped = data.skipped || [];

			// Keep only ticks for orders that are still ready.
			const ready = new Set(this.orders.map((o) => o.sales_order));
			this.selected = new Set([...this.selected].filter((so) => ready.has(so)));

			this.check = null;
			this.loaded_once = true;
			this.render();
		});
	}

	check_materials() {
		if (!this.selected.size) {
			frappe.msgprint(__("Tick at least one Sales Order first."));
			return;
		}

		const sales_orders = [...this.selected];
		return frappe
			.call({
				method: PLANNER_API.check,
				args: { sales_orders },
				freeze: true,
				freeze_message: __("Checking materials..."),
			})
			.then((r) => {
				this.check = r.message;
				this.check.selection_key = this.selection_key();
				this.render();
			});
	}

	create_batch() {
		if (!this.can_create()) return;

		const sales_orders = this.orders
			.map((o) => o.sales_order)
			.filter((so) => this.selected.has(so)); // keep the on-screen order

		const dialog = new frappe.ui.Dialog({
			title: __("Create Production Batch"),
			fields: [
				{
					fieldtype: "HTML",
					options: `<p>${__("{0} Sales Orders, all materials available.", [
						sales_orders.length,
					])}</p>`,
				},
				{
					label: __("Production Deadline"),
					fieldname: "production_deadline",
					fieldtype: "Date",
					reqd: 1,
				},
				{
					label: __("Production Notes"),
					fieldname: "production_notes",
					fieldtype: "Small Text",
				},
			],
			primary_action_label: __("Create Batch"),
			primary_action: (values) => {
				if (values.production_deadline < frappe.datetime.get_today()) {
					frappe.msgprint(__("The Production Deadline cannot be in the past."));
					return;
				}
				dialog.hide();

				// The server checks everything again (readiness + materials) before saving.
				frappe
					.call({
						method: PLANNER_API.create,
						args: { sales_orders, ...values },
						freeze: true,
						freeze_message: __("Creating batch..."),
					})
					.then((r) => {
						if (!r.message) return;
						frappe.show_alert({
							message: __("Batch {0} created", [r.message]),
							indicator: "green",
						});
						this.selected.clear();
						this.check = null;
						frappe.set_route("Form", "Klaes Production Batch", r.message);
					});
			},
		});
		dialog.show();
	}

	// ------------------------------------------------------------------ state

	selection_key() {
		return [...this.selected].sort().join("|");
	}

	check_is_current() {
		return this.check && this.check.selection_key === this.selection_key();
	}

	can_create() {
		return this.selected.size > 0 && this.check_is_current() && this.check.feasible;
	}

	selection_changed() {
		if (!this.check_is_current()) this.check = null;
		this.render();
	}

	update_actions() {
		this.page.btn_primary.prop("disabled", !this.can_create());
		this.page.btn_secondary.prop("disabled", !this.selected.size);
		this.$body
			.find(".pp-selected-count")
			.text(this.selected.size ? __("{0} selected", [this.selected.size]) : "");
	}

	// ------------------------------------------------------------------ rendering

	render() {
		this.render_orders();
		this.render_check();
		this.render_skipped();
		this.update_actions();
	}

	render_orders() {
		if (!this.orders.length) {
			this.$orders.html(`
				<div class="pp-box info pp-muted">
					${__(
						"No orders are ready. An order appears here when its Sales Order is submitted, has a Klaes production number (O...), is paid at least the minimum %, has no Work Order, and is not in another batch."
					)}
				</div>`);
			return;
		}

		const status = this.order_status_map();
		const all_ticked = this.orders.every((o) => this.selected.has(o.sales_order));

		const rows = this.orders
			.map((o) => {
				const s = status[o.sales_order];
				const ticked = this.selected.has(o.sales_order);
				return `
				<tr class="${s && s.problem ? "pp-problem" : ""}">
					<td><input type="checkbox" class="pp-select" data-so="${pp_esc(o.sales_order)}" ${
					ticked ? "checked" : ""
				}></td>
					<td>${pp_link("Sales Order", o.sales_order)}</td>
					<td>${pp_esc(o.klaes_document_number)}</td>
					<td>${pp_esc(o.customer_name || o.customer)}</td>
					<td>${pp_date(o.delivery_date)}</td>
					<td>${pp_date(o.klaes_delivery_date)}</td>
					<td class="num">${format_currency(o.total)}</td>
					<td class="num">${o.paid_percent}%</td>
					<td>${s ? s.html : ""}</td>
				</tr>`;
			})
			.join("");

		this.$orders.html(`
			<div class="table-wrap">
				<table class="table table-sm table-hover">
					<thead><tr>
						<th><input type="checkbox" class="pp-select-all" title="${__("Select all")}" ${
			all_ticked ? "checked" : ""
		}></th>
						<th>${__("Sales Order")}</th>
						<th>${__("Klaes No.")}</th>
						<th>${__("Customer")}</th>
						<th>${__("Delivery Date")}</th>
						<th>${__("Klaes Delivery")}</th>
						<th class="num">${__("Total")}</th>
						<th class="num">${__("Paid")}</th>
						<th>${__("Materials")}</th>
					</tr></thead>
					<tbody>${rows}</tbody>
				</table>
			</div>`);
	}

	// Material result per ticked order, only while the check matches the selection.
	order_status_map() {
		if (!this.check_is_current()) return {};

		const map = {};
		for (const o of this.check.orders) {
			if (o.material_availability === "Available") {
				map[o.sales_order] = { problem: false, html: pp_pill(__("Available"), "green") };
				continue;
			}
			let note = "";
			if (o.missing_boms.length) note = __("No BOM: {0}", [o.missing_boms.join(", ")]);
			else if (o.fits_alone) note = __("Fits on its own; short together with the others");
			else note = __("{0} materials short", [o.short_items.length]);
			map[o.sales_order] = {
				problem: true,
				html: `${pp_pill(__("Insufficient"), "red")} <span class="pp-muted pp-small">${pp_esc(note)}</span>`,
			};
		}
		return map;
	}

	render_check() {
		if (!this.selected.size) {
			this.$check.html("");
			return;
		}

		if (!this.check_is_current()) {
			this.$check.html(`
				<div class="pp-box info">
					${__("Click <b>Check Materials</b> to check the {0} selected orders before creating a batch.", [
						this.selected.size,
					])}
				</div>`);
			return;
		}

		const c = this.check;
		if (c.feasible) {
			this.$check.html(`
				<div class="pp-box ok">
					<b>${__("All materials available.")}</b>
					${__("The {0} selected orders can be made from stock in {1}. Click <b>Create Batch</b> to continue.", [
						c.orders.length,
						pp_esc(c.warehouse),
					])}
				</div>`);
			return;
		}

		const missing_boms = c.orders.filter((o) => o.missing_boms.length);
		const shortage_rows = c.shortages
			.map(
				(s) => `
				<tr>
					<td>${pp_link("Item", s.item_code)}<div class="pp-muted pp-small">${pp_esc(s.item_name || "")}</div></td>
					<td class="num">${pp_qty(s.required)}</td>
					<td class="num">${pp_qty(s.available)}</td>
					<td class="num"><b>${pp_qty(s.short)}</b></td>
					<td>${pp_esc(s.uom || "")}</td>
					<td class="pp-small">${s.sales_orders.map(pp_esc).join(", ")}</td>
				</tr>`
			)
			.join("");

		this.$check.html(`
			<div class="pp-box bad">
				<b>${__("Not enough materials for this selection.")}</b>
				${__("Untick the orders marked Insufficient, or wait for stock, then check again.")}
				${
					missing_boms.length
						? `<div style="margin-top: var(--margin-sm)">${missing_boms
								.map((o) =>
									__("{0} has stock items without a BOM: {1}", [
										pp_esc(o.sales_order),
										pp_esc(o.missing_boms.join(", ")),
									])
								)
								.join("<br>")}</div>`
						: ""
				}
			</div>
			${
				c.shortages.length
					? `<div class="pp-head"><h5>${__("Shortages")}</h5>
						<span class="pp-muted pp-small">${__("Stock in {0}", [pp_esc(c.warehouse)])}</span></div>
					<div class="table-wrap">
						<table class="table table-sm">
							<thead><tr>
								<th>${__("Material")}</th>
								<th class="num">${__("Needed")}</th>
								<th class="num">${__("Available")}</th>
								<th class="num">${__("Short")}</th>
								<th>${__("UOM")}</th>
								<th>${__("Used by")}</th>
							</tr></thead>
							<tbody>${shortage_rows}</tbody>
						</table>
					</div>`
					: ""
			}`);
	}

	render_skipped() {
		this.$body.find(".pp-skipped-count").text(this.skipped.length);

		if (!this.skipped.length) {
			this.$skipped.html(`<div class="pp-muted">${__("Nothing skipped.")}</div>`);
			return;
		}

		const rows = this.skipped
			.map(
				(o) => `
				<tr>
					<td>${pp_link("Sales Order", o.sales_order)}</td>
					<td>${pp_esc(o.klaes_document_number)}</td>
					<td>${pp_esc(o.customer_name || o.customer)}</td>
					<td class="num">${o.paid_percent}%</td>
					<td>${pp_esc(o.reason)}</td>
				</tr>`
			)
			.join("");

		this.$skipped.html(`
			<div class="table-wrap">
				<table class="table table-sm">
					<thead><tr>
						<th>${__("Sales Order")}</th>
						<th>${__("Klaes No.")}</th>
						<th>${__("Customer")}</th>
						<th class="num">${__("Paid")}</th>
						<th>${__("Reason")}</th>
					</tr></thead>
					<tbody>${rows}</tbody>
				</table>
			</div>`);
	}
}

// ---------------------------------------------------------------------- helpers

function pp_esc(value) {
	return frappe.utils.escape_html(value == null ? "" : String(value));
}

function pp_link(doctype, name) {
	return `<a href="${frappe.utils.get_form_link(doctype, name)}">${pp_esc(name)}</a>`;
}

function pp_date(value) {
	return value ? frappe.datetime.str_to_user(value) : `<span class="pp-muted">-</span>`;
}

function pp_qty(value) {
	return format_number(value, null, 3);
}

function pp_pill(label, color) {
	return `<span class="indicator-pill ${color}">${pp_esc(label)}</span>`;
}
