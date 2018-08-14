# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AdOrderLineMakeInvoice(models.TransientModel):
    _inherit = "ad.order.line.make.invoice"

    @api.multi
    def _prepare_invoice_line(self, line):
        res = super(AdOrderLineMakeInvoice, self)._prepare_invoice_line(line)
        if line.filtered('subscription'):
            res['start_date'] = line.start_date
            res['end_date'] = line.end_date
            res['price_unit'] = line.price_unit
            res['name'] = line.name
        return res

    @api.model
    def _prepare_invoice(self, partner, published_customer, payment_mode, operating_unit, lines, invoice_date, posting_date):
        res = super(AdOrderLineMakeInvoice, self)._prepare_invoice(partner, published_customer, payment_mode,
                                                                   operating_unit, lines, invoice_date, posting_date)
        for invline in lines['lines']:
            if invline.sale_line_ids.filtered('subscription'):
                res['ad'] = False
                res['payment_term_id'] = partner.property_subscription_payment_term_id.id or False
                pay_mode = partner.subscription_customer_payment_mode_id
                res['payment_mode_id'] = pay_mode.id or False
                if res['type'] == 'out_invoice':
                    if pay_mode and pay_mode.bank_account_link == 'fixed':
                        res['partner_bank_id'] = pay_mode.fixed_journal_id.bank_account_id
                break
        return res

    @job
    @api.multi
    def make_invoices_job_queue(self, inv_date, post_date, chunk):
        invoices = {}

        def make_invoice(partner, published_customer, payment_mode, operating_unit, lines, inv_date, post_date, sub):
            vals = self._prepare_invoice(partner, published_customer, payment_mode, operating_unit,
                                         lines, inv_date, post_date, sub)
            invoice = self.env['account.invoice'].create(vals)
            return invoice.id

        count = 0
        for line in chunk:
            key = (line.order_id.partner_invoice_id, line.order_id.published_customer, line.order_id.payment_mode_id,
                   line.order_id.operating_unit_id, line.magazine)

            if (not line.invoice_lines) and (line.state in ('sale', 'done')):
                if not key in invoices:
                    invoices[key] = {'lines': [], 'name': ''}

                inv_line_vals = self.invoice_line_create(line)
                invoices[key]['lines'].append((0, 0, inv_line_vals))
                if count < 3:
                    invoices[key]['name'] += unidecode(line.name) + ' / '
                count += 1

        if not invoices and not self.job_queue:
            raise UserError(
                _('Invoice cannot be created for this Advertising Order Line due to one of the following reasons:\n'
                  '1.The state of these ad order lines are not "sale" or "done"!\n'
                  '2.The Lines are already Invoiced!\n'))
        elif not invoices:
            raise FailedJobError(
                _('Invoice cannot be created for this Advertising Order Line due to one of the following reasons:\n'
                  '1.The state of these ad order lines are not "sale" or "done"!\n'
                  '2.The Lines are already Invoiced!\n'))
        for key, il in invoices.items():
            partner = key[0]
            published_customer = key[1]
            payment_mode = key[2]
            operating_unit = key[3]
            try:
                make_invoice(partner, published_customer, payment_mode, operating_unit, il, inv_date, post_date)
            except Exception, e:
                if self.job_queue:
                    raise FailedJobError(_("The details of the error:'%s' regarding '%s'") % (unicode(e), il['name']))
                else:
                    raise UserError(_("The details of the error:'%s' regarding '%s'") % (unicode(e), il['name']))
        return True