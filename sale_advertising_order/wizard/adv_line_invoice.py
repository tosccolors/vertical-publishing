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
from odoo.exceptions import UserError, ValidationError
# from odoo.addons.queue_job.job import job, related_action
from odoo.addons.queue_job.exception import FailedJobError
from unidecode import unidecode


class AdOrderMakeInvoice(models.TransientModel):
    _name = "ad.order.make.invoice"
    _description = "Advertising Order Make_invoice"

    invoice_date = fields.Date('Invoice Date', default=fields.Date.today)
    posting_date = fields.Date('Posting Date', default=False)
    job_queue = fields.Boolean('Process via Job Queue', default=False)
    chunk_size = fields.Integer('Chunk Size Job Queue', default=50)
    execution_datetime = fields.Datetime('Job Execution not before', default=fields.Datetime.now())


    def make_invoices_from_ad_orders(self):
        context = self._context

        order_ids = context.get('active_ids', [])
        his_obj = self.env['ad.order.line.make.invoice']
        lines = self.env['sale.order.line'].search([('order_id','in', order_ids)])
        ctx = context.copy()
        ctx['active_ids'] = lines.ids
        ctx['invoice_date'] = self.invoice_date
        ctx['posting_date'] = self.posting_date
        ctx['chunk_size'] = self.chunk_size
        ctx['job_queue'] = self.job_queue
        ctx['execution_datetime'] = self.execution_datetime
        his_obj.with_context(ctx).make_invoices_from_lines()
        return True



