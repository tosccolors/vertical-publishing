# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    subscription_product = fields.Boolean(string='Is subscription product?')
    delivery_obligation_account = fields.Many2one('account.account', string="Delivery Obligation Account")
    subscription_revenue_account = fields.Many2one('account.account', string='Subscription Revenue Acoount')
    subscription_length = fields.Integer('Subscription Length')

    @api.multi
    def _get_product_accounts(self):
        return {
            'income': self.delivery_obligation_account if self.subscription_product else self.property_account_income_id or self.categ_id.property_account_income_categ_id,
            'expense': self.property_account_expense_id or self.categ_id.property_account_expense_categ_id
        }