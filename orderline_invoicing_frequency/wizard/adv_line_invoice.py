# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, datetime

class AdOrderLineMakeInvoice(models.TransientModel):
    _inherit = "ad.order.line.make.invoice"
    _description = "Advertising Order Line Make_invoice"

    @api.multi
    def make_invoices_from_lines(self):
        """
             To make invoices.
             @return: A dictionary which exists of fields with values.
        """
        context = self.env.context.copy()
        if not context.get('active_ids', []):
            raise UserError(_('No Ad Order lines are selected for invoicing:\n'))
        else: active_order_line_ids = context.get('active_ids', [])

        OrderLine = self.env['sale.order.line']
        order_line_ids = []
        customer = []
        for line in OrderLine.browse(active_order_line_ids):
            frequency = line.order_id.partner_id.invoice_frequency
            inv_date = line.order_id.partner_id.last_invoice_sent_date
            if (not inv_date) or (inv_date and not frequency):
                order_line_ids.append(line.id)
            elif inv_date and frequency:
                cur_date = date.today()
                inv_date = datetime.strptime(inv_date, "%Y-%m-%d").date()
                days = (cur_date - inv_date).days
                if frequency == 'weekly':
                    if days >= 7 or line.order_id.partner_id.id in customer:
                        customer.append(line.order_id.partner_id.id)
                        order_line_ids.append(line.id)
                elif frequency == 'monthly':
                    if days >= 30 or line.order_id.partner_id.id in customer:
                        customer.append(line.order_id.partner_id.id)
                        order_line_ids.append(line.id)
        context.update({'active_ids':order_line_ids}),context.update({'active_id':order_line_ids[0]}) if order_line_ids else context
        if not order_line_ids:
            raise UserError(_('No Ad Order lines are comming under this criteria.'))
        return super(AdOrderLineMakeInvoice, self.with_context(context)).make_invoices_from_lines()

