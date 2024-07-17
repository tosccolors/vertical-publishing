# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AdOrderLineMakeInvoice(models.TransientModel):
	_inherit = "ad.order.line.make.invoice"
	_description = "Advertising Order Line Make_invoice"


	@api.model
	def _prepare_invoice(self, keydict, lines, invoice_date, posting_date):
		vals = super(AdOrderLineMakeInvoice, self)._prepare_invoice(keydict, lines, invoice_date, posting_date)
		vals['date'] = False
		return vals

	def make_invoice(self, keydict, lines, inv_date, post_date):
		"""Links newly created invoice lines to order lines in case of a refund invoice"""
		invoice = super(AdOrderLineMakeInvoice, self).make_invoice(keydict, lines, inv_date, post_date)

		for invoice_line in invoice.invoice_line_ids:
			sale_order_lines_on_invoice = self.env['sale.order.line'].search([('id','=', invoice_line.so_line_id.id)])
			if not sale_order_lines_on_invoice:
				continue
			for sale_order_line in sale_order_lines_on_invoice:
				if invoice.type in ('out_invoice', 'out_refund'):
					sale_order_line.invoice_lines = [(4, invoice_line.id)]
		return invoice

	
	def _prepare_invoice_line(self, line):
		res = super(AdOrderLineMakeInvoice, self)._prepare_invoice_line(line)
		if line.qty_invoiced:
			res['quantity'] = line.product_uom_qty - \
			line.qty_invoiced
		else:
			res['quantity'] = line.product_uom_qty
		return res

