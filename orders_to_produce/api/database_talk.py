import pypyodbc as pyodbc
import frappe

cnxn = pyodbc.connect('TrustServerCertificate=yes;DRIVER={ODBC Driver 18 for SQL Server};SERVER='+server+';DATABASE='+database+';ENCRYPT=yes;UID='+username+';PWD='+ password)

def GetDeliveryInformation(Doc_Number):
    cnxn = pyodbc.connect('TrustServerCertificate=yes;DRIVER={ODBC Driver 18 for SQL Server};SERVER='+os.getenv('DATABASE_SERVER')+';DATABASE='+os.getenv('DATABASE_NAME')+';ENCRYPT=yes;UID='+os.getenv('DATABASE_USERNAME')+';PWD='+os.getenv('DATABASE_PASSWORD'))

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
            FROM [{database}].[dbo].[VKBELEGSTUB]
            where [BSX_BELEGNR] like '{Doc_Number}' """)

            row=cursor.fetchone()
            # print(row)
            #Delivery['Date']=row[8].date().isoformat()
            Delivery['Location']=row[1]
            # print(Delivery)
        except Exception as e:
            Delivery['error']=e
            Delivery['Location']="Fake location bro"
            print(f"Delivery Date Fetching error: {e}")
    return Delivery

def GetUserInfos(KlaesUserID):
    cnxn = pyodbc.connect('TrustServerCertificate=yes;DRIVER={ODBC Driver 18 for SQL Server};SERVER='+server+/';DATABASE='+database+';ENCRYPT=yes;UID='+username+';PWD='+ password)

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
            FROM [{database}].[dbo].[KLAESUSER]
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


def get_all_user_ids():
    cnxn = pyodbc.connect('TrustServerCertificate=yes;DRIVER={ODBC Driver 18 for SQL Server};SERVER='+server+';DATABASE='+database+';ENCRYPT=yes;UID='+username+';PWD='+ password)
    with cnxn:
        cursor = cnxn.cursor()
        try:
            cursor.execute(f"""
            SELECT [USX_FULLNAME]
            FROM [{database}].[dbo].[KLAESUSER]
            """)
            row=cursor.fetchone()
        except Exception as e:
            return {'data': 'error bro'}
    return {'data': str(row)}

@frappe.whitelist()
def say_hi_as_pdf():
    userInfo = get_all_user_ids()
    html = frappe.render_template("orders_to_produce/templates/test_page.html", userInfo)
    pdf = frappe.utils.pdf.get_pdf(html)
    frappe.local.response.filename = "hi.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "pdf"