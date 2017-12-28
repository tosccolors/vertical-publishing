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
        context = dict(self._context or {})
        company_id = context.get('company_id', []) or []
        journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
#        partner_record = self.env['res.partner'].search([('id', '=', partner.id)])
#        published_record = self.env['res.partner'].search([('id', '=', published_customer.id)])
        if not journal_id:
            raise UserError(_('Please define an accounting sale journal for this company.'))
        return {
            'name': lines['name'] or '',
#            'origin': lines.name,
            'type': 'out_invoice',
            'account_id': partner.property_account_receivable_id.id,
            'partner_id': partner.id,
#            'published_customer': published_customer.id,
            'invoice_line_ids': [(6, 0, lines['lines'])],
#            'comment': lines['note'],
#            'payment_term_id': partner.payment_term_id.id or False,
            'journal_id': journal_id,
            'fiscal_position_id': partner.property_account_position_id.id,
            'user_id': partner.user_id.id,
            'company_id': self.env.user.company_id.id,
            'partner_bank_id': partner.bank_ids and partner.bank_ids[0].id or False,
#            'check_total': lines['subtotal'],
            'team_id': partner.team_id.id
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
#            self._cr.execute('update account_invoice_line set invoice_id=%s where id in %s ', (invoice.id,lines.ids))
            return invoice.id

        OrderLine = self.env['sale.order.line']
        Order = self.env['sale.order']

        for line in OrderLine.browse(lids):
            key = (line.order_partner_id, line.order_id.published_customer)

            if (not line.invoice_lines) and (line.state in ('sale', 'done')) :
                if not key in invoices:
                    invoices[key] = {'lines':[],'subtotal':0, 'name': ''}

                inv_line_id = self.invoice_line_create(line)

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
    def _prepare_invoice_line(self,line):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        """
        line.ensure_one()
        res = {}
        account = line.product_id.property_account_income_id or line.product_id.categ_id.property_account_income_categ_id
        if not account:
            raise UserError(
                _('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
                (line.product_id.name, line.product_id.id, line.product_id.categ_id.name))

        fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
        if fpos:
            account = fpos.map_account(account)

        res = {
            'name': line.name,
            'sequence': line.sequence,
            'origin': line.order_id.name,
            'account_id': account.id,
            'price_unit': line.actual_unit_price,
            'quantity': line.product_uom_qty,
            'discount': line.discount,
            'uom_id': line.product_uom.id,
            'product_id': line.product_id.id or False,
            'layout_category_id': line.layout_category_id and line.layout_category_id.id or False,
            'invoice_line_tax_ids': [(6, 0, line.tax_id.ids)],
            'account_analytic_id': line.adv_issue.analytic_account_id.id,
            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
        }
        return res

    @api.multi
    def invoice_line_create(self, line):
        """
        Create an invoice line.
        """
        self.ensure_one()
        vals = self._prepare_invoice_line(line)
        vals.update({'sale_line_ids': [(6, 0, [line.id])]})
        return self.env['account.invoice.line'].create(vals)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
