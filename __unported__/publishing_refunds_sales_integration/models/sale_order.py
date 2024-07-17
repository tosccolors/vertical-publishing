# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	@api.depends('invoice_lines.invoice_id.state', 'invoice_lines.quantity')
	def _get_invoice_qty(self):
		"""
		Compute the quantity invoiced. If case of a refund, the quantity invoiced is decreased. Note
		that this is the case only if the refund is generated from the SO and that is intentional: if
		a refund made would automatically decrease the invoiced quantity, then there is a risk of reinvoicing
		it automatically, which may not be wanted at all. That's why the refund has to be created from the SO
		"""
		for line in self:
			qty_invoiced = 0.0
			for invoice_line in line.invoice_lines:
				if invoice_line.invoice_id.state != 'cancel':
					if invoice_line.invoice_id.type == 'out_invoice':
						# if invoice_line.invoice_id.modify_refund_created == False:
						qty_invoiced += invoice_line.uom_id._compute_quantity(invoice_line.quantity, line.product_uom)
					elif invoice_line.invoice_id.type == 'out_refund':
						# if invoice_line.invoice_id.modify_refund_created == False:
						qty_invoiced -= invoice_line.uom_id._compute_quantity(invoice_line.quantity, line.product_uom)
			line.qty_invoiced = qty_invoiced