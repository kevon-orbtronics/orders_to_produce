import frappe
import xmltodict

COMPANY = frappe.db.get_single_value("Global Defaults", "default_company")
COMPANY_ABBR = frappe.db.get_value("Company", COMPANY, "abbr")



@frappe.whitelist()
def get_work_orders():
    work_orders = frappe.get_all(
        "Work Order",
        filters={"company": COMPANY, "status": ["in", ["Not Started", "In Process"]]},
        fields=["name", "production_item", "qty", "status"],
    )
    return work_orders



"""
<?xml version="1.0" standalone="yes"?>
<documentBatch Datatype="Class" Count="5">
    <version Datatype="Int32">1</version>
    <batchType Datatype="String">OrderBatch</batchType>
    <documentList Datatype="Sequence" Count="17">
        <document Datatype="Class" Count="6">
            <version Datatype="Int32">1</version>
            <documentStubId Datatype="Id">-4925810265788893168</documentStubId>
            <orderNumber Datatype="String">O260909-0281</orderNumber>
            <deliveryNoteNumber Datatype="String"></deliveryNoteNumber>
            <invoiceNumber Datatype="String"></invoiceNumber>
            <subOrderList Datatype="Sequence" Count="0" />
        </document>
        <document Datatype="Class" Count="6">
            <version Datatype="Int32">1</version>
            <documentStubId Datatype="Id">-8089026054067508208</documentStubId>
            <orderNumber Datatype="String">O260909-0271</orderNumber>
            <deliveryNoteNumber Datatype="String"></deliveryNoteNumber>
            <invoiceNumber Datatype="String"></invoiceNumber>
            <subOrderList Datatype="Sequence" Count="0" />
        </document>
    </documentList>
    <quantityLists Datatype="Bool">false</quantityLists>
    <quantityLists3d Datatype="Bool">false</quantityLists3d>
</documentBatch>
"""


import os
import pypyodbc as pyodbc
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


# Server Connexion informations
server = os.getenv('DATABASE_SERVER')
database = os.getenv('DATABASE_NAME')
username = os.getenv('DATABASE_USERNAME')
password = os.getenv('DATABASE_PASSWORD')

cnxn = pyodbc.connect('TrustServerCertificate=yes;DRIVER={ODBC Driver 18 for SQL Server};SERVER='+server+';DATABASE='+database+';ENCRYPT=yes;UID='+username+';PWD='+ password)

def GetDeliveryInformation(Doc_Number):
    cnxn = pyodbc.connect('TrustServerCertificate=yes;DRIVER={ODBC Driver 18 for SQL Server};SERVER='+server+';DATABASE='+database+';ENCRYPT=yes;UID='+username+';PWD='+ password)

    with cnxn:
        cursor = cnxn.cursor()

        Delivery = {"Date":"Null", "Location":"Null","error":""}

        # Get Informations from the document
        try:
            cursor.execute(f"""
            SELECT 
                [BSX_MODDATE]
                ,[BSX_MODUSER]
                ,[BSX_BELEGNR]
                ,[BSX_TECHBELEGNR]
                ,[BSX_BEZEICHNUNG]
                ,[BSX_ERFDATUM]
                ,[BSX_IDERFASSER]
                ,[BSX_BELEGDATUM]
                ,[BSX_LIEFERDATUM]
                ,[BSX_AUFMASSDATUM]
                ,[BSX_MONTAGEDATUM]
                ,[BSX_DRUCKDATUM]
                ,[BSX_VORGANGNR]
                ,[BSX_GP_ID]
                ,[BSX_GP_IDENTNUMMER]
                ,[BSX_1_AUSWAHL_BRANCHDELIVERY]
            FROM [7_16_20210527_122155_KBS_SaintLuP].[dbo].[VKBELEGSTUB]
            where [BSX_BELEGNR] like '{Doc_Number}' """)

            row=cursor.fetchone()
            # print(row)
            Delivery['Date']=row[8].date().isoformat()
            Delivery['Location']=row[15]
            # print(Delivery)
        except Exception as e:
            Delivery['error']=e
            print(f"Delivery Date Fetching error: {e}")
    return Delivery

def GetUserInfos(KlaesUserID):
    cnxn = pyodbc.connect('TrustServerCertificate=yes;DRIVER={ODBC Driver 18 for SQL Server};SERVER='+server+';DATABASE='+database+';ENCRYPT=yes;UID='+username+';PWD='+ password)

    KlaesUser={
        "ID":"",
        "Short_Name":"",
        "Name": "",
        "Description":"",
        "Email": "",
        "error":""
        }
    with cnxn:
        cursor = cnxn.cursor()

        try:
            cursor.execute(f"""
            SELECT [USX_ID]
                ,[USX_USER]
                ,[USX_FULLNAME]
                ,[USX_INFO]
                ,[USX_MAIL]
            FROM [7_16_20210527_122155_KBS_SaintLuP].[dbo].[KLAESUSER]
            Where USX_ID = {KlaesUserID}
            """)
            row=cursor.fetchone()
            KlaesUser['ID']=row[0]
            KlaesUser['Short_Name']=row[1]
            KlaesUser["Name"]=row[2]
            KlaesUser["Description"]=row[3]
            KlaesUser["Email"]=row[4]
            if KlaesUser['Email']=='':
                KlaesUser['Email']=f"{KlaesUser['Short_Name']}@blaise.lc"
        except Exception as e:
            KlaesUser["error"]=e
    return KlaesUser

def GetSalesUserFromOrder(Order_Number):
    cnxn = pyodbc.connect('TrustServerCertificate=yes;DRIVER={ODBC Driver 18 for SQL Server};SERVER='+server+';DATABASE='+database+';ENCRYPT=yes;UID='+username+';PWD='+ password)

    with cnxn:
        cursor = cnxn.cursor()
        try:
            cursor.execute(f"""
                SELECT [BSX_ID]
                    ,[BSX_MODUSER]
                FROM [7_16_20210527_122155_KBS_SaintLuP].[dbo].[VKBELEGSTUB]
                WHERE BSX_BELEGNR like '{Order_Number}'
                """)
            row=cursor.fetchone()
            ID = row[1]
        except Exception as e:
            print(e)
        cursor.close()
    SalesPerson=GetUserInfos(ID)
    return SalesPerson
