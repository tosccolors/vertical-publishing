# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SaleOrderTypology(models.Model):
    _inherit = "sale.order.type"

    act_window_id = fields.Many2one("ir.actions.act_window", string="Window Action",
                                help="Set 'Window Action' which will be used to determined to open corresponding SaleOrder view in Lead > New Quotation.")


class Lead2QuoteSOT(models.TransientModel):
    """
    This wizard will allow to choose order type (as in SOT)
    """
    _name = "lead.to.quote.sot"
    _description = "Choose sale order type (SOT)"

    order_type_id = fields.Many2one("sale.order.type", string="Sale Order Type", required=True)

    def action_proceed(self):
        "Open SaleOrder (Quotation) action"

        actWin = self.order_type_id.act_window_id or False

        if not actWin:
            raise UserError(_("Please configure 'Window Action' to proceed. Under Sales > Configuration > Sale Order Type."))

        action = actWin.read()[0]
        originalCtx = self._context

        try:
            formView = False
            for vi in action.get('views', []):
                v, k = vi[0], vi[1]
                if k == 'form':
                    formView = v

            # Combine both Context:
            ctx = eval(action.get('context', '{}'))
            ctx.update(originalCtx)

            # Force update:
            action['views'] = [(formView,'form')]
            action['context'] = ctx

        except:
            pass

        return action
