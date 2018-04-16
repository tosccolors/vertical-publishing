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
    _inherit = ['res.partner', 'time.dependent']

    is_subscription_customer = fields.Boolean('Subscription Customer', default=False)
    date_start = fields.Date(string='Validity From')
    date_end = fields.Date(string='Validity To', index=True)
    # subscription_payment_id = fields.Many2one('account.journal',string='Subscription Payment Method', ondelete='set null', index=True, default=False)
    property_subscription_subscription = fields.Many2one('account.journal', string="Subscription Payment Method", company_dependent=True)
    subs_sale_order_count = fields.Integer(compute='_compute_subs_sale_order_count', string='Subscription Sales Order')

    @api.constrains('date_start', 'date_end')
    def _check_start_end_dates(self):
        for partner in self.filtered('date_end'):
            if partner.date_start and partner.date_start > partner.date_end:
                raise ValidationError(_("'Validity From' can't be future date than 'Validity To'!"))

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

    @api.multi
    @api.onchange('date_start','date_end')
    def date_validation(self):
        if self._origin.date_start and self.date_start:
            old_validity_from = datetime.strptime(self._origin.date_start, "%Y-%m-%d")
            new_validity_from = datetime.strptime(self.date_start, "%Y-%m-%d")
            if new_validity_from < old_validity_from:
                raise ValidationError(_("'Validity From' can't be later than previous 'Validity From'!"))
        if self._origin.date_end and self.date_end:
            old_validity_to = datetime.strptime(self._origin.date_end, "%Y-%m-%d")
            new_validity_to = datetime.strptime(self.date_end, "%Y-%m-%d")
            if new_validity_to < old_validity_to:
                raise ValidationError(_("'Validity To' can't be later than previous 'Validity To'!"))
