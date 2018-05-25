# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SaleOrderType(models.TransientModel):
    """
    This wizard will allow to choose order type(Regular Sale Order/Advertising Sale Order/Subscription Sale Order)
    """
    _inherit = "sale.order.type"
    _description = "Select sale order type"

    order_type = fields.Selection(selection_add=[('sub_order', 'Subscription Order')], string="Order Type")

    @api.multi
    def action_form_view(self):
        result = super(SaleOrderType, self).action_form_view()
        if self.order_type == 'sub_order':
            result['views'] = [(self.env.ref('publishing_subscription_order.view_order_form_subscriptions').id, 'form')]
            result['context']['default_subscription'] = True
        return result