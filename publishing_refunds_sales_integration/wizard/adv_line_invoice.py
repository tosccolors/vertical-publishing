# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.queue_job.exception import FailedJobError
from unidecode import unidecode


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
		#invoice = self.env['account.invoice'].search([('id','=', res)])
		for invoice_line in invoice.invoice_line_ids:
			sale_order_lines_on_invoice = self.env['sale.order.line'].search([('id','=', invoice_line.so_line_id.id)])
			if not sale_order_lines_on_invoice:
				continue
			for sale_order_line in sale_order_lines_on_invoice:
				if invoice.type in ('out_invoice', 'out_refund'):
					sale_order_line.invoice_lines = [(4, invoice_line.id)]
		return invoice

	@api.multi
	def _prepare_invoice_line(self, line):
		res = super(AdOrderLineMakeInvoice, self)._prepare_invoice_line(line)
		if line.qty_invoiced:
			res['quantity'] = line.product_uom_qty - \
			line.qty_invoiced
		else:
			res['quantity'] = line.product_uom_qty
		return res

