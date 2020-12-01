
from odoo import api, fields, models, _

class SaleOrder(models.Model):
	_inherit = 'sale.order'

	invoicing_property_id = fields.Many2one('invoicing.property',string="Invoicing Property",required=True,copy=True)
	invoicing_date = fields.Date(string="Invoicing Date",copy=True)
	inv_date_bool = fields.Boolean(string="Set attribute to Invoicing date field",copy=True)
	terms_condition = fields.Text(string="Terms and condition",copy=True)
	terms_cond_bool = fields.Boolean(string="Set attribute to Terms & condition field",copy=True)
	package = fields.Boolean(string='Package', index=True, copy=True)
	package_description = fields.Char(string='Package Description', copy=True)

	@api.multi
	@api.onchange('published_customer','advertising_agency')
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
	def onchange_partner_package(self):
		for line in self:
			if line.invoicing_property_id.inv_package_deal == True:
				line.package = True
			else:
				line.package = False

	@api.multi
	@api.onchange('invoicing_property_id')
	def onchange_partner_invoicing_date(self):
		for line in self:
			if line.invoicing_property_id.inv_per_line_adv_print == True or line.invoicing_property_id.inv_per_line_adv_online == True or line.invoicing_property_id.inv_whole_order_at_once == True:
				line.inv_date_bool = True
			else:
				line.inv_date_bool = False
				line.invoicing_date = False

	@api.multi
	@api.onchange('invoicing_property_id')
	def onchange_partner_pay_terms(self):
		for line in self:
			if line.invoicing_property_id.pay_in_terms == True:
				line.terms_cond_bool = True
			else:
				line.terms_cond_bool = False
				line.terms_condition = False

class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	invoicing_property_id = fields.Many2one('invoicing.property',related='order_id.invoicing_property_id',string="Invoicing Property")

	@api.multi
	def write(self, vals):
		result = super(SaleOrderLine, self).write(vals)
		user = self.env['res.users'].browse(self.env.uid)
		for line in self.filtered(lambda s: s.state in ['sale'] and s.advertising):
			if 'pubble_sent' in vals:
				continue
			is_allowed = user.has_group('account.group_account_invoice') or user.has_group('advertising_sale_superuser') or 'allow_user' in self.env.context
			if line.invoice_status == 'invoiced' and not (vals.get('product_uom_qty') == 0 and line.qty_invoiced == 0) \
												 and not is_allowed \
												 and not user.id == 1:

				raise UserError(_('You cannot change an order line after it has been fully invoiced.'))
			if not line.multi_line and ('product_id' in vals or 'adv_issue' in vals or 'product_uom_qty' in vals):
				if line.deadline_check():
					line.page_qty_check_update()
		return result

