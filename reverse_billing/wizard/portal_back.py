# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016 Magnus Group BV (www.magnus.nl).
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


from odoo import api, fields, models, _
from odoo.exceptions import UserError

class Portalback(models.TransientModel):
    """
    This wizard will send  all the selected draft invoices to the supplier Portal
    """

    _name = "account.invoice.portalback"
    _description = "Send the selected invoices to supplier portal"

    @api.multi
    def invoice_portalback(self):
        context = self._context
        if not context.get('active_ids'): return False

        data_inv = self.env['account.invoice'].browse(context['active_ids'])

        CategId = self.env['ir.model.data'].get_object('freelancer_self_billing', 'hon_categoryT').id

        for record in data_inv:
            if record.state != ('draft'):
                raise UserError(_("Selected invoice(s) cannot be sent to portal as they are not in 'Draft' state."))

            if record.product_category.id is CategId :
                raise UserError(_("Selected invoice(s) cannot be sent to portal as they have HON Tekst Category."))

            record.action_portalback()
        return {'type': 'ir.actions.act_window_close'}





# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
