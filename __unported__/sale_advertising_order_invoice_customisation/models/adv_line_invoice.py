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
from odoo.exceptions import UserError
# from odoo.addons.queue_job.job import job, related_action
from odoo.addons.queue_job.exception import FailedJobError
from unidecode import unidecode

class AdOrderLineMakeInvoice(models.TransientModel):
    _inherit = "ad.order.line.make.invoice"
    _description = "Advertising Order Line Make_invoice"

    @api.model
    def _prepare_invoice(self, keydict, lines, invoice_date, posting_date):
        customer_contact = keydict['customer_contact_id']
        vals = super(AdOrderLineMakeInvoice, self)._prepare_invoice(keydict, lines, invoice_date, posting_date)
        vals['customer_contact'] = customer_contact
        return vals

    def modify_key(self, key, keydict, line):
        key, keydict = super(AdOrderLineMakeInvoice, self).modify_key(key, keydict, line)
        key = list(key)
        key.append(line.order_id.customer_contact)
        key = tuple(key)
        keydict['customer_contact_id'] = line.order_id.customer_contact.id
        return key, keydict

    
    def make_invoices_from_lines(self):
        """
             To make invoices.
        """
        context = self._context
        inv_date = self.invoice_date
        post_date = self.posting_date
        jq = False
        size = False
        eta = False
        if self.job_queue:
            jq = self.job_queue
            size = self.chunk_size
            eta = fields.Datetime.from_string(self.execution_datetime)
        if not context.get('active_ids', []):
            raise UserError(_('No Ad Order lines are selected for invoicing:\n'))
        else:
            lids = context.get('active_ids', [])
            OrderLines = self.env['sale.order.line'].browse(lids)
            invoice_date_ctx = context.get('invoice_date', False)
            posting_date_ctx = context.get('posting_date', False)
            jq_ctx = context.get('job_queue', False)
            size_ctx = context.get('chunk_size', False)
            eta_ctx = context.get('execution_datetime', False)
        if invoice_date_ctx and not inv_date:
            inv_date = invoice_date_ctx
        if posting_date_ctx and not post_date:
            post_date = posting_date_ctx
        if jq_ctx and not jq:
            jq = True
            if len(self) == 1:
                self.job_queue = True
            if size_ctx and not size:
                size = size_ctx
            if eta_ctx and not eta:
                eta = fields.Datetime.from_string(eta_ctx)
        if jq:
            self.with_delay(eta=eta).make_invoices_split_lines_jq(inv_date, post_date, OrderLines, eta, size)
        else:
            self.make_invoices_job_queue(inv_date, post_date, OrderLines)

