// Klaes Production Batch form: download the batch for Klaes and refresh Work Order progress.

const KPB_METHODS = {
	download_xml: "orders_to_produce.api.batch.download_klaes_xml",
	refresh_progress: "orders_to_produce.production_planning.work_order_events.refresh_batch_progress",
};

frappe.ui.form.on("Klaes Production Batch", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status === "Cancelled") return;

		frm.add_custom_button(__("Download Klaes XML"), () => kpb_download_xml(frm)).addClass(
			// Highlight it while the batch has not been handed to Klaes yet.
			frm.doc.status === "Draft" ? "btn-primary" : ""
		);

		frm.add_custom_button(__("Refresh Progress"), () => {
			frappe.call({
				method: KPB_METHODS.refresh_progress,
				args: { batch: frm.doc.name },
				freeze: true,
				freeze_message: __("Reading Work Orders..."),
				callback: () => frm.reload_doc(),
			});
		});
	},
});

// Downloads with a POST request: Frappe only saves database changes on POST, and the
// download moves the batch from Draft to Ready. fetch() (instead of a form submit) lets
// us show server errors, e.g. "Not found in Klaes", as a normal message.
async function kpb_download_xml(frm) {
	if (frm.is_dirty()) {
		frappe.msgprint(__("Please save the batch first."));
		return;
	}

	frappe.dom.freeze(__("Building Klaes XML..."));
	try {
		const response = await fetch(`/api/method/${KPB_METHODS.download_xml}`, {
			method: "POST",
			headers: {
				"X-Frappe-CSRF-Token": frappe.csrf_token,
				"Content-Type": "application/x-www-form-urlencoded",
			},
			body: new URLSearchParams({ batch: frm.doc.name }),
		});

		if (!response.ok) {
			frappe.msgprint({
				title: __("Could not download the Klaes XML"),
				message: await kpb_error_message(response),
				indicator: "red",
			});
			return;
		}

		kpb_save_file(await response.blob(), `${frm.doc.name}.xml`);
		frappe.show_alert({ message: __("Klaes XML downloaded"), indicator: "green" });
	} catch (e) {
		frappe.msgprint({ title: __("Download failed"), message: String(e), indicator: "red" });
	} finally {
		frappe.dom.unfreeze();
		frm.reload_doc(); // show the new status (Ready) and the comment
	}
}

// Frappe sends errors as JSON: `_server_messages` is a JSON list of JSON messages.
async function kpb_error_message(response) {
	try {
		const data = await response.json();
		if (data._server_messages) {
			return JSON.parse(data._server_messages)
				.map((m) => JSON.parse(m).message)
				.join("<br>");
		}
		return data.exception || data.message || response.statusText;
	} catch {
		return `${response.status} ${response.statusText}`;
	}
}

// Hand the downloaded data to the browser as a file.
function kpb_save_file(blob, filename) {
	const url = URL.createObjectURL(blob);
	const link = document.createElement("a");
	link.href = url;
	link.download = filename;
	document.body.appendChild(link);
	link.click();
	link.remove();
	URL.revokeObjectURL(url);
}
