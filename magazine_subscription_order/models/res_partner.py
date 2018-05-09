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
    property_subscription_journal_id = fields.Many2one('account.journal', string="Subscription Payment Method", company_dependent=True)
    property_subscription_payment_term_id = fields.Many2one('account.payment.term', company_dependent=True, string='Subscription Payment Terms', help="This payment term will be used instead of the default one for subscription orders and subscription bills")

    @api.model
    def _commercial_fields(self):
        return super(Partner, self)._commercial_fields() + ['property_subscription_payment_term_id','property_subscription_journal_id','is_subscription_customer']

    @api.constrains('date_start', 'date_end')
    def _check_start_end_dates(self):
        for partner in self.filtered('date_end'):
            if partner.date_start and partner.date_start > partner.date_end:
                raise ValidationError(_("'Validity From' can't be future date than 'Validity To'!"))

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
