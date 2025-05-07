import frappe
from frappe.model.document import Document
from frappe import _

def on_update(doc, method):
    if doc.custom_item_tax_template:
        tax_template = frappe.get_doc('Tax Template', doc.custom_item_tax_template)

        if not doc.taxes:
            for tax_row in tax_template.taxes:
                doc.append('taxes', {
                    'item_tax_template': tax_row.item_tax_template,
                    'tax_category': tax_row.tax_category,
                    'valid_from': tax_row.valid_from,
                    'minimum_net_rate': tax_row.minimum_net_rate,
                    'maximum_net_rate': tax_row.maximum_net_rate
                })