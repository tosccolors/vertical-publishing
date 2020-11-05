# -*- coding: utf-8 -*-

from odoo import models, fields, api

class nsm_invoicing_property(models.Model):
	_name = 'invoicing.property'

	name = fields.Char(string="Invoicing Property")
	
	group_invoice_lines_per_period = fields.Boolean(string="Group invoice lines per period")
	group_invoice_lines_per_title = fields.Boolean(string="Group invoice lines per title")
	group_invoice_lines_per_po_number = fields.Boolean(string="Group invoice lines per PO number")
	only_invoice_published_adv = fields.Boolean(string="Only invoice published advertisements")
	group_by_week = fields.Boolean(string="Group by Week")
	group_by_month = fields.Boolean(string="Group by Month")
	pre_pay_publishing_add = fields.Boolean(string="Group by pre-pay publishing advertisements")
	pre_pay_online_add = fields.Boolean(string="Group by pre-pay online advertisements")
	# remove above
	group_by_edition = fields.Boolean(string="Group by Edition")
	group_by_order = fields.Boolean(string="Group by order")
	group_by_advertiser = fields.Boolean(string="Group by Advertiser")
	group_by_online_separate = fields.Boolean(string="Group by online / print separate")


	# newly added
	inv_package_deal = fields.Boolean(string="Invoice package deal")
	inv_per_line_adv_print = fields.Boolean(string="Invoice per OrderLine in advance print")
	inv_per_line_after_online = fields.Boolean(string="Invoice per OrderLine afterwards online")
	inv_whole_order_at_once = fields.Boolean(string="Invoice whole order at once")
	pay_in_terms = fields.Boolean(string="Pay in terms")

	inv_per_line_after_print = fields.Boolean(string="Invoice per orderline afterwards print")
	inv_per_line_adv_online = fields.Boolean(string="Invoice per orderline in advance online")


	