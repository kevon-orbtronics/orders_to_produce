import pypyodbc as pyodbc
import frappe
import os
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def get_connection_to_database():
    cnxn = pyodbc.connect('TrustServerCertificate=yes;DRIVER={ODBC Driver 18 for SQL Server};SERVER='+os.getenv('DATABASE_SERVER')+';DATABASE='+os.getenv('DATABASE_NAME')+';ENCRYPT=yes;UID='+os.getenv('DATABASE_USERNAME')+';PWD='+os.getenv('DATABASE_PASSWORD'))
    return cnxn

def get_all_sales_orders(database_name = os.getenv('DATABASE_NAME')):
    #cnxn = get_connection_to_database()
    cnxn = pyodbc.connect('TrustServerCertificate=yes;DRIVER={ODBC Driver 18 for SQL Server};SERVER='+os.getenv('DATABASE_SERVER')+';DATABASE='+os.getenv('DATABASE_NAME')+';ENCRYPT=yes;UID='+os.getenv('DATABASE_USERNAME')+';PWD='+os.getenv('DATABASE_PASSWORD'))
    with cnxn:
        cursor = cnxn.cursor()
        try:
            cursor.execute(f"""
            SELECT TOP 20
                [VKB_ID],
                [VKB_MODDATE],
                [VKB_MODUSER],
                [VKB_NUMMER],
                [VKB_STATE]
            FROM 
                [{database_name}].[dbo].[VKVORGANGBELEG]
            ORDER BY VKB_MODDATE DESC;
            """
            )
            row = cursor.fetchall()
            sales_orders = []
            for r in row:
                sales_order = {
                    "VKB_ID": r[0],
                    "VKB_MODDATE": r[1],
                    "VKB_MODUSER": r[2],
                    "VKB_NUMMER": r[3],
                    "VKB_STATE": r[4]
                }
                sales_orders.append(sales_order)
            return sales_orders
        except Exception as e:
            print(f"Error fetching sales orders: {e}")
            return []

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
            sales_order.get("VKB_ID") or ""
        )
        ET.SubElement(document, "auftragnr", {"Datatype": "String"}).text = str(
            sales_order.get("VKB_NUMMER") or ""
        )
        ET.SubElement(document, "leiferscheinnr", {"Datatype": "String"})
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

