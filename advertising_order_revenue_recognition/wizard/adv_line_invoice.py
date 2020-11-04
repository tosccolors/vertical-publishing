# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

class AdOrderLineMakeInvoice(models.TransientModel):
    _inherit = "ad.order.line.make.invoice"

    @api.multi
    def _prepare_invoice_line(self, line):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.
        :param line: sales order line to invoice
        """
        line.ensure_one()
        start_date = 0
        end_date = 0
        res = super(AdOrderLineMakeInvoice, self)._prepare_invoice_line(line)

        if line.to_date and line.from_date:
            start_date = line.from_date
            end_date = line.to_date
        else:
            if line.issue_date:
                start_date = line.issue_date
                end_date = line.issue_date
        res.update({
            'start_date':start_date,
            'end_date':end_date,})
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
