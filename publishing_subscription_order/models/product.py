# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    subscription_product = fields.Boolean(string='Is subscription product?')
#    delivery_obligation_account_id = fields.Many2one('account.account', string="Delivery Obligation Account", domain=[('deprecated', '=', False)])
    subscription_revenue_account_id = fields.Many2one('account.account', string='Subscription Revenue Account', domain=[('deprecated', '=', False)])
    number_of_issues = fields.Integer('No. Of Issues')
    subscr_number_of_days = fields.Integer('No. Of Days')
    digital_subscription = fields.Boolean(string='Is digital subscription?')
    weekday_ids = fields.Many2many('week.days', 'weekday_template_rel', 'template_id', 'weekday_id', 'Weekdays')
    can_renew = fields.Boolean('Can Renewed?', default=False)
    renew_product_id = fields.Many2one('product.template','Renewal Product')

    '''@api.multi
    def _get_product_accounts(self):
        return {
            'income': self.delivery_obligation_account_id if self.subscription_product else self.property_account_income_id or self.categ_id.property_account_income_categ_id,
            'expense': self.property_account_expense_id or self.categ_id.property_account_expense_categ_id
        }'''

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
            res.write({'renew_product_id':res.id})
        return res

    @api.onchange('can_renew','renew_product_id')
    def onchange_renewal(self):
        if self.subscription_product and self._origin.id:
            if self.can_renew and not self.renew_product_id:
                self.renew_product_id = self._origin.id or False
            elif not self.can_renew:
                self.renew_product_id = False

class ProductCategory(models.Model):
    _inherit = 'product.category'

    subscription_categ = fields.Boolean(string='Is subscription Category?')
