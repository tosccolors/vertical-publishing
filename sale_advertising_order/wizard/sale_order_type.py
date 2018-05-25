# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SaleOrderType(models.TransientModel):
    """
    This wizard will allow to choose order type(Regular Sale Order/Advertising Sale Order)
    """
    _name = "sale.order.type"
    _description = "Select sale order type"

    order_type = fields.Selection([('reg_order', 'Regular Order'), ('adv_order', 'Advertising Order')], string="Order Type")

    @api.multi
    def action_form_view(self):
        if not self.order_type:
            raise UserError(_("Please select order type."))
        context = self._context.copy()
        context['default_opportunity_id'] = context.get('active_id')
        form_view_id = False
        if self.order_type == 'reg_order':
            form_view_id = self.env.ref('sale.view_order_form').id
            context['default_advertising'] = False
        elif self.order_type == 'adv_order':
            form_view_id = self.env.ref('sale_advertising_order.view_order_form_advertising').id
            context['default_advertising'] = True

        return {
            'name':'Quotation',
            'view_type':'form',
            'res_model':'sale.order',
            'views':[(form_view_id,'form')],
            'type':'ir.actions.act_window',
            'target':'current',
            'context':context,
        }