import frappe


@frappe.whitelist()
def get_work_orders():
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    work_orders = frappe.get_all(
        "Work Order",
        filters={"company": company, "status": ["in", ["Not Started", "In Process"]]},
        fields=["name", "production_item", "qty", "status"],
    )
    return work_orders


# Sample of the batch XML format Klaes expects (English tag names).
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
