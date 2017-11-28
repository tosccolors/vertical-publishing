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


class AdOrderMakeInvoice(models.TransientModel):
    _name = "ad.order.make.invoice"
    _description = "Advertising Order Make_invoice"

    @api.multi
    def make_invoices_from_ad_orders(self):
        context = self._context

        order_ids = context.get('active_ids', [])
        his_obj = self.env['ad.order.line.make.invoice']

        lines = self.env['sale.order.line'].search([('order_id','in', order_ids)])

        ctx = context.copy()
        ctx['active_ids'] = lines.ids
        his_obj.with_context(ctx).make_invoices_from_lines()
        return True



class AdOrderLineMakeInvoice(models.TransientModel):
    _name = "ad.order.line.make.invoice"
    _description = "Advertising Order Line Make_invoice"

    @api.model
    def _prepare_invoice(self, partner, published_customer, lines):

        self.ensure_one()
        if partner and partner.property_customer_payment_term_id.id:
            pay_term = partner.property_customer_payment_term_id.id
        else:
            pay_term = False

        journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(_('Please define an accounting sale journal for this company.'))

        dateInvoice = self._context.get('date_invoice', False) or fields.Date.today()
#        Section = order.account_analytic_id.section_ids

        return {
            'name': lines['name'] or '',
            'origin': "in te vullen",
            'type': 'out_invoice',
            'reference': False,
            'account_id': partner.partner_invoice_id.property_account_receivable_id.id,
            'partner_id': partner.partner_invoice_id.id,
            'published_customer': published_customer.id,
            'invoice_line_ids': [(6, 0, lines['lines'])],
            'comment': "in te vullen",
            'payment_term': pay_term,
            'journal_id': journal_id,
            'fiscal_position_id': partner.property_account_position_id.id,
            'user_id': self.uid ,
            'company_id': self.company_id.id,
            'date_invoice': dateInvoice,
            'partner_bank_id': partner.bank_ids and partner.bank_ids[0].id or False,
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
            raise UserError(_('No Ad Order lines are selected for invoicing:\n'))
        else: lids = context.get('active_ids', [])

        res = False
        invoices = {}

        def make_invoice(partner, published_customer, lines):
            vals = self._prepare_invoice(partner, published_customer, lines)
            invoice = self.env['account.invoice'].create(vals)
            self._cr.execute('insert into sale_order_invoice_rel (order_id,invoice_id) values (%s,%s)', (lines.order_id.id, invoice.id))
            return invoice.id

        OrderLine = self.env['sale.order.line']
        Order = self.env['sale.order']

        for line in OrderLine.browse(lids):
            key = (line.order_partner_id, line.order_id.published_customer)

            if (not line.invoice_lines) and (line.state in ('sale', 'done')) :
                if not key in invoices:
                    invoices[key] = {'lines':[],'subtotal':0, 'name': ''}

                inv_line_id = line.invoice_line_create()

                for lid in inv_line_id:
                    invoices[key]['lines'].append(lid)
                    invoices[key]['subtotal'] += line.price_subtotal
                    invoices[key]['name'] += str(line.name)+' / '

        if not invoices:
            raise UserError(_('Invoice cannot be created for this Advertising Order Line due to one of the following reasons:\n'
                              '1.The state of this ad order line is either "draft", "submitted", "approved1", "approved2", "sent", or "cancel"!\n'
                              '2.The Line is Invoiced!\n'))

        newInvoices = []
        for key, il in invoices.items():
            partner = key[0]
            published_customer = key[1]

            newInv = make_invoice(partner, published_customer, il)
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

    @api.multi
    def _prepare_invoice_line(self, qty):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        """
        self.ensure_one()
        res = {}
        account = self.product_id.property_account_income_id or self.product_id.categ_id.property_account_income_categ_id
        if not account:
            raise UserError(
                _('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
                (self.product_id.name, self.product_id.id, self.product_id.categ_id.name))

        fpos = self.order_id.fiscal_position_id or self.order_id.partner_id.property_account_position_id
        if fpos:
            account = fpos.map_account(account)

        res = {
            'name': self.name,
            'sequence': self.sequence,
            'origin': self.order_id.name,
            'account_id': account.id,
            'price_unit': self.price_unit,
            'quantity': qty,
            'discount': self.discount,
            'uom_id': self.product_uom.id,
            'product_id': self.product_id.id or False,
            'layout_category_id': self.layout_category_id and self.layout_category_id.id or False,
            'invoice_line_tax_ids': [(6, 0, self.tax_id.ids)],
            'account_analytic_id': self.order_id.project_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
        }
        return res

    @api.multi
    def invoice_line_create(self, invoice_id, qty):
        """
        Create an invoice line. The quantity to invoice can be positive (invoice) or negative
        (refund).

        :param invoice_id: integer
        :param qty: float quantity to invoice
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            if not float_is_zero(qty, precision_digits=precision):
                vals = line._prepare_invoice_line(qty=qty)
                vals.update({'invoice_id': invoice_id, 'sale_line_ids': [(6, 0, [line.id])]})
                self.env['account.invoice.line'].create(vals)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
