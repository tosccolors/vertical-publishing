# -*- coding: utf-8 -*-

from odoo import models, fields, api

class nsm_invoicing_property(models.Model):
	_name = 'invoicing.property'

	name = fields.Char(string="Invoicing Property")
	
	group_by_advertiser = fields.Boolean(string="Group by Advertiser")

	active = fields.Boolean(default=True)

	# Correct invoice properties
	group_by_order = fields.Boolean(string="Group order lines with the same SO number on one invoice")
	inv_package_deal = fields.Boolean(string="Invoice as package deal")
	inv_per_line_adv_print = fields.Boolean(string="Invoice print order lines on or after the selected date, invoice online order lines on or after startdate")
	inv_per_line_after_online = fields.Boolean(string="Deprecated")
	inv_whole_order_at_once = fields.Boolean(string="Invoice all order lines on or after selected date ")
	inv_whole_order_afterwards = fields.Boolean(string="Invoice print order lines on or after issue date, invoice online order lines on or after start date")
	pay_in_terms = fields.Boolean(string="Invoice in terms")
	inv_per_line_after_print = fields.Boolean(string="Invoice per OrderLine afterwards print")
	inv_per_line_adv_online = fields.Boolean(string="Invoice online order lines on or after the selected date, invoice print order lines on or after issue date")
	default_property = fields.Boolean(string="Check if it is a default property", compute="check_default_property")
	inv_manually = fields.Boolean(string="Invoice Manually")

	# The invoice properties below are deprecated, and should be removed if the database allows it
	group_invoice_lines_per_period = fields.Boolean(string="Group invoice lines per period")
	group_invoice_lines_per_title = fields.Boolean(string="Group invoice lines per title")
	group_invoice_lines_per_po_number = fields.Boolean(string="Group invoice lines per PO number")
	only_invoice_published_adv = fields.Boolean(string="Only invoice published advertisements")
	group_by_week = fields.Boolean(string="Group by Week")
	group_by_month = fields.Boolean(string="Group by Month")
	pre_pay_publishing_add = fields.Boolean(string="Group by pre-pay publishing advertisements")
	pre_pay_online_add = fields.Boolean(string="Group by pre-pay online advertisements")
	group_by_online_separate = fields.Boolean(string="Group by online / print separate")
	group_by_edition = fields.Boolean(string="Group by Edition")

	@api.depends('group_by_edition','group_by_order','group_by_advertiser','group_by_online_separate','inv_package_deal','inv_per_line_adv_print','inv_per_line_after_online',
		'inv_whole_order_at_once','pay_in_terms','inv_per_line_after_print','inv_per_line_adv_online','inv_whole_order_afterwards')
	def check_default_property(self):
		if self.group_by_edition or self.group_by_order or self.group_by_advertiser \
				or self.group_by_online_separate  or self.inv_package_deal  or self.inv_per_line_adv_print  \
				or self.inv_per_line_after_online  or self.inv_whole_order_at_once  \
				or self.pay_in_terms  or self.inv_per_line_after_print  or self.inv_per_line_adv_online  or self.inv_whole_order_afterwards  or self.inv_manually :
			self.default_property = False
		else:
			self.default_property = True

	@api.onchange('inv_package_deal', 'pay_in_terms')
	def _onchange_inv_package_deal(self):
		if self.inv_package_deal or self.pay_in_terms:
			self.inv_manually = self.group_by_order = self.inv_per_line_after_print = self.inv_per_line_adv_print = self.inv_per_line_after_online = self.inv_whole_order_at_once = self.inv_whole_order_afterwards = self.inv_per_line_adv_online = False

	@api.onchange('inv_per_line_after_print')
	def _onchange_invoice_timing_inv_per_line_after_print(self):
		if self.inv_per_line_after_print:
			self.inv_manually = self.inv_per_line_adv_print = self.inv_package_deal = self.pay_in_terms = self.inv_per_line_after_online = self.inv_whole_order_at_once = self.inv_whole_order_afterwards = self.inv_per_line_adv_online = False

	@api.onchange('inv_per_line_adv_print')
	def _onchange_invoice_timing_inv_per_line_adv_print(self):
		if self.inv_per_line_adv_print:
			self.inv_manually = self.inv_per_line_after_print = self.inv_package_deal = self.pay_in_terms = self.inv_per_line_after_online = self.inv_whole_order_at_once = self.inv_whole_order_afterwards = self.inv_per_line_adv_online = False

	@api.onchange('inv_per_line_after_online')
	def _onchange_invoice_timing_inv_per_line_after_online(self):
		if self.inv_per_line_after_online:
			self.inv_manually = self.inv_per_line_after_print = self.inv_package_deal = self.pay_in_terms = self.inv_per_line_adv_print = self.inv_whole_order_at_once = self.inv_whole_order_afterwards = self.inv_per_line_adv_online = False

	@api.onchange('inv_whole_order_at_once')
	def _onchange_invoice_timing_inv_whole_order_at_once(self):
		if self.inv_whole_order_at_once:
			self.inv_manually = self.inv_per_line_after_print = self.inv_package_deal = self.pay_in_terms = self.inv_per_line_adv_print = self.inv_per_line_after_online = self.inv_whole_order_afterwards = self.inv_per_line_adv_online = False

	@api.onchange('inv_whole_order_afterwards')
	def _onchange_invoice_timing_inv_whole_order_afterwards(self):
		if self.inv_whole_order_afterwards:
			self.inv_manually = self.inv_per_line_after_print = self.inv_package_deal = self.pay_in_terms = self.inv_per_line_adv_print = self.inv_per_line_after_online = self.inv_whole_order_at_once = self.inv_per_line_adv_online = False

	@api.onchange('inv_per_line_adv_online')
	def _onchange_invoice_timing_inv_per_line_adv_online(self):
		if self.inv_per_line_adv_online:
			self.inv_manually = self.inv_per_line_after_print = self.inv_package_deal = self.pay_in_terms = self.inv_per_line_adv_print = self.inv_per_line_after_online = self.inv_whole_order_at_once = self.inv_whole_order_afterwards = False

	@api.onchange('inv_manually')
	def _onchange_invoice_manually(self):
		if self.inv_manually:
			self.inv_package_deal = self.pay_in_terms = self.group_by_order = self.inv_per_line_after_print = self.inv_per_line_adv_print = self.inv_per_line_after_online = self.inv_whole_order_at_once = self.inv_whole_order_afterwards = self.inv_per_line_adv_online = False
