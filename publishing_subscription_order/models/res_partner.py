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

    def _compute_subs_quotation_count(self):
        sale_data = self.env['sale.order'].read_group(domain=[('partner_id', 'child_of', self.ids),('subscription','=',True),('state','not in',('sale','done'))],
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

    @api.model
    def _commercial_fields(self):
        return super(Partner, self)._commercial_fields() + ['property_subscription_payment_term_id','subscription_customer_payment_mode_id','is_subscription_customer']


    @api.multi
    @api.onchange('is_subscription_customer')
    def subscription_customer_payment(self):
        if self.is_subscription_customer and not self.subscription_customer_payment_mode_id:
            self.subscription_customer_payment_mode_id = self.env.ref('publishing_subscription_order.payment_mode_inbound_subscriptiondd1', False)