class AdOrderLineMakeInvoice(models.TransientModel):
    _name = "ad.order.line.make.invoice"
    _description = "Advertising Order Line Make_invoice"

    invoice_date = fields.Date('Invoice Date', default=fields.Date.today)
    posting_date = fields.Date('Posting Date', default=False)

    # --- [deprecated] following fields are removed in view level ---
    job_queue = fields.Boolean('Process via Job Queue', default=False) # deprecated
    chunk_size = fields.Integer('Chunk Size Job Queue', default=50) # deprecated
    execution_datetime = fields.Datetime('Job Execution not before', default=fields.Datetime.now()) # deprecated

    @api.model
    def _prepare_invoice(self, keydict, lines, invoice_date, posting_date):
        ref = self.env.ref
        partner = keydict['partner_id']
        published_customer = keydict['published_customer']
        payment_mode = keydict['payment_mode_id']
        operating_unit = keydict['operating_unit_id']
        invoice_payment_term_id = keydict['payment_term_id']
        journal_id = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal().id
        if not journal_id:
            raise UserError(_('Please define an accounting sale journal for this company.'))
        vals = {
            'invoice_date': invoice_date,
            'date': posting_date or False,
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'published_customer': published_customer.id,
            'invoice_line_ids': lines['lines'],
            'narration': lines['name'],
            'invoice_payment_term_id': invoice_payment_term_id,
            'journal_id': journal_id,
            'fiscal_position_id': partner.property_account_position_id.id or False,
            'user_id': self.env.user.id,
            'company_id': self.env.user.company_id.id,
            'operating_unit_id': operating_unit.id,
            'payment_mode_id': payment_mode.id or False,
            'partner_bank_id': payment_mode.fixed_journal_id.bank_account_id.id
                               if payment_mode.bank_account_link == 'fixed'
                               else partner.bank_ids and partner.bank_ids[0].id or False,
            'sale_type_id': ref('sale_advertising_order.ads_sale_type').id,
        }
        return vals



    def make_invoices_from_lines(self):
        """
             To make invoices.
        """
        context = self._context
        inv_date = self.invoice_date
        post_date = self.posting_date
        size = False
        eta  = False
        jq   = False
        if self.job_queue:
            jq = self.job_queue
            size = self.chunk_size
            eta = fields.Datetime.from_string(self.execution_datetime)
        if not context.get('active_ids', []):
            message = 'No ad order lines selected for invoicing.'
            if context.get('job_queue') == True :
                return message+"\n"
            else :
                raise UserError(_(message))
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
            description = context.get('job_queue_description', False)
            if description :
                self.with_delay(eta=eta, description=description).make_invoices_split_lines_jq(inv_date, post_date, OrderLines, eta, size)
            else :
                self.with_delay(eta=eta).make_invoices_split_lines_jq(inv_date, post_date, OrderLines, eta, size)
            return "Lines dispatched for async processing. See separate job(s) for result(s).\n"
        else:
            self.make_invoices_job_queue(inv_date, post_date, OrderLines)
            return "Lines dispatched."

    # @job
    def make_invoices_split_lines_jq(self, inv_date, post_date, olines, eta, size):
            partners = olines.mapped('order_id.partner_invoice_id')
            chunk = False
            for partner in partners:
                lines = olines.filtered(lambda r: r.order_id.partner_invoice_id.id == partner.id)
                if len(lines) > size:
                    published_customer = lines.filtered('order_id.published_customer').mapped('order_id.published_customer')
                    for pb in published_customer:
                        linespb = lines.filtered(lambda r: r.order_id.published_customer.id == pb.id)
                        chunk = linespb if not chunk else chunk | linespb
                        if len(chunk) < size:
                            continue
                        self.with_delay(eta=eta).make_invoices_job_queue(inv_date, post_date, chunk)
                        chunk = False
                    remaining_lines = lines.filtered(lambda r: not r.order_id.published_customer)
                    chunk = remaining_lines if not chunk else chunk | remaining_lines
                    self.with_delay(eta=eta).make_invoices_job_queue(inv_date, post_date, chunk)
                else:
                    chunk = lines if not chunk else chunk | lines
                    if len(chunk) < size:
                        continue
                    description = "invoicing " + str(len(chunk)) + " orderlines"
                    self.with_delay(eta=eta, description=description).make_invoices_job_queue(inv_date, post_date, chunk)
                    chunk = False
            if chunk:
                    description = "invoicing " + str(len(chunk)) + " orderlines"
                    self.with_delay(eta=eta, description=description).make_invoices_job_queue(inv_date, post_date, chunk)
            return "Invoice lines successfully chopped in chunks. Chunks will be processed in separate jobs.\n"

    def modify_key(self, key, keydict, line):
        """Hook method to modify grouping key of advertising invoicing"""
        return key, keydict


    def make_invoice(self, keydict, lines, inv_date, post_date):
        vals = self._prepare_invoice(keydict, lines, inv_date, post_date)
        invoice = self.env['account.move'].create(vals)
        # invoice.compute_taxes() --deprecated
        return invoice

    # @job
    def make_invoices_job_queue(self, inv_date, post_date, chunk):
        invoices = {}
        count = 0
        for line in chunk:
            key = (line.order_id.partner_invoice_id, line.order_id.published_customer, line.order_id.payment_mode_id,
                   line.order_id.operating_unit_id, line.order_id.payment_term_id.id)
            keydict = {
                'partner_id': line.order_id.partner_invoice_id,
                'published_customer': line.order_id.published_customer,
                'payment_mode_id': line.order_id.payment_mode_id,
                'operating_unit_id': line.order_id.operating_unit_id,
                'payment_term_id': line.order_id.payment_term_id.id,
            }
            key, keydict = self.modify_key(key, keydict, line)

            #if (not line.invoice_lines) and (line.state in ('sale', 'done')) :
            if line.qty_to_invoice > 0 and (line.state in ('sale', 'done')):
                if not key in invoices:
                    invoices[key] = {'lines':[], 'name': ''}
                    invoices[key]['keydict'] = keydict
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
            try:
                self.make_invoice(invoices[key]['keydict'], il, inv_date, post_date)
            except Exception as e:
                if self.job_queue:
                    raise FailedJobError(_("The details of the error:'%s' regarding '%s'") % (str(e), il['name'] ))
                else:
                    raise UserError(_("The details of the error:'%s' regarding '%s'") % (str(e), il['name'] ))
        #raise ValidationError(_("Your selection consisted of:'%s' \n The number of succesfully invoiced lines is '%s'") % (len(chunk), len(chunk)))
        return "Invoice(s) successfully made."


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



    def _prepare_invoice_line(self, line):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param line: sales order line to invoice
        """
        line.ensure_one()
        account = line.product_id.property_account_income_id or line.product_id.categ_id.property_account_income_categ_id
        if not account:
            raise UserError(
                _('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
                (line.product_id.name, line.product_id.id, line.product_id.categ_id.name))

        fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
        if fpos:
            account = fpos.map_account(account)
        
        res = {
            'name': line.title.name or "/",
            'sequence': line.sequence,
            # 'origin': line.order_id.name, -- deprecated; perhaps we could use ref instead? FIXME
            'account_id': account.id,
            'price_unit': line.actual_unit_price,
            'quantity': line.product_uom_qty,
            'discount': line.discount,
            'product_uom_id': line.product_uom.id,
            'product_id': line.product_id and line.product_id.id or False,
            'tax_ids': [(6, 0, line.tax_id.ids or [])],
            'analytic_account_id': line.adv_issue.analytic_account_id and line.adv_issue.analytic_account_id.id or False,
            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids or [])],
            'so_line_id': line.id,
            'computed_discount': line.computed_discount,
            'ad_number': line.ad_number,
            'opportunity_subject': line.order_id.opportunity_subject,
            'sale_line_ids': [(6, 0, [line.id])],
            'from_date' : line.from_date,
            'to_date' : line.to_date,
            'issue_date' : line.issue_date,
        }
        return res

