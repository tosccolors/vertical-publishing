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


	@api.multi
	def make_invoices_from_lines(self):
		"""
			 To make invoices.
		"""
		context = self._context
		inv_date = self.invoice_date
		post_date = self.posting_date
		size = False
		eta  = False
		jq   = False
		if self.job_queue:
			jq = self.job_queue
			size = self.chunk_size
			eta = fields.Datetime.from_string(self.execution_datetime)
		if not context.get('active_ids', []):
			raise UserError(_('No Ad Order lines are selected for invoicing:\n'))
		else:
			lids = context.get('active_ids', [])
			OrderLines = self.env['sale.order.line'].browse(lids)
			invoice_date_ctx = context.get('invoice_date', False)
			posting_date_ctx = context.get('posting_date', False)
			jq_ctx = context.get('job_queue', False)
			size_ctx = context.get('chunk_size', False)
			eta_ctx = context.get('execution_datetime', False)
		if invoice_date_ctx and not inv_date:
			inv_date = invoice_date_ctx
		if posting_date_ctx and not post_date:
			post_date = posting_date_ctx
		if jq_ctx and not jq:
			jq = True
			if len(self)==1:
				self.job_queue = True
			if size_ctx and not size:
				size = size_ctx
			if eta_ctx and not eta:
				eta = fields.Datetime.from_string(eta_ctx)
		if jq:
			description = context.get('job_queue_description', False)
			if description :
				self.with_delay(eta=eta, description=description).make_invoices_split_lines_jq(inv_date, post_date, OrderLines, eta, size)
			else :
				self.with_delay(eta=eta).make_invoices_split_lines_jq(inv_date, post_date, OrderLines, eta, size)
			return "Lines dispatched for async processing. See separate job(s) for result(s).\n"
		else:
			# get list of invoicing properties and remove duplicate
			inv_property_ids = []
			group_title_id = []
			group_advertiser_id = []
			set_invoice_property = set_group_by_title = set_customer_ids = set_inv_property_ids = set_advertiser_ids = 0
			group_by_title = []
			customer_ids = []
			advertiser_ids = []
			group_adv_issue_id = []
			for line in OrderLines:
				inv_property_ids.append(line.order_id.invoicing_property_id)
				customer_ids.append(line.order_id.partner_id.id)
				advertiser_ids.append(line.order_id.published_customer.id)
			set_inv_property_ids = list(set(inv_property_ids))
			set_customer_ids = list(set(customer_ids))
			set_advertiser_ids = list(set(advertiser_ids))
			title_count = 0
			for inv_ids in set_inv_property_ids:
				# Group by order
				if inv_ids.group_by_order == True and inv_ids.group_by_advertiser == False and inv_ids.group_by_edition == False and inv_ids.default_property == False and \
				   inv_ids.inv_per_line_adv_print == False and inv_ids.inv_whole_order_at_once == False and inv_ids.inv_whole_order_afterwards == False and \
				   inv_ids.inv_per_line_after_print == False and inv_ids.inv_per_line_adv_online == False and inv_ids.inv_per_line_after_online == False:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_order = []
							group_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_order.append(line.order_id.id)
									set_group_order = list(set(group_order))
									# looping over the orders to generate invoices
							for sale_id in set_group_order:
								group_order_lines = []
								for lines in OrderLines:
									order_line_ids = self.env['sale.order.line'].search(['&',('id','=',lines.id),'&',('order_id','=',sale_id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
									if order_line_ids:
										for line_ids in order_line_ids:
											group_order_lines.append(line_ids)
								set_group_order_line_id = list(set(group_order_lines))
								if set_group_order_line_id:
									# Condition is used to truncate the null value
									self.make_invoices_job_queue(inv_date, post_date, set_group_order_line_id)


				# Group by Invoice per orderline in advance print
				elif inv_ids.inv_per_line_adv_print == True and inv_ids.group_by_order == False	and inv_ids.group_by_advertiser == False and inv_ids.group_by_edition == False and \
					 inv_ids.inv_per_line_after_online == False and inv_ids.inv_whole_order_at_once == False and inv_ids.inv_per_line_after_print == False and \
					 inv_ids.inv_per_line_adv_online == False and inv_ids.default_property == False and inv_ids.inv_whole_order_afterwards == False:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_order = []
							group_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_order.append(line.order_id.id)
									set_group_order = list(set(group_order))
							# looping over the orders to generate invoices
							for sale_id in set_group_order:
								group_order_lines = []
								for lines in OrderLines:
									order_line_ids = self.env['sale.order.line'].search(['&',('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
									if order_line_ids:
										for line_ids in order_line_ids:
											if not line_ids.issue_date:
												if self.invoice_date:
													if line_ids.from_date:
														if self.invoice_date > line_ids.from_date:
															group_order_lines.append(line_ids)
												else:
													if line_ids.from_date:
														if self._context['invoice_date'] > line_ids.from_date:
															group_order_lines.append(line_ids)
											else:
												if self.invoice_date:
													if self.invoice_date > line_ids.order_id.invoicing_date:
														group_order_lines.append(line_ids)
												else:
													if self._context['invoice_date'] > line_ids.order_id.invoicing_date:
														group_order_lines.append(line_ids)
								set_group_order_line_id = list(set(group_order_lines))
								if set_group_order_line_id:
									# Condition is used to truncate the null value
									self.make_invoices_job_queue(inv_date, post_date, set_group_order_line_id)

				# Invoice per OrderLine in advance print + Group by order
				elif inv_ids.inv_per_line_adv_print == True and inv_ids.group_by_order == True and inv_ids.group_by_advertiser == False and inv_ids.group_by_edition == False and \
					 inv_ids.inv_per_line_after_online == False and inv_ids.inv_whole_order_at_once == False and inv_ids.inv_per_line_after_print == False and \
					 inv_ids.inv_per_line_adv_online == False and inv_ids.default_property == False and inv_ids.inv_whole_order_afterwards == False:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_order = []
							group_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_order.append(line.order_id.id)
									set_group_order = list(set(group_order))
							# looping over the orders to generate invoices
							for sale_id in set_group_order:
								group_order_lines = []
								for lines in OrderLines:
									order_line_ids = self.env['sale.order.line'].search(['&',('id','=',lines.id),'&',('order_id','=',sale_id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
									if order_line_ids:
										for line_ids in order_line_ids:
											if not line_ids.issue_date:
												if self.invoice_date:
													if line_ids.from_date:
														if self.invoice_date > line_ids.from_date:
															group_order_lines.append(line_ids)
												else:
													if line_ids.from_date:
														if self._context['invoice_date'] > line_ids.from_date:
															group_order_lines.append(line_ids)
											else:
												if self.invoice_date:
													if self.invoice_date > line_ids.order_id.invoicing_date:
														group_order_lines.append(line_ids)
												else:
													if self._context['invoice_date'] > line_ids.order_id.invoicing_date:
														group_order_lines.append(line_ids)
								set_group_order_line_id = list(set(group_order_lines))
								if set_group_order_line_id:
									# Condition is used to truncate the null value
									self.make_invoices_job_queue(inv_date, post_date, set_group_order_line_id)

				# Group by Invoice per OrderLine afterwards online
				elif inv_ids.inv_per_line_after_online == True and inv_ids.group_by_order == False and inv_ids.group_by_advertiser == False and inv_ids.group_by_edition == False and \
					 inv_ids.inv_per_line_adv_print == False and inv_ids.inv_whole_order_at_once == False and inv_ids.inv_per_line_after_print == False and inv_ids.inv_per_line_adv_online == False and inv_ids.default_property == False and inv_ids.inv_whole_order_afterwards == False:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_order = []
							group_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_order.append(line.order_id.id)
									set_group_order = list(set(group_order))
							# looping over the orders to generate invoices
							for sale_id in set_group_order:
								group_order_lines = []
								for lines in OrderLines:
									order_line_ids = self.env['sale.order.line'].search(['&',('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
									if order_line_ids:
										for line_ids in order_line_ids:
											if not line_ids.issue_date:
												if self.invoice_date:
													if line_ids.from_date:
														if self.invoice_date > line_ids.from_date:
															group_order_lines.append(line_ids)
												else:
													if line_ids.from_date:
														if self._context['invoice_date'] > line_ids.from_date:
															group_order_lines.append(line_ids)
											else:
												if self.invoice_date:
													if self.invoice_date > line_ids.issue_date:
														group_order_lines.append(line_ids)
												else:
													if self._context['invoice_date'] > line_ids.issue_date:
														group_order_lines.append(line_ids)

								set_group_order_line_id = list(set(group_order_lines))
								if set_group_order_line_id:
									# Condition is used to truncate the null value
									self.make_invoices_job_queue(inv_date, post_date, set_group_order_line_id)

				# Group by Invoice per OrderLine afterwards online + Group by order
				elif inv_ids.inv_per_line_after_online == True and inv_ids.group_by_order == True and inv_ids.group_by_advertiser == False and inv_ids.group_by_edition == False and \
					 inv_ids.inv_whole_order_afterwards == False and inv_ids.inv_per_line_adv_print == False and inv_ids.inv_per_line_after_print == False and \
					 inv_ids.inv_per_line_adv_online == False and inv_ids.default_property == False and inv_ids.inv_whole_order_at_once == False:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_order = []
							group_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_order.append(line.order_id.id)
									set_group_order = list(set(group_order))
									# looping over the orders to generate invoices
							for sale_id in set_group_order:
								group_order_lines = []
								for lines in OrderLines:
									order_line_ids = self.env['sale.order.line'].search(['&',('id','=',lines.id),'&',('order_id','=',sale_id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
									if order_line_ids:
										for line_ids in order_line_ids:
											if not line_ids.issue_date:
												if self.invoice_date:
													if line_ids.from_date:
														if self.invoice_date > line_ids.from_date:
															group_order_lines.append(line_ids)
												else:
													if line_ids.from_date:
														if self._context['invoice_date'] > line_ids.from_date:
															group_order_lines.append(line_ids)
											else:
												if self.invoice_date:
													if self.invoice_date > line_ids.issue_date:
														group_order_lines.append(line_ids)
												else:
													if self._context['invoice_date'] > line_ids.issue_date:
														group_order_lines.append(line_ids)
								set_group_order_line_id = list(set(group_order_lines))
								if set_group_order_line_id:
									# Condition is used to truncate the null value
									self.make_invoices_job_queue(inv_date, post_date, set_group_order_line_id)

				

				# Group by Invoice whole order at once
				elif inv_ids.inv_whole_order_at_once == True and inv_ids.group_by_order == False and inv_ids.group_by_advertiser == False and inv_ids.group_by_edition == False and \
					 inv_ids.inv_per_line_adv_print == False and inv_ids.inv_per_line_after_online == False and inv_ids.inv_per_line_after_print == False and inv_ids.inv_per_line_adv_online == False and inv_ids.default_property == False and inv_ids.inv_whole_order_afterwards == False:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_order = []
							group_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_order.append(line.order_id.id)
									set_group_order = list(set(group_order))
									# looping over the orders to generate invoices
							for sale_id in set_group_order:
								group_order_lines = []
								for lines in OrderLines:
									order_line_ids = self.env['sale.order.line'].search(['&',('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
									if order_line_ids:
										for line_ids in order_line_ids:
											if line_ids.order_id.invoicing_date:
												if self.invoice_date:
													if self.invoice_date > line_ids.order_id.invoicing_date:
														group_order_lines.append(line_ids)
												else:
													if self._context['invoice_date'] > line_ids.order_id.invoicing_date:
														group_order_lines.append(line_ids)

							set_group_order_line_id = list(set(group_order_lines))
							if set_group_order_line_id:
								# Condition is used to truncate the null value
								self.make_invoices_job_queue(inv_date, post_date, set_group_order_line_id)

				# Group by Invoice whole order at once + Group by order
				elif inv_ids.inv_whole_order_at_once == True and inv_ids.group_by_order == True and inv_ids.group_by_advertiser == False and inv_ids.group_by_edition == False and \
					 inv_ids.inv_per_line_after_online == False and inv_ids.inv_per_line_adv_print == False and inv_ids.inv_per_line_after_print == False and \
					 inv_ids.inv_per_line_adv_online == False and inv_ids.default_property == False and inv_ids.inv_whole_order_afterwards == False:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_order = []
							group_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_order.append(line.order_id.id)
									set_group_order = list(set(group_order))
									# looping over the orders to generate invoices
							for sale_id in set_group_order:
								group_order_lines = []
								for lines in OrderLines:
									order_line_ids = self.env['sale.order.line'].search(['&',('id','=',lines.id),'&',('order_id','=',sale_id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
									if order_line_ids:
										for line_ids in order_line_ids:
											if line_ids.order_id.invoicing_date:
												if self.invoice_date:
													if self.invoice_date > line_ids.order_id.invoicing_date:
														group_order_lines.append(line_ids)
												else:
													if self._context['invoice_date'] > line_ids.order_id.invoicing_date:
														group_order_lines.append(line_ids)
								set_group_order_line_id = list(set(group_order_lines))
								if set_group_order_line_id:
									# Condition is used to truncate the null value
									self.make_invoices_job_queue(inv_date, post_date, set_group_order_line_id)


				# Group by Invoice whole order afterwards
				elif inv_ids.inv_whole_order_afterwards == True and inv_ids.group_by_order == False and inv_ids.group_by_advertiser == False and inv_ids.group_by_edition == False and \
					 inv_ids.inv_per_line_adv_print == False and inv_ids.inv_per_line_after_online == False and inv_ids.inv_per_line_after_print == False and inv_ids.inv_per_line_adv_online == False and inv_ids.default_property == False and inv_ids.inv_whole_order_at_once == False:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_order = []
							group_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_order.append(line.order_id.id)
									set_group_order = list(set(group_order))
									# looping over the orders to generate invoices
							for sale_id in set_group_order:
								group_order_lines = []
								for lines in OrderLines:
									order_line_ids = self.env['sale.order.line'].search(['&',('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
									if order_line_ids:
										for line_ids in order_line_ids:
											if not line_ids.issue_date:
												if self.invoice_date:
													if line_ids.from_date:
														if self.invoice_date > line_ids.from_date:
															group_order_lines.append(line_ids)
												else:
													if line_ids.from_date:
														if self._context['invoice_date'] > line_ids.from_date:
															group_order_lines.append(line_ids)
														
											else:
												if self.invoice_date:
													if self.invoice_date > line_ids.issue_date:
														group_order_lines.append(line_ids)
												else:
													if self._context['invoice_date'] > line_ids.issue_date:
														group_order_lines.append(line_ids)

								set_group_order_line_id = list(set(group_order_lines))
								if set_group_order_line_id:
									# Condition is used to truncate the null value
									self.make_invoices_job_queue(inv_date, post_date, set_group_order_line_id)

				# Group by Invoice whole order afterwards + Group by order
				elif inv_ids.inv_whole_order_afterwards == True and inv_ids.group_by_order == True and inv_ids.group_by_advertiser == False and inv_ids.group_by_edition == False and \
					 inv_ids.inv_per_line_after_online == False and inv_ids.inv_per_line_adv_print == False and inv_ids.inv_per_line_after_print == False and \
					 inv_ids.inv_per_line_adv_online == False and inv_ids.default_property == False and inv_ids.inv_whole_order_at_once == False:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_order = []
							group_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_order.append(line.order_id.id)
									set_group_order = list(set(group_order))
									# looping over the orders to generate invoices
							for sale_id in set_group_order:
								group_order_lines = []
								for lines in OrderLines:
									order_line_ids = self.env['sale.order.line'].search(['&',('id','=',lines.id),'&',('order_id','=',sale_id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
									if order_line_ids:
										for line_ids in order_line_ids:
											if not line_ids.issue_date:
												if self.invoice_date:
													if line_ids.from_date:
														if self.invoice_date > line_ids.from_date:
															group_order_lines.append(line_ids)
												else:
													if line_ids.from_date:
														if self._context['invoice_date'] > line_ids.from_date:
															group_order_lines.append(line_ids)
											else:
												if self.invoice_date:
													if self.invoice_date > line_ids.issue_date:
														group_order_lines.append(line_ids)
												else:
													if self._context['invoice_date'] > line_ids.issue_date:
														group_order_lines.append(line_ids)
								set_group_order_line_id = list(set(group_order_lines))
								if set_group_order_line_id:
									# Condition is used to truncate the null value
									self.make_invoices_job_queue(inv_date, post_date, set_group_order_line_id)


				# Group by Invoice per orderline afterwards print
				elif inv_ids.inv_per_line_after_print == True and inv_ids.group_by_order == False and inv_ids.group_by_advertiser == False and inv_ids.group_by_edition == False and \
					 inv_ids.inv_per_line_adv_online == False and inv_ids.inv_per_line_adv_print == False and inv_ids.inv_per_line_after_online == False and \
					 inv_ids.inv_whole_order_at_once == False and inv_ids.default_property == False and inv_ids.inv_whole_order_afterwards == False:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_order = []
							group_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_order.append(line.order_id.id)
									set_group_order = list(set(group_order))
							# looping over the orders to generate invoices
							for sale_id in set_group_order:
								group_order_lines = []
								for lines in OrderLines:
									order_line_ids = self.env['sale.order.line'].search(['&',('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
									if order_line_ids:
										for line_ids in order_line_ids:
											if not line_ids.issue_date:
												if self.invoice_date:
													if line_ids.from_date:
														if self.invoice_date > line_ids.from_date:
															group_order_lines.append(line_ids)
												else:
													if line_ids.from_date:
														if self._context['invoice_date'] > line_ids.from_date:
															group_order_lines.append(line_ids)
														
											else:
												if self.invoice_date:
													if self.invoice_date > line_ids.issue_date:
														group_order_lines.append(line_ids)
												else:
													if self._context['invoice_date'] > line_ids.issue_date:
														group_order_lines.append(line_ids)

								set_group_order_line_id = list(set(group_order_lines))
								if set_group_order_line_id:
									# Condition is used to truncate the null value
									self.make_invoices_job_queue(inv_date, post_date, set_group_order_line_id)

				# Group by Invoice per orderline afterwards print + Group by order
				elif inv_ids.inv_per_line_after_print == True and inv_ids.group_by_order == True and inv_ids.group_by_advertiser == False and inv_ids.group_by_edition == False and \
					 inv_ids.inv_per_line_after_online == False and inv_ids.inv_per_line_adv_print == False and inv_ids.inv_whole_order_afterwards == False and \
					 inv_ids.inv_per_line_adv_online == False and inv_ids.default_property == False and inv_ids.inv_whole_order_at_once == False:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_order = []
							group_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_order.append(line.order_id.id)
									set_group_order = list(set(group_order))
									# looping over the orders to generate invoices
							for sale_id in set_group_order:
								group_order_lines = []
								for lines in OrderLines:
									order_line_ids = self.env['sale.order.line'].search(['&',('id','=',lines.id),'&',('order_id','=',sale_id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
									if order_line_ids:
										for line_ids in order_line_ids:
											if not line_ids.issue_date:
												if self.invoice_date:
													if line_ids.from_date:
														if self.invoice_date > line_ids.from_date:
															group_order_lines.append(line_ids)
												else:
													if line_ids.from_date:
														if self._context['invoice_date'] > line_ids.from_date:
															group_order_lines.append(line_ids)
											else:
												if self.invoice_date:
													if self.invoice_date > line_ids.issue_date:
														group_order_lines.append(line_ids)
												else:
													if self._context['invoice_date'] > line_ids.issue_date:
														group_order_lines.append(line_ids)
								set_group_order_line_id = list(set(group_order_lines))
								if set_group_order_line_id:
									# Condition is used to truncate the null value
									self.make_invoices_job_queue(inv_date, post_date, set_group_order_line_id)

				# Group by Invoice per orderline in advance online
				elif inv_ids.inv_per_line_adv_online == True and inv_ids.group_by_order == False and inv_ids.group_by_advertiser == False and inv_ids.group_by_edition == False and \
					 inv_ids.inv_per_line_after_print == False and inv_ids.inv_per_line_adv_print == False and inv_ids.inv_per_line_after_online == False and \
					 inv_ids.inv_whole_order_at_once == False and inv_ids.default_property == False and inv_ids.inv_whole_order_afterwards == False:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_order = []
							group_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_order.append(line.order_id.id)
									set_group_order = list(set(group_order))
									# looping over the orders to generate invoices
							for sale_id in set_group_order:
								group_order_lines = []
								for lines in OrderLines:
									order_line_ids = self.env['sale.order.line'].search(['&',('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
									if order_line_ids:
										for line_ids in order_line_ids:
											if not line_ids.issue_date:
												if self.invoice_date:
													if self.invoice_date > line_ids.order_id.invoicing_date:
														group_order_lines.append(line_ids)
												else:
													if self._context['invoice_date'] > line_ids.order_id.invoicing_date:
														group_order_lines.append(line_ids)
											else:
												if self.invoice_date:
													if self.invoice_date > line_ids.issue_date:
														group_order_lines.append(line_ids)
												else:
													if self._context['invoice_date'] > line_ids.issue_date:
														group_order_lines.append(line_ids)
								set_group_order_line_id = list(set(group_order_lines))

								if set_group_order_line_id:
									# Condition is used to truncate the null value
									self.make_invoices_job_queue(inv_date, post_date, set_group_order_line_id)


				# Group by Invoice per orderline in advance online + Group by order
				elif inv_ids.inv_per_line_adv_online == True and inv_ids.group_by_order == True and inv_ids.group_by_advertiser == False and inv_ids.group_by_edition == False and \
					 inv_ids.inv_per_line_after_online == False and inv_ids.inv_per_line_adv_print == False and inv_ids.inv_per_line_after_print == False and \
					 inv_ids.inv_whole_order_afterwards == False and inv_ids.default_property == False and inv_ids.inv_whole_order_at_once == False:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_order = []
							group_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_order.append(line.order_id.id)
									set_group_order = list(set(group_order))
									# looping over the orders to generate invoices
							for sale_id in set_group_order:
								group_order_lines = []
								for lines in OrderLines:
									order_line_ids = self.env['sale.order.line'].search(['&',('id','=',lines.id),'&',('order_id','=',sale_id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
									if order_line_ids:
										for line_ids in order_line_ids:
											if not line_ids.issue_date:
												if self.invoice_date:
													if self.invoice_date > line_ids.order_id.invoicing_date:
														group_order_lines.append(line_ids)
												else:
													if self._context['invoice_date'] > line_ids.order_id.invoicing_date:
														group_order_lines.append(line_ids)
											else:
												if self.invoice_date:
													if self.invoice_date > line_ids.issue_date:
														group_order_lines.append(line_ids)
												else:
													if self._context['invoice_date'] > line_ids.issue_date:
														group_order_lines.append(line_ids)
								set_group_order_line_id = list(set(group_order_lines))
								if set_group_order_line_id:
									# Condition is used to truncate the null value
									self.make_invoices_job_queue(inv_date, post_date, set_group_order_line_id)

				#------------------- No need to change below 3------------
				elif inv_ids.default_property == True:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_default_order = []
							group_default_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_default_order.append(line)
									set_group_default_order = list(set(group_default_order))
							if set_group_default_order:
								# Condition is used to truncate the null value
								self.make_invoices_job_queue(inv_date, post_date, set_group_default_order)
				elif inv_ids.pay_in_terms == True:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_default_order = []
							group_default_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_default_order.append(line)
									set_group_default_order = list(set(group_default_order))
							if set_group_default_order:
								# Condition is used to truncate the null value
								self.make_invoices_job_queue(inv_date, post_date, set_group_default_order)
				elif inv_ids.inv_package_deal == True:
					# Loop over the customer to generate the invoice
					for cus_id in set_customer_ids:
						customer_id = self.env['res.partner'].search([('id','=',cus_id)])
						if customer_id:
							# Loop over the selected order lines
							set_group_order = []
							group_order = []
							for lines in OrderLines:
								# Filter the order lines based on the customer
								sale_order_line_id = self.env['sale.order.line'].search([('id','=',lines.id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
								if sale_order_line_id:
									# Fetching the order number
									for line in sale_order_line_id:
										group_order.append(line.order_id.id)
									set_group_order = list(set(group_order))
									# looping over the orders to generate invoices
							for sale_id in set_group_order:
								group_order_lines = []
								for lines in OrderLines:
									order_line_ids = self.env['sale.order.line'].search(['&',('id','=',lines.id),'&',('order_id','=',sale_id),'&',('order_partner_id','=',customer_id.id),'&',('invoicing_property_id','=',inv_ids.id),('invoice_status','!=','invoiced')])
									if order_line_ids:
										for line_ids in order_line_ids:
											group_order_lines.append(line_ids)
								set_group_order_line_id = list(set(group_order_lines))
								if set_group_order_line_id:
									# Condition is used to truncate the null value
									self.make_invoices_job_queue(inv_date, post_date, set_group_order_line_id)
				else:
					return "Lines dispatched."

