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


	@job
	@api.multi
	def make_invoices_job_queue(self, inv_date, post_date, chunk):
		invoices = {}
		def make_invoice(partner, published_customer, payment_mode, operating_unit, lines, inv_date, post_date,customer_contact):
			vals = self._prepare_invoice(partner, published_customer, payment_mode, operating_unit,
										 lines, inv_date, post_date,customer_contact)
			
			invoice = self.env['account.invoice'].create(vals)
			for line in invoice.invoice_line_ids:
				sale_line_id = self.env['sale.order.line'].search([('id','=',line.so_line_id.id)])

				if sale_line_id:
					for sale_line in sale_line_id:
						if invoice.type =='out_invoice':
							sale_line.invoice_lines = [(4, line.id)]
						if invoice.type == 'out_refund':
							sale_line.invoice_lines = [(4, line.id)]
					#fetch the invoice lines to add the removed lines from standard 
						inv_line_ids = self.env['account.invoice.line'].search([('so_line_id','=',sale_line.id)])
						for inv_line in inv_line_ids:
							if inv_line.invoice_id.state != 'cancel':
								sale_line.invoice_lines = [(4, inv_line.id)]
			invoice.compute_taxes()
			return invoice.id
		count = 0
		for line in chunk:
			key = (line.order_id.partner_invoice_id, line.order_id.published_customer, line.order_id.payment_mode_id,
				   line.order_id.operating_unit_id,line.order_id.customer_contact)
			if (line.state in ('sale', 'done')) :
				if not key in invoices:
					invoices[key] = {'lines':[], 'name': ''}

				inv_line_vals = self._prepare_invoice_line(line)
				invoices[key]['lines'].append((0, 0, inv_line_vals))
				if count < 3:
					invoices[key]['name'] += unidecode(line.name)+' / '
				count += 1

		
		if not invoices and not self.job_queue:
			raise UserError(_('Invoice cannot be created for this Advertising Order Line due to one of the following reasons:\n'
							  '1.The state of these ad order lines are not "sale" or "done"!\n'
							  '2.The Lines are already Invoiced!\n'))
		elif not invoices:
			raise FailedJobError(_('Invoice cannot be created for this Advertising Order Line due to one of the following reasons:\n'
								  '1.The state of these ad order lines are not "sale" or "done"!\n'
								  '2.The Lines are already Invoiced!\n'))
		for key, il in invoices.items():
			partner = key[0]
			published_customer = key[1]
			payment_mode = key[2]
			operating_unit = key[3]
			customer_contact = key[4]
			try:
				make_invoice(partner, published_customer, payment_mode, operating_unit, il, inv_date, post_date,customer_contact)
			except Exception, e:
				if self.job_queue:
					raise FailedJobError(_("The details of the error:'%s' regarding '%s'") % (unicode(e), il['name'] ))
				else:
					raise UserError(_("The details of the error:'%s' regarding '%s'") % (unicode(e), il['name'] ))
		return True




	@api.multi
	def _prepare_invoice_line(self, line):
		res = super(AdOrderLineMakeInvoice, self)._prepare_invoice_line(line)
		if line.qty_invoiced:
			res['quantity'] = line.product_uom_qty - \
			line.qty_invoiced
		else:
			res['quantity'] = 10
		return res

