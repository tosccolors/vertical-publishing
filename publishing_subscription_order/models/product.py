# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    subscription_product = fields.Boolean(string='Is subscription product?')
    delivery_obligation_account_id = fields.Many2one('account.account', string="Delivery Obligation Account", domain=[('deprecated', '=', False)])
    subscription_revenue_account_id = fields.Many2one('account.account', string='Subscription Revenue Account', domain=[('deprecated', '=', False)])
    number_of_issues = fields.Integer('No. Of Issues')
    subscr_number_of_days = fields.Integer('No. Of Days')

    @api.multi
    def _get_product_accounts(self):
        return {
            'income': self.delivery_obligation_account_id if self.subscription_product else self.property_account_income_id or self.categ_id.property_account_income_categ_id,
            'expense': self.property_account_expense_id or self.categ_id.property_account_expense_categ_id
        }


class ProductCategory(models.Model):
    _inherit = 'product.category'

    subscription_categ = fields.Boolean(string='Is subscription Category?')
