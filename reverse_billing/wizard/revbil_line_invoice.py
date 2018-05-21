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


class BatchMakeInvoice(models.TransientModel):
    _name = "sow.batch.make.invoice"
    _description = "Statement of Work Batch Make_invoice"

    @api.multi
    def make_invoices_from_batches(self):
        context = self._context

        batch_ids = context.get('active_ids', [])
        his_obj = self.env['revbil.statement.of.work.make.invoice']

        lines = self.env['revbil.statement.of.work'].search([('batch_id','in', batch_ids)])

        ctx = context.copy()
        ctx['active_ids'] = lines.ids
        his_obj.with_context(ctx).make_invoices_from_lines()
        return True



class RevBilStatementOfWorkMakeInvoice(models.TransientModel):
    _name = "revbil.statement.of.work.make.invoice"
    _description = "Statement of Work Make Invoice"

    @api.model
    def _prepare_invoice(self, partner, ou, batch, lines):
        batch_invoices = batch
        invoices = self.env['account.invoice'].search([('id','in', [x.id for x in batch_invoices.invoice_ids]),('partner_id','=',partner.id)])
        if len(invoices) >= 1:
            inv_count = len(invoices) + 1
        else:
            inv_count = 1
        a = partner.property_account_payable_id.id
        if partner and partner.property_supplier_payment_term_id.id:
            pay_term = partner.property_supplier_payment_term_id.id
        else:
            pay_term = False

        # -- deep: validation added
        RevbilJournalID = ou.company_id.revbil_journal and ou.company_id.revbil_journal.id or False
        if not RevbilJournalID:
            raise UserError(_('Please map "Reverse Billing Journal" in the Company master.'))

        dateInvoice = self._context.get('date_invoice', False) or fields.Date.today()
#        Section = issue.account_analytic_id.section_ids

        return {
            'name': lines['name'] or '',
            'revbil': True,
            'origin': batch.name,
            'type': 'in_invoice',
            'reference': False,
            'date_batch': batch.date_batch,
            'account_id': a,
            'partner_id': partner.id,
            'invoice_line_ids': [(6, 0, lines['lines'])],
            'comment': batch.comment,
            'payment_term': pay_term,
            'journal_id': RevbilJournalID,
            'operating_unit_id': ou.id,
            'fiscal_position_id': partner.property_account_position_id.id,
            'supplier_invoice_number': "RB%dNo%d" % (batch.id, inv_count),
            'user_id': self._uid,
            'company_id': batch.company_id.id,
            'date_invoice': dateInvoice,
            'partner_bank_id': partner.bank_ids and partner.bank_ids[0].id or False,
#            'product_category': category.id,
            'check_total': lines['subtotal'],
        }

    @api.multi
    def make_invoices_from_lines(self):
        """
             To make invoices.
             @return: A dictionary which of fields with values.
        """
        context = self._context
        if not context.get('active_ids', []):
            raise UserError(_('No Reverse Billing sow lines are selected for invoicing:\n'))
        else: lids = context.get('active_ids', [])

        res = False
        invoices = {}

        def make_invoice(partner, ou, batch, lines):
            vals = self._prepare_invoice(partner, ou, batch, lines)
            invoice = self.env['account.invoice'].create(vals)
            self._cr.execute('insert into sow_batch_invoice_rel (batch_id,invoice_id) values (%s,%s)', (batch.id, invoice.id))
            return invoice.id

        RevbilSow = self.env['revbil.statement.of.work']
        Batch = self.env['sow.batch']

        for line in RevbilSow.browse(lids):
            key = (line.analytic_account_id.operating_unit_ids[0], line.partner_id, line.batch_id)

            if (not line.invoice_line_id) and (line.state not in ('draft', 'cancel')) and (not line.employee) and (not line.gratis):
                if not key in invoices:
                    invoices[key] = {'lines':[],'subtotal':0, 'name': ''}

                inv_line_id = line.invoice_line_create()

                for lid in inv_line_id:
                    invoices[key]['lines'].append(lid)
                    invoices[key]['subtotal'] += line.price_subtotal
                    invoices[key]['name'] += str(line.name)+' / '

        if not invoices:
            raise UserError(_('Invoice cannot be created for this RevBil Statement of Work due to one of the following reasons:\n'
                              '1.The state of this sow line is either "draft" or "cancel"!\n'
                              '2.The RevBil Statement of Work is Invoiced!\n'
                              '3.The RevBil Statement of Work is marked "gratis"\n'
                              '4.The RevBil Statement of Work has an Employee as Creditor\n'))

        newInvoices = []
        for key, il in invoices.items():
            ou = key[0]
            partner = key[1]
            batch = key[2]

            newInv = make_invoice(partner, ou, batch, il)
            newInvoices.append(newInv)

        if context.get('open_invoices', False):
            return self.open_invoices(invoice_ids=newInvoices)
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def open_invoices(self, invoice_ids):
        """ open a view on one of the given invoice_ids """

        action = self.env.ref('account.action_invoice_tree2').read()[0]
        if len(invoice_ids) > 1:
            action['domain'] = [('id', 'in', invoice_ids)]
        elif len(invoice_ids) == 1:
            action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
            action['res_id'] = invoice_ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
