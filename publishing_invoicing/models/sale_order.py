
from odoo import api, fields, models, _

class SaleOrder(models.Model):
	_inherit = 'sale.order'

	invoicing_property_id = fields.Many2one('invoicing.property', string="Invoicing Property", required=True)
	invoicing_date = fields.Date(string="Invoicing Date")
	inv_date_bool = fields.Boolean(string="Set attribute to Invoicing date field")
	inv_package_bool = fields.Boolean(string="Set attribute to Package")
	terms_condition = fields.Text(string="Description of terms")
	terms_cond_bool = fields.Boolean(string="Set attribute to Terms & condition field")

	@api.multi
	@api.onchange('published_customer', 'advertising_agency')
	def onchange_customer_publishing_invoicing(self):
		for line in self:
			if line.advertising_agency:
				if line.advertising_agency.invoicing_property_id:
					line.invoicing_property_id = line.advertising_agency.invoicing_property_id.id
			else:
				if line.published_customer.invoicing_property_id:
					line.invoicing_property_id = line.published_customer.invoicing_property_id.id
	

					
	# @api.multi
	# @api.onchange('invoicing_property_id')
	# def onchange_partner_package(self):
	# 	for line in self:
	# 		if line.invoicing_property_id.inv_package_deal and line.invoicing_property_id.pay_in_terms == False:
	# 			line.package = True
	# 			line.inv_package_bool = True
	# 		else:
	# 			line.package = False
	# 			line.inv_package_bool = False

	@api.multi
	@api.onchange('invoicing_property_id')
	def onchange_partner_packagedeal_payinterms(self):
		for line in self:
			if line.invoicing_property_id.inv_package_deal == True and line.invoicing_property_id.pay_in_terms == True:
				line.inv_date_bool = False
				line.package = True
				line.inv_package_bool = True
				line.terms_cond_bool = True
			elif line.invoicing_property_id.inv_package_deal == False and line.invoicing_property_id.pay_in_terms == True:
				line.inv_date_bool = False
				line.package = False
				line.inv_package_bool = False
				line.terms_cond_bool = True
			elif line.invoicing_property_id.inv_package_deal == True and line.invoicing_property_id.pay_in_terms == False:
				line.inv_date_bool = True
				line.package = True
				line.inv_package_bool = True
				line.terms_cond_bool = False
			else:
				#line.inv_date_bool = False
				line.package = False
				line.inv_package_bool = False
				line.terms_cond_bool = False
				line.terms_condition = False

	@api.multi
	@api.onchange('invoicing_property_id')
	def onchange_partner_invoicing_date(self):
		for line in self:
			if line.invoicing_property_id.inv_per_line_adv_print == True or line.invoicing_property_id.inv_per_line_adv_online == True or line.invoicing_property_id.inv_whole_order_at_once == True or line.invoicing_property_id.inv_package_deal == True:
				line.inv_date_bool = True
			else:
				line.inv_date_bool = False
				line.invoicing_date = False

	# @api.multi
	# @api.onchange('invoicing_property_id')
	# def onchange_partner_pay_terms(self):
	# 	for line in self:
	# 		if line.invoicing_property_id.pay_in_terms == True:
	# 			line.terms_cond_bool = True
	# 		else:
	# 			line.terms_cond_bool = False
	# 			line.terms_condition = False


class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	invoicing_property_id = fields.Many2one('invoicing.property',related='order_id.invoicing_property_id',string="Invoicing Property")

	@api.multi
	def write(self, vals):
		user = self.env['res.users'].browse(self.env.uid)
		ctx = self.env.context.copy()
		if self.env.user.has_group('publishing_invoicing.advertising_sale_superuser'):
			ctx.update({'allow_user':True})
		return super(SaleOrderLine, self.with_context(ctx)).write(vals)


