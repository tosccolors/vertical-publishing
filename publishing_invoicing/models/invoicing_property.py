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
	group_by_online_separate = fields.Boolean(string="Group by online / print separate")
	# remove above
	group_by_edition = fields.Boolean(string="Group by Edition")
	group_by_order = fields.Boolean(string="Group by Order")
	group_by_advertiser = fields.Boolean(string="Group by Advertiser")
	


	# newly added
	inv_package_deal = fields.Boolean(string="Invoice package deal")
	inv_per_line_adv_print = fields.Boolean(string="Invoice per OrderLine in advance print")
	inv_per_line_after_online = fields.Boolean(string="Invoice per OrderLine afterwards online")
	inv_whole_order_at_once = fields.Boolean(string="Invoice whole order in advance")
	inv_whole_order_afterwards = fields.Boolean(string="Invoice whole order afterwards")
	pay_in_terms = fields.Boolean(string="Pay in terms")

	inv_per_line_after_print = fields.Boolean(string="Invoice per OrderLine afterwards print")
	inv_per_line_adv_online = fields.Boolean(string="Invoice per OrderLine in advance online")

	default_property = fields.Boolean(string="Check if it is a default property",compute="check_default_property")


	@api.depends('group_by_edition','group_by_order','group_by_advertiser','group_by_online_separate','inv_package_deal','inv_per_line_adv_print','inv_per_line_after_online',
		'inv_whole_order_at_once','pay_in_terms','inv_per_line_after_print','inv_per_line_adv_online','inv_whole_order_afterwards')
	def check_default_property(self):
		for line in self:
			if line.group_by_edition == True or line.group_by_order == True or line.group_by_advertiser == True  \
					or line.group_by_online_separate == True or line.inv_package_deal == True or line.inv_per_line_adv_print == True \
					or line.inv_per_line_after_online == True or line.inv_whole_order_at_once == True \
					or line.pay_in_terms == True or line.inv_per_line_after_print == True or line.inv_per_line_adv_online == True or line.inv_whole_order_afterwards == True:
				line.default_property = False
			else:
				line.default_property = True


	@api.onchange('group_by_order')
	def _onchange_invoicing_layout_group_by_order(self):
		for line in self:
			if line.group_by_order == True:
				line.group_by_edition = False
				line.group_by_advertiser = False
	@api.onchange('group_by_edition')
	def _onchange_invoicing_layout_group_by_edition(self):
		for line in self:
			if line.group_by_edition == True:
				line.group_by_order = False
				line.group_by_advertiser = False
	@api.onchange('group_by_advertiser')
	def _onchange_invoicing_layout_group_by_advertiser(self):
		for line in self:
			if line.group_by_advertiser == True:
				line.group_by_edition = False
				line.group_by_order = False


	@api.onchange('inv_per_line_after_print')
	def _onchange_invoice_timing_inv_per_line_after_print(self):
		for line in self:
			if line.inv_per_line_after_print == True:
				line.inv_per_line_adv_print = line.inv_per_line_after_online = line.inv_whole_order_at_once = line.inv_whole_order_afterwards = line.inv_per_line_adv_online = False

	@api.onchange('inv_per_line_adv_print')
	def _onchange_invoice_timing_inv_per_line_adv_print(self):
		for line in self:
			if line.inv_per_line_adv_print == True:
				line.inv_per_line_after_print = line.inv_per_line_after_online = line.inv_whole_order_at_once = line.inv_whole_order_afterwards = line.inv_per_line_adv_online = False

	@api.onchange('inv_per_line_after_online')
	def _onchange_invoice_timing_inv_per_line_after_online(self):
		for line in self:
			if line.inv_per_line_after_online == True:
				line.inv_per_line_after_print = line.inv_per_line_adv_print = line.inv_whole_order_at_once = line.inv_whole_order_afterwards = line.inv_per_line_adv_online = False

	@api.onchange('inv_whole_order_at_once')
	def _onchange_invoice_timing_inv_whole_order_at_once(self):
		for line in self:
			if line.inv_whole_order_at_once == True:
				line.inv_per_line_after_print = line.inv_per_line_adv_print = line.inv_per_line_after_online = line.inv_whole_order_afterwards = line.inv_per_line_adv_online = False

	@api.onchange('inv_whole_order_afterwards')
	def _onchange_invoice_timing_inv_whole_order_afterwards(self):
		for line in self:
			if line.inv_whole_order_afterwards == True:
				line.inv_per_line_after_print = line.inv_per_line_adv_print = line.inv_per_line_after_online = line.inv_whole_order_at_once = line.inv_per_line_adv_online = False

	@api.onchange('inv_per_line_adv_online')
	def _onchange_invoice_timing_inv_per_line_adv_online(self):
		for line in self:
			if line.inv_per_line_adv_online == True:
				line.inv_per_line_after_print = line.inv_per_line_adv_print = line.inv_per_line_after_online = line.inv_whole_order_at_once = line.inv_whole_order_afterwards = False










	