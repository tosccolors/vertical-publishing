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

    @api.model
    def _commercial_fields(self):
        return super(Partner, self)._commercial_fields() + ['property_subscription_payment_term_id','subscription_customer_payment_mode_id','is_subscription_customer']


    @api.multi
    @api.onchange('is_subscription_customer')
    def subscription_customer_payment(self):
        if self.is_subscription_customer and not self.subscription_customer_payment_mode_id:
            self.subscription_customer_payment_mode_id = self.env.ref('publishing_subscription_order.payment_mode_inbound_subscriptiondd1', False)
