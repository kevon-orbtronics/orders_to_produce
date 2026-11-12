import xml.etree.ElementTree as ET

import frappe

from orders_to_produce.api.klaes_db import get_connection


def get_all_sales_orders():
    try:
        with get_connection() as cnxn:
            cursor = cnxn.cursor()
            cursor.execute(
                """
                SELECT TOP 2
                    [BSX_ID],
                    [BSX_MODDATE],
                    [BSX_BELEGNR]
                FROM [dbo].[VKBELEGSTUB]
                ORDER BY BSX_MODDATE DESC;
                """
            )
            rows = cursor.fetchall()
    except Exception as e:
        frappe.log_error(title="Klaes sales order fetch failed", message=str(e))
        return []

    return [
        {"BSX_ID": r[0], "BSX_MODDATE": r[1], "BSX_BELEGNR": r[2]}
        for r in rows
    ]

@frappe.whitelist()
def print_as_pdf():
    sales_orders = get_all_sales_orders()
    html = frappe.render_template(
        "orders_to_produce/templates/test_page.html",
        {"sales_orders": sales_orders},
    )
    pdf = frappe.utils.pdf.get_pdf(html)
    frappe.local.response.filename = "sales_orders.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "pdf"


def build_sales_orders_xml(sales_orders):
    document_batch = ET.Element("belegstapel", {"Datatype": "Class", "Count": "5"})
    ET.SubElement(document_batch, "version", {"Datatype": "Int32"}).text = "1"
    ET.SubElement(document_batch, "stapelart", {"Datatype": "String"}).text = "AuftragStapel"

    document_list = ET.SubElement(
        document_batch,
        "belegliste",
        {"Datatype": "Sequence", "Count": str(len(sales_orders))},
    )
    for sales_order in sales_orders:
        document = ET.SubElement(document_list, "beleg", {"Datatype": "Class", "Count": "6"})
        ET.SubElement(document, "version", {"Datatype": "Int32"}).text = "1"
        ET.SubElement(document, "belegstubid", {"Datatype": "Id"}).text = str(
            sales_order.get("BSX_ID") or ""
        )
        ET.SubElement(document, "auftragnr", {"Datatype": "String"}).text = str(
            sales_order.get("BSX_BELEGNR") or ""
        )
        ET.SubElement(document, "lieferscheinnr", {"Datatype": "String"})
        ET.SubElement(document, "rechnungnr", {"Datatype": "String"})
        ET.SubElement(document, "fauftragliste", {"Datatype": "Sequence", "Count": "0"})

    ET.SubElement(document_batch, "mengenlisten", {"Datatype": "Bool"}).text = "false"
    ET.SubElement(document_batch, "mengenlisten_3d", {"Datatype": "Bool"}).text = "false"
    ET.indent(document_batch, space="    ")
    return '<?xml version="1.0" standalone="yes"?>\n' + ET.tostring(
        document_batch, encoding="unicode"
    )


@frappe.whitelist()
def download_sales_orders_xml():
    xml_content = build_sales_orders_xml(get_all_sales_orders())
    frappe.local.response.filename = "sales_orders.xml"
    frappe.local.response.filecontent = xml_content.encode("utf-8")
    frappe.local.response.type = "download"
