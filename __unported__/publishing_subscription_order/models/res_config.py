# -*- encoding: utf-8 -*-

from odoo import api, fields, exceptions, models, _

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    delivery_obligation_account_id = fields.Many2one('account.account', string="Delivery Obligation Account", domain=[('deprecated', '=', False)])
    subscription_revenue_account_id = fields.Many2one('account.account', string='Subscription Revenue Account', domain=[('deprecated', '=', False)])

    @api.onchange('company_id')
    def onchange_company_id(self):
        res = super(AccountConfigSettings, self).onchange_company_id()
        if self.company_id:
            # update subscription account
            ir_values = self.env['ir.values']
            delivery_account_id = ir_values.get_default('product.template', 'delivery_obligation_account_id', company_id = self.company_id.id)
            revenue_account_id = ir_values.get_default('product.template', 'subscription_revenue_account_id', company_id = self.company_id.id)
            self.delivery_obligation_account_id = delivery_account_id if delivery_account_id else False
            self.subscription_revenue_account_id = revenue_account_id if revenue_account_id else False
        return res

    
    def set_product_susbcription_account(self):
        """ Set the product susbcription accounts if they have changed """
        ir_values_obj = self.env['ir.values']
        ir_values_obj.sudo().set_default('product.template', "delivery_obligation_account_id", self.delivery_obligation_account_id.id if self.delivery_obligation_account_id else False, for_all_users=True, company_id=self.company_id.id)
        ir_values_obj.sudo().set_default('product.template', "subscription_revenue_account_id", self.subscription_revenue_account_id.id if self.subscription_revenue_account_id else False, for_all_users=True, company_id=self.company_id.id)
