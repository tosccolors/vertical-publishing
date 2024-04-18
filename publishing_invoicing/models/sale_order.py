
from odoo import api, fields, models, _
from datetime import date, timedelta, datetime

class SaleOrder(models.Model):
	_inherit = 'sale.order'

	invoicing_property_id = fields.Many2one('invoicing.property', string="Invoicing Property", required=True)
	invoicing_date = fields.Date(string="Invoicing Date")
	inv_date_bool = fields.Boolean(string="Set attribute to Invoicing date field", compute="_calculate_helper_booleans", store=True)
	inv_package_bool = fields.Boolean(string="Set attribute to Package")
	terms_condition = fields.Text(string="Description of terms")
	terms_cond_bool = fields.Boolean(string="Set attribute to Terms & condition field", compute="_calculate_helper_booleans", store=True)
	package = fields.Boolean(string='Package', index=True, copy=False, compute="_calculate_helper_booleans", store=True)


	@api.onchange('published_customer', 'advertising_agency')
	def onchange_customer_publishing_invoicing(self):
		for line in self:
			if line.advertising_agency:
				if line.advertising_agency.invoicing_property_id:
					line.invoicing_property_id = line.advertising_agency.invoicing_property_id.id
			else:
				if line.published_customer.invoicing_property_id:
					line.invoicing_property_id = line.published_customer.invoicing_property_id.id

	@api.depends('invoicing_property_id')
	def _calculate_helper_booleans(self):
		if self.invoicing_property_id.inv_package_deal and self.invoicing_property_id.pay_in_terms:
			self.update({'inv_date_bool': False})
			self.update({'package': True})
			self.update({'terms_cond_bool': True})
		elif self.invoicing_property_id.pay_in_terms and not self.invoicing_property_id.inv_package_deal:
			self.update({'terms_cond_bool': True})
			self.update({'inv_date_bool': False})
			self.update({'package': False})
		elif self.invoicing_property_id.inv_package_deal and not self.invoicing_property_id.pay_in_terms:
			self.update({'inv_date_bool': True})
			self.update({'package': True})
			#self.inv_package_bool = True
			self.update({'terms_cond_bool': False})
		elif self.invoicing_property_id.inv_per_line_adv_print or self.invoicing_property_id.inv_per_line_adv_online or self.invoicing_property_id.inv_whole_order_at_once:
			self.update({'inv_date_bool': True})
		else:
			self.update({'inv_date_bool': False})
			self.update({'inv_date_bool': False})
			self.update({'package': False})
			self.update({'terms_cond_bool': False})
		return True

class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	invoicing_property_id = fields.Many2one('invoicing.property', related='order_id.invoicing_property_id', string="Invoicing Property")
	cutoff_date = fields.Date(string="Cutoff Date", compute='_calculate_cutoff_date', store=True, readonly=True)

	@api.depends('order_id.invoicing_property_id', 'order_id.invoicing_date')
	def _calculate_cutoff_date(self):
		""""Calculates the date after which an order line can be invoiced"""
		for line in self:
			line_print = not(line.product_id.categ_id.digital)
			# All order lines after a selected date
			if line.invoicing_property_id.inv_whole_order_at_once:
				cutoff_date = line.order_id.invoicing_date
			# All order lines after placement
			elif line.invoicing_property_id.inv_whole_order_afterwards:
				if line_print:
					cutoff_date = line.issue_date
				else:
					cutoff_date = line.from_date
			# All order lines end date
			elif line.invoicing_property_id.inv_whole_order_enddate:
				if line_print:
					cutoff_date = line.issue_date
				else:
					cutoff_date = line.to_date
			# Print after selected date, online after placement
			elif line.invoicing_property_id.inv_per_line_adv_print:
				if line_print:
					cutoff_date = line.order_id.invoicing_date
				else:
					cutoff_date = line.from_date
			# Online after selected date, print after placement
			elif line.invoicing_property_id.inv_per_line_adv_online:
				if not line_print:
					cutoff_date = line.order_id.invoicing_date
				else:
					cutoff_date = line.issue_date
			# Package deal but not pay in terms
			# elif line.invoicing_property_id.inv_package_deal and not line.invoicing_property_id.pay_in_terms:
			# 	cutoff_date = line.issue_date
			# In case of package deal, pay in terms etc.
			else:
				cutoff_date = '1900-01-01'
			line.update({'cutoff_date': cutoff_date})
		return True


	# deep: deprecated
	# def write(self, vals):
	# 	user = self.env['res.users'].browse(self.env.uid)
	# 	ctx = self.env.context.copy()
	# 	if self.env.user.has_group('publishing_invoicing.advertising_sale_superuser'):
	# 		ctx.update({'allow_user':True})
	# 	return super(SaleOrderLine, self.with_context(ctx)).write(vals)

