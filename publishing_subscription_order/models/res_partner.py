# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2015 Magnus
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, exceptions, models, _
from odoo.exceptions import ValidationError
from datetime import datetime

class Partner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'time.dependent.thread']

    is_subscription_customer = fields.Boolean('Subscription Customer', default=False)
    property_subscription_payment_term_id = fields.Many2one('account.payment.term', company_dependent=True, string='Subscription Payment Terms', help="This payment term will be used instead of the default one for subscription orders and subscription bills")
    subscription_customer_payment_mode_id = fields.Many2one('account.payment.mode', string='Subscription Customer Payment Mode',company_dependent=True,domain=[('payment_type', '=', 'inbound')],help="Select the default subscription payment mode for this customer.")
    subs_quotation_count = fields.Integer(compute='_compute_subs_quotation_count', string='# of Quotations')
    subs_sale_order_count = fields.Integer(compute='_compute_subs_sale_order_count', string='# of Sales Orders')
    subs_as_reader_count = fields.Integer(compute='_compute_subs_as_reader_count', string='# of Sales Orders as reader')
    department_id = fields.Many2one('hr.department', string='Department')

    def _compute_subs_quotation_count(self):
        sale_data = self.env['sale.order'].read_group(domain=[('partner_id', 'child_of', self.ids),('subscription','=',True),('state','not in',('sale','done','cancel'))],
                                                      fields=['partner_id'], groupby=['partner_id'])
        # read to keep the child/parent relation while aggregating the read_group result in the loop
        partner_child_ids = self.read(['child_ids'])
        mapped_data = dict([(m['partner_id'][0], m['partner_id_count']) for m in sale_data])
        for partner in self:
            # let's obtain the partner id and all its child ids from the read up there
            partner_ids = filter(lambda r: r['id'] == partner.id, partner_child_ids)[0]
            partner_ids = [partner_ids.get('id')] + partner_ids.get('child_ids')
            # then we can sum for all the partner's child
            partner.subs_quotation_count = sum(mapped_data.get(child, 0) for child in partner_ids)

    def _compute_subs_sale_order_count(self):
        sale_data = self.env['sale.order'].read_group(domain=[('partner_id', 'child_of', self.ids),('subscription','=',True),('state','in',('sale','done'))],
                                                      fields=['partner_id'], groupby=['partner_id'])
        # read to keep the child/parent relation while aggregating the read_group result in the loop
        partner_child_ids = self.read(['child_ids'])
        mapped_data = dict([(m['partner_id'][0], m['partner_id_count']) for m in sale_data])
        for partner in self:
            # let's obtain the partner id and all its child ids from the read up there
            partner_ids = filter(lambda r: r['id'] == partner.id, partner_child_ids)[0]
            partner_ids = [partner_ids.get('id')] + partner_ids.get('child_ids')
            # then we can sum for all the partner's child
            partner.subs_sale_order_count = sum(mapped_data.get(child, 0) for child in partner_ids)

    def _compute_subs_as_reader_count(self):
        subscription_orders = self.env['sale.order'].search([('partner_shipping_id', '=', self.ids),
                                                             ('subscription','=',True),
                                                             ('state','in',('sale','done'))])
        for partner in self:
            partner.subs_as_reader_count = len(subscription_orders)

    @api.multi
    def _compute_total_sales_order(self):
        for partner in self:
            partner.total_sales_order = partner.sale_order_count + partner.adv_sale_order_count + partner.subs_sale_order_count

    # Adding ('subscription', '=', False) in filter criteria to filter out subscription records from regular quotations smart button
    @api.multi
    def _compute_quotation_count(self):
        for partner in self:
            operator = 'child_of' if partner.is_company else '='
            partner.quotation_count = self.env['sale.order'].search_count([('partner_id', operator, partner.id), ('state','not in',('sale','done','cancel')), ('advertising', '=', False), ('subscription', '=', False)])

    # Adding ('subscription', '=', False) in filter criteria to filter out subscription records from regular sales orders smart button
    @api.multi
    def _compute_sale_order_count(self):
        for partner in self:
            operator = 'child_of' if partner.is_company else '='
            partner.sale_order_count = self.env['sale.order'].search_count([('partner_id', operator, partner.id), ('state','in',('sale','done')), ('advertising', '=', False), ('subscription', '=', False)])

    @api.model
    def _commercial_fields(self):
        return super(Partner, self)._commercial_fields() + ['property_subscription_payment_term_id','subscription_customer_payment_mode_id','is_subscription_customer']


    @api.multi
    @api.onchange('is_subscription_customer')
    def subscription_customer_payment(self):
        if self.is_subscription_customer and not self.subscription_customer_payment_mode_id:
            payment_mode = self.env['account.payment.mode'].with_context({'lang':'en_US'}).search([('name','=','SEPA DD')], limit=1)
            self.subscription_customer_payment_mode_id = payment_mode.id if payment_mode else False
        if self.is_subscription_customer and not self.property_subscription_payment_term_id:
            self.property_subscription_payment_term_id = self.env.ref('bdumedia.account_payment_term_14', False)
