# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    subscription_product = fields.Boolean(string='Is subscription')
    delivery_obligation_account_id = fields.Many2one('account.account', string="Delivery Obligation Account", domain=[('deprecated', '=', False)])
    subscription_revenue_account_id = fields.Many2one('account.account', string='Subscription Revenue Account', domain=[('deprecated', '=', False)])
    number_of_issues = fields.Integer('No. Of Issues')
    subscr_number_of_days = fields.Integer('No. Of Days')
    digital_subscription = fields.Boolean(string='Digital only')
    weekday_ids = fields.Many2many('week.days', 'weekday_template_rel', 'template_id', 'weekday_id', 'Weekdays')
    can_renew = fields.Boolean('Can Renewed?', default=False)
    renew_product_id = fields.Many2one('product.product','Renewal Product')

    @api.multi
    def _get_product_accounts(self):
        return {
            'income': self.delivery_obligation_account_id if self.subscription_product else self.property_account_income_id or self.categ_id.property_account_income_categ_id,
            'expense': self.property_account_expense_id or self.categ_id.property_account_expense_categ_id
        }

    @api.onchange('subscription_product')
    def onchange_subscription_product(self):
        if self.subscription_product:
            weekdays = self.env['week.days'].search([],order='id desc')
            self.weekday_ids = [(6,0,weekdays.ids)]
        else:
            self.weekday_ids = [(6, 0, [])]

    @api.model
    def create(self, values):
        res = super(ProductTemplate, self).create(values)
        if res.subscription_product and values['can_renew'] and not values['renew_product_id']:
            product = self.env['product.product'].search([('product_tmpl_id', '=', res.id)], limit=1)
            res.write({'renew_product_id':product.ids[0]})
        return res

    @api.multi
    def write(self, values):
        res = super(ProductTemplate, self).write(values)
        for tmpl in self:
            if tmpl.subscription_product and tmpl.can_renew and not tmpl.renew_product_id:
                product = self.env['product.product'].search([('product_tmpl_id', '=', tmpl.id)], limit=1)
                if product:
                    tmpl.write({'renew_product_id': product.ids[0]})
        return res

    @api.onchange('can_renew','renew_product_id')
    def onchange_renewal(self):
        if self.subscription_product and self._origin.id:
            if self.can_renew and not self.renew_product_id:
                product = self.env['product.product'].search([('product_tmpl_id', '=', self._origin.id)], limit=1)
                self.renew_product_id = product and product[0] or False
            elif not self.can_renew:
                self.renew_product_id = False

class ProductCategory(models.Model):
    _inherit = 'product.category'

    subscription_categ = fields.Boolean(string='Is subscription Category?')
