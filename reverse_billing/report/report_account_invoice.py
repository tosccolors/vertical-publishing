# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2016 Odoo Experts
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

import time
from datetime import datetime
from odoo.report import report_sxw

class account_invoice_hon(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context=None):
        super(account_invoice_hon, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_date': self.get_date,
            'new_date': self.new_date,
        })

    def get_date(self, date_invoice):
        if date_invoice in ['False' or False]:
            return False
        return datetime.strptime(date_invoice, "%Y-%m-%d").strftime('%d-%m-%Y')

    def new_date(self, date_due):
        if date_due in ['False' or False]:
            return False
        return datetime.strptime(date_due, "%Y-%m-%d").strftime('%d-%m-%Y')


report_sxw.report_sxw(
    'report.account.invoice.hon',
    'account.invoice',
    'addons/freelancer_self_billing/report/report_account_invoice_print.rml',
    parser=account_invoice_hon,
)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
