
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

	@api.multi
	@api.onchange('invoicing_property_id')
	def onchange_invoicing_property(self):
		for line in self:
			if line.invoicing_property_id.inv_package_deal:
				if line.invoicing_property_id.pay_in_terms:
					line.inv_date_bool = line.invoicing_date = False
					line.package = line.inv_package_bool = line.terms_cond_bool = True
				else:
					line.inv_date_bool = line.package = line.inv_package_bool = True
					line.terms_cond_bool = line.terms_condition = False
			elif not line.invoicing_property_id.inv_package_deal and line.invoicing_property_id.pay_in_terms:
				line.inv_date_bool = line.package = line.inv_package_bool = line.package_description = line.invoicing_date = False
				line.terms_cond_bool = True
			else:
				if line.invoicing_property_id.inv_per_line_adv_print or line.invoicing_property_id.inv_per_line_adv_online or line.invoicing_property_id.inv_whole_order_at_once:
					line.inv_date_bool = True
					line.package = line.inv_package_bool = line.terms_cond_bool = line.terms_condition = line.package_description = False
				else:
					line.inv_date_bool = line.invoicing_date = line.package = line.inv_package_bool = False
					line.terms_cond_bool = line.terms_condition = False


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


