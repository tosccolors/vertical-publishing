# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError


# need to check w.r.t v14
class AccountInvoiceRefund(models.TransientModel):
	"""Refunds invoice"""

	_inherit = "account.invoice.refund"
	_description = "Invoice Refund"

	
	def compute_refund(self, mode='refund'):
		''''
		Adds refund invoice line to sol.sale_line
		'''
		res = super(AccountInvoiceRefund, self).compute_refund(mode)
		# code added for checking which invoice is used for modifying and refund option and the link is added in sale order line invoice lines
		for inv in self.env['account.move'].browse(self.env.context.get('active_ids')):
			for line in inv.invoice_line_ids:
				sale_line_id = self.env['sale.order.line'].search([('id','=',line.so_line_id.id)])
				if sale_line_id:
					for sale_line in sale_line_id:
						if inv.type =='out_invoice':
							if mode == 'modify':
								inv.modify_refund_created = True
							sale_line.invoice_lines = [(4, line.id)]
						if inv.type == 'out_refund':
							sale_line.invoice_lines = [(4, line.id)]
						#fetch the invoice lines to add the removed lines from standard
						inv_line_ids = self.env['account.move.line'].search([('so_line_id','=',sale_line.id)])
						for inv_line in inv_line_ids:
							if inv_line.invoice_id.state != 'cancel':
								sale_line.invoice_lines = [(4, inv_line.id)]
		return res
