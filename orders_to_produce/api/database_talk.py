import frappe

from orders_to_produce.api.klaes_db import get_connection


def GetDeliveryInformation(Doc_Number):
	Delivery = {"Date": None, "Location": None, "error": ""}

	try:
		with get_connection() as cnxn:
			cursor = cnxn.cursor()
			cursor.execute(
				"""
				SELECT [BSX_LIEFERDATUM], [BSX_1_AUSWAHL_BRANCHDELIVERY]
				FROM [dbo].[VKBELEGSTUB]
				WHERE [BSX_BELEGNR] = ?
				""",
				(Doc_Number,),
			)
			row = cursor.fetchone()
		if row is None:
			Delivery["error"] = f"Document {Doc_Number} not found"
			return Delivery
		Delivery["Date"] = row[0].date().isoformat() if row[0] else None
		Delivery["Location"] = row[1]
	except Exception as e:
		Delivery["error"] = str(e)
		frappe.log_error(title="Klaes delivery info fetch failed", message=str(e))
	return Delivery


def GetUserInfos(KlaesUserID):
	KlaesUser = {
		"ID": "",
		"Short_Name": "",
		"Name": "",
		"Description": "",
		"Email": "",
		"error": "",
	}

	try:
		with get_connection() as cnxn:
			cursor = cnxn.cursor()
			cursor.execute(
				"""
				SELECT [USX_ID], [USX_USER], [USX_FULLNAME], [USX_INFO], [USX_MAIL]
				FROM [dbo].[KLAESUSER]
				WHERE [USX_ID] = ?
				""",
				(KlaesUserID,),
			)
			row = cursor.fetchone()
		if row is None:
			KlaesUser["error"] = f"Klaes user {KlaesUserID} not found"
			return KlaesUser
		KlaesUser["ID"] = row[0]
		KlaesUser["Short_Name"] = row[1]
		KlaesUser["Name"] = row[2]
		KlaesUser["Description"] = row[3]
		KlaesUser["Email"] = row[4] or f"{row[1]}@blaise.lc"
	except Exception as e:
		KlaesUser["error"] = str(e)
		frappe.log_error(title="Klaes user fetch failed", message=str(e))
	return KlaesUser


def GetSalesUserFromOrder(Order_Number):
	try:
		with get_connection() as cnxn:
			cursor = cnxn.cursor()
			cursor.execute(
				"""
				SELECT [BSX_MODUSER]
				FROM [dbo].[VKBELEGSTUB]
				WHERE [BSX_BELEGNR] = ?
				""",
				(Order_Number,),
			)
			row = cursor.fetchone()
	except Exception as e:
		frappe.log_error(title="Klaes sales user fetch failed", message=str(e))
		return {"error": str(e)}

	if row is None:
		return {"error": f"Order {Order_Number} not found"}
	return GetUserInfos(row[0])


def get_all_user_ids():
	try:
		with get_connection() as cnxn:
			cursor = cnxn.cursor()
			cursor.execute("SELECT [USX_FULLNAME] FROM [dbo].[KLAESUSER]")
			rows = cursor.fetchall()
	except Exception as e:
		frappe.log_error(title="Klaes user list fetch failed", message=str(e))
		return {"data": [], "error": str(e)}
	return {"data": [row[0] for row in rows], "error": ""}


@frappe.whitelist()
def say_hi_as_pdf():
	userInfo = get_all_user_ids()
	html = frappe.render_template("orders_to_produce/templates/test_page.html", userInfo)
	pdf = frappe.utils.pdf.get_pdf(html)
	frappe.local.response.filename = "hi.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"
