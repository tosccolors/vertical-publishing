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
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.queue_job.exception import FailedJobError
from unidecode import unidecode

class AdOrderLineMakeInvoice(models.TransientModel):
    _inherit = "ad.order.line.make.invoice"
    _description = "Advertising Order Line Make_invoice"

    @api.model
    def _prepare_invoice(self, partner, published_customer, payment_mode, operating_unit, lines, invoice_date, posting_date,customer_contact):
        
#        self.ensure_one()
#        line_ids = [x.id for x in lines['lines']]
        journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(_('Please define an accounting sale journal for this company.'))
        
        vals = {
            'date_invoice': invoice_date,
            'date': posting_date or False,
            'type': 'out_invoice',
            'account_id': partner.property_account_receivable_id.id,
            'partner_id': partner.id,
            'published_customer': published_customer.id,
            'invoice_line_ids': lines['lines'],
            'comment': lines['name'],
            'payment_term_id': partner.property_payment_term_id.id or False,
            'journal_id': journal_id,
            'fiscal_position_id': partner.property_account_position_id.id or False,
            'user_id': self.env.user.id,
            'company_id': self.env.user.company_id.id,
            'operating_unit_id': operating_unit.id,
            'payment_mode_id': payment_mode.id or False,
            'partner_bank_id': payment_mode.fixed_journal_id.bank_account_id.id
                               if payment_mode.bank_account_link == 'fixed'
                               else partner.bank_ids and partner.bank_ids[0].id or False,
            'customer_contact':customer_contact.id,
        }
        return vals



    @api.multi
    def make_invoices_from_lines(self):
        """
             To make invoices.
        """
        context = self._context
        inv_date = self.invoice_date
        post_date = self.posting_date
        jq = False
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
            jq = self.job_queue = True
            if size_ctx and not size:
                size = size_ctx
            if eta_ctx and not eta:
                eta = fields.Datetime.from_string(eta_ctx)
        if jq:
            self.with_delay(eta=eta).make_invoices_split_lines_jq(inv_date, post_date, OrderLines, eta, size)
        else:
            self.make_invoices_job_queue(inv_date, post_date, OrderLines)
    
    @job
    @api.multi
    def make_invoices_job_queue(self, inv_date, post_date, chunk):
        invoices = {}
        def make_invoice(partner, published_customer, payment_mode, operating_unit, lines, inv_date, post_date,customer_contact):
            vals = self._prepare_invoice(partner, published_customer, payment_mode, operating_unit,
                                         lines, inv_date, post_date,customer_contact)
            
            invoice = self.env['account.invoice'].create(vals)
            invoice.compute_taxes()
            return invoice.id
        count = 0
        for line in chunk:
            
            key = (line.order_id.partner_invoice_id, line.order_id.published_customer, line.order_id.payment_mode_id,
                   line.order_id.operating_unit_id,line.order_id.customer_contact)
            if (not line.invoice_lines) and (line.state in ('sale', 'done')) :
                if not key in invoices:
                    invoices[key] = {'lines':[], 'name': ''}

                inv_line_vals = self._prepare_invoice_line(line)
                invoices[key]['lines'].append((0, 0, inv_line_vals))
                if count < 3:
                    invoices[key]['name'] += unidecode(line.name)+' / '
                count += 1

        if not invoices and not self.job_queue:
            raise UserError(_('Invoice cannot be created for this Advertising Order Line due to one of the following reasons:\n'
                              '1.The state of these ad order lines are not "sale" or "done"!\n'
                              '2.The Lines are already Invoiced!\n'))
        elif not invoices:
            raise FailedJobError(_('Invoice cannot be created for this Advertising Order Line due to one of the following reasons:\n'
                                  '1.The state of these ad order lines are not "sale" or "done"!\n'
                                  '2.The Lines are already Invoiced!\n'))
        for key, il in invoices.items():
            partner = key[0]
            published_customer = key[1]
            payment_mode = key[2]
            operating_unit = key[3]
            customer_contact = key[4]
            try:
                make_invoice(partner, published_customer, payment_mode, operating_unit, il, inv_date, post_date,customer_contact)
            except Exception, e:
                if self.job_queue:
                    raise FailedJobError(_("The details of the error:'%s' regarding '%s'") % (unicode(e), il['name'] ))
                else:
                    raise UserError(_("The details of the error:'%s' regarding '%s'") % (unicode(e), il['name'] ))
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
