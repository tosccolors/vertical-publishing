# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2016 Magnus (<http://www.magnus.nl>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from odoo import api, fields, models, _
from datetime import date

class Lead(models.Model):
    _inherit = ["crm.lead"]

    subs_quotations_count = fields.Integer("# of Subscription Quotations", compute='_compute_subs_quotations_count')
    subs_sale_amount_total= fields.Monetary(compute='_compute_sale_amount_total', string="Sum of Subs. Orders", currency_field='company_currency')

    @api.multi
    def _compute_subs_quotations_count(self):
        for lead in self:
            lead.subs_quotations_count = self.env['sale.order'].search_count([('opportunity_id', '=', lead.id), ('state','not in',('sale','done','cancel')), ('subscription', '=', True)])

    # Adding ('subscription', '=', False) in filter criteria to filter subscription records in regular quotations smart button
    @api.multi
    def _compute_quotations_count(self):
        for lead in self:
            lead.quotations_count = self.env['sale.order'].search_count([('opportunity_id', '=', lead.id), ('state','not in',['sale','done','cancel']), ('advertising', '=', False), ('subscription', '=', False)])

    @api.depends('order_ids')
    def _compute_sale_amount_total(self):
        for lead in self:
            total = adv_total = subs_total = 0.0
            nbr = 0
            company_currency = lead.company_currency or self.env.user.company_id.currency_id
            for order in lead.order_ids:
                if order.state not in ('sale', 'done', 'cancel'):
                    nbr += 1
                if order.state in ('sale', 'done'):
                    if not order.advertising and not order.subscription:
                        total += order.currency_id.compute(order.amount_total, company_currency)
                    if order.advertising:
                        adv_total += order.currency_id.compute(order.amount_untaxed, company_currency)
                    if order.subscription:
                        subs_total += order.currency_id.compute(order.amount_untaxed, company_currency)
            lead.sale_amount_total, lead.adv_sale_amount_total, lead.subs_sale_amount_total, lead.sale_number = total, adv_total, subs_total, nbr

    @api.model
    def retrieve_sales_dashboard(self):
        result = super(Lead, self).retrieve_sales_dashboard()
        result['subs_quotes'] = {'overdue': 0}
        quote_domain = [
            ('state', 'not in', ['sale', 'done']),
            ('user_id', '=', self.env.uid),
            ('validity_date', '<', fields.Date.to_string(date.today())),
            ('subscription', '=', True)
        ]
        quote_data = self.env['sale.order'].search(quote_domain)
        for quote in quote_data:
            if quote.subscription == True:
                result['subs_quotes']['overdue'] += 1
        #Deducting subscription quotes count from regular quotes count
        result['reg_quotes']['overdue'] = result['reg_quotes']['overdue'] - result['subs_quotes']['overdue']

        return result