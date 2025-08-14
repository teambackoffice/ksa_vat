# Copyright (c) 2025, Ashkar and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.utils import get_url_to_list


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "title",
			"label": _("Title"),
			"fieldtype": "Data",
			"width": 300,
		},
		{
			"fieldname": "amount",
			"label": _("Amount (SAR)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "adjustment_amount",
			"label": _("Adjustment (SAR)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "vat_amount",
			"label": _("VAT Amount (SAR)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Currency",
			"width": 150,
			"hidden": 1,
		},
	]


def get_data(filters):
	data = []

	# Validate if vat settings exist
	company = filters.get("company")
	company_currency = frappe.get_cached_value("Company", company, "default_currency")

	if frappe.db.exists("KSA VAT Setting", company) is None:
		url = get_url_to_list("KSA VAT Setting")
		frappe.msgprint(_('Create <a href="{}">KSA VAT Setting</a> for this company').format(url))
		return data

	ksa_vat_setting = frappe.get_doc("KSA VAT Setting", company)

	# Sales Heading
	append_data(data, "VAT on Sales", "", "", "", company_currency)

	grand_total_taxable_amount = 0
	grand_total_taxable_adjustment_amount = 0
	grand_total_tax = 0

	for vat_setting in ksa_vat_setting.ksa_vat_sales_accounts:
		(
			total_taxable_amount,
			total_taxable_adjustment_amount,
			total_tax,
		) = get_tax_data_for_each_vat_setting(vat_setting, filters, "Sales Invoice")

		append_data(
			data,
			vat_setting.title,
			total_taxable_amount,
			total_taxable_adjustment_amount,
			total_tax,
			company_currency,
		)

		grand_total_taxable_amount += total_taxable_amount
		grand_total_taxable_adjustment_amount += total_taxable_adjustment_amount
		grand_total_tax += total_tax

	append_data(
		data,
		"Grand Total",
		grand_total_taxable_amount,
		grand_total_taxable_adjustment_amount,
		grand_total_tax,
		company_currency,
	)

	append_data(data, "", "", "", "", company_currency)

	# Purchase Heading
	append_data(data, "VAT on Purchases", "", "", "", company_currency)

	grand_total_taxable_amount = 0
	grand_total_taxable_adjustment_amount = 0
	grand_total_tax = 0

	# Check if purchase accounts exist
	if not ksa_vat_setting.ksa_vat_purchase_accounts:
		append_data(
			data,
			"No Purchase VAT Settings Configured",
			0,
			0,
			0,
			company_currency,
		)
	else:
		for vat_setting in ksa_vat_setting.ksa_vat_purchase_accounts:
			(
				total_taxable_amount,
				total_taxable_adjustment_amount,
				total_tax,
			) = get_tax_data_for_each_vat_setting(vat_setting, filters, "Purchase Invoice")

			append_data(
				data,
				vat_setting.title,
				total_taxable_amount,
				total_taxable_adjustment_amount,
				total_tax,
				company_currency,
			)

			grand_total_taxable_amount += total_taxable_amount
			grand_total_taxable_adjustment_amount += total_taxable_adjustment_amount
			grand_total_tax += total_tax

	append_data(
		data,
		"Grand Total",
		grand_total_taxable_amount,
		grand_total_taxable_adjustment_amount,
		grand_total_tax,
		company_currency,
	)

	return data


def get_tax_data_for_each_vat_setting(vat_setting, filters, doctype):
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	total_taxable_amount = 0
	total_taxable_adjustment_amount = 0
	total_tax = 0

	# Get company from filters for additional filtering
	company = filters.get("company")

	invoices = frappe.get_all(
		doctype,
		filters={
			"docstatus": 1, 
			"posting_date": ["between", [from_date, to_date]],
			"company": company
		},
		fields=["name", "is_return"],
	)

	for invoice in invoices:
		# First check if invoice has any items with the specific item_tax_template
		invoice_items = frappe.get_all(
			f"{doctype} Item",
			filters={
				"docstatus": 1,
				"parent": invoice.name,
				"item_tax_template": vat_setting.item_tax_template,
			},
			fields=["item_code", "net_amount", "base_net_amount"],
		)

		# If no items match the tax template, check if there are items without tax template
		# but the invoice has the tax account in taxes table
		if not invoice_items:
			# Check if this invoice has the tax account
			has_tax_account = frappe.db.exists(
				"Purchase Taxes and Charges" if doctype == "Purchase Invoice" else "Sales Taxes and Charges",
				{
					"docstatus": 1,
					"parent": invoice.name,
					"account_head": vat_setting.account
				}
			)
			
			if has_tax_account:
				# Get all items for this invoice (fallback when item tax template is not set)
				invoice_items = frappe.get_all(
					f"{doctype} Item",
					filters={
						"docstatus": 1,
						"parent": invoice.name,
					},
					fields=["item_code", "net_amount", "base_net_amount"],
				)

		if not invoice_items:
			continue  # Skip this invoice if no matching items

		for item in invoice_items:
			# Use base_net_amount if available, otherwise use net_amount
			amount = item.get("base_net_amount") or item.get("net_amount") or 0
			
			if invoice.is_return == 0:
				total_taxable_amount += amount
			elif invoice.is_return == 1:
				total_taxable_adjustment_amount += amount

		# Add tax only if matching items exist
		total_tax += get_tax_amount(vat_setting.account, doctype, invoice.name)

	return total_taxable_amount, total_taxable_adjustment_amount, total_tax


def append_data(data, title, amount, adjustment_amount, vat_amount, company_currency):
	data.append(
		{
			"title": _(title),
			"amount": amount,
			"adjustment_amount": adjustment_amount,
			"vat_amount": vat_amount,
			"currency": company_currency,
		}
	)


def get_tax_amount(account_head, doctype, parent):
	if doctype == "Sales Invoice":
		tax_doctype = "Sales Taxes and Charges"
	elif doctype == "Purchase Invoice":
		tax_doctype = "Purchase Taxes and Charges"
	else:
		return 0

	# Get all tax entries for this invoice and account
	tax_entries = frappe.get_all(
		tax_doctype,
		filters={
			"docstatus": 1, 
			"parent": parent, 
			"account_head": account_head
		},
		fields=["tax_amount", "base_tax_amount"]
	)

	total_tax_amount = 0
	for entry in tax_entries:
		# Use base_tax_amount if available, otherwise use tax_amount
		tax_amount = entry.get("base_tax_amount") or entry.get("tax_amount") or 0
		total_tax_amount += tax_amount

	return total_tax_amount
