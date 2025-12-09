# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016 Magnus NL (<http://magnus.nl>).
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
import logging

_logger = logging.getLogger(__name__)


class Invoice(models.Model):
    """ Inherits invoice and adds ad boolean to invoice to flag Advertising-invoices"""
    _inherit = 'account.move'

    ad = fields.Boolean(related='invoice_line_ids.ad', string='Ad', help="It indicates that the invoice is an Advertising Invoice.", store=True)
    published_customer = fields.Many2one('res.partner', 'Advertiser', domain=[('is_customer', '=', True)])

    invoice_description = fields.Text('Description')
    has_failed2confirm = fields.Boolean('Failed to auto-validate', default=False, copy=False)


    def _get_name_invoice_report(self):
        self.ensure_one()
        ref = self.env.ref

        if self.sale_type_id.id == ref('sale_advertising_order.ads_sale_type').id:
            return 'sale_advertising_order.report_invoice_document_sao'
        return super()._get_name_invoice_report()

    def _post(self, soft=True):
        """
        Assign start/end date of ad issue belonging to the selected analytic account, if any
        """
        for line in self.line_ids:
            if line.from_date or not line.analytic_account_id:
                continue
            issue = self.env['sale.advertising.issue'].search([
                ('analytic_account_id', '=', line.analytic_account_id.id),
                ('parent_id', '!=', False),
            ], limit=1)
            if not issue:
                continue
            line.from_date = issue.issue_date
        return super()._post(soft=soft)


    @api.model
    def _get_invoice_key_cols_out(self):
        res = super()._get_invoice_key_cols_out()
        res.append('sale_type_id')
        res.remove('user_id')
        return res

    @api.model
    def _get_invoice_key_cols_in(self):
        res = super()._get_invoice_key_cols_in()
        res.append('sale_type_id')
        res.remove('user_id')
        return res

    @api.model
    def _get_invoice_line_key_cols(self):
        res = super()._get_invoice_line_key_cols()
        saoln = ['ad_number', 'issue_date', 'from_date', 'to_date']
        res2 = res + saoln
        return res2

    @api.model
    def _get_first_invoice_fields(self, invoice):
        res = super()._get_first_invoice_fields(invoice)
        res.update({'sale_type_id': invoice.sale_type_id.id, 'user_id': False})
        return res


    def _do_invoice_sent_wizard(self):
        self.ensure_one()
        wiz_send_invoice = self.env['account.invoice.send']
        ctx = dict(self.env.context)

        if self.is_move_sent:
            return _("This invoice has already been sent.")

        res = self.action_invoice_sent()
        ctx = res["context"] or {}
        ctx["active_model"] = self._name
        ctx["active_ids"] = self.ids

        wsi_vals = wiz_send_invoice.with_context(ctx).default_get(['template_id', 'partner_ids'])
        wiz = self.env["account.invoice.send"].with_context(**ctx).create(wsi_vals)
        wiz.write({
            "is_print": False,
            "is_email": True,
            'auto_delete': False,
            "composition_mode": "mass_mail",
        })
        return wiz.send_and_print_action()



    def _cron_auto_validate_invoices(self):
        "Called from Cron, to validate Out-Invoices which are in draft status."

        draftInvoices = self.search([('move_type', '=', 'out_invoice'), ('state', 'in', ('draft', 'sent'))], order='id, invoice_date', limit=2)

        for invoice in draftInvoices:
            try:
                invoice.action_post()
                invoice.has_failed2confirm = False
                invoice.message_post(body=_(
                    'This invoice has been auto validated.'))

                # Send Email: Check Amount & Transmission Method
                if invoice.amount_total > 0 and invoice.transmit_method_id.id != self.env.ref('sale_advertising_order.no_send_mail').id:
                    invoice._do_invoice_sent_wizard()

            except Exception as e:
                invoice.has_failed2confirm = True
                invoice.message_post(body=_(
                    'Unable to auto validate this invoice;  %s.')
                                 % (str(e)))



class InvoiceLine(models.Model):
    """ Inherits invoice.line and adds advertising order line id and publishing date to invoice """
    _inherit = 'account.move.line'

    @api.depends('price_unit', 'quantity')
    def _compute_price(self):
        """
        Compute subtotal_before_agency_disc.
        """
        for line in self:
            sbad = 0.0
            if line.ad:
                price_unit = line.price_unit or 0.0
                qty = line.quantity or 0.0
                if price_unit and qty:
                    sbad = price_unit * qty

            line.subtotal_before_agency_disc = sbad

    date_publish = fields.Date('Publishing Date')
    so_line_id = fields.Many2one('sale.order.line', 'link between Sale Order Line and Invoice Line')
    sale_line_id = fields.Integer(related='so_line_id.id', string='link between Sale Order Line and Invoice Line')
    computed_discount = fields.Float(string='Discount' )
    subtotal_before_agency_disc = fields.Float(compute='_compute_price', string='SBAD', readonly=True )
    ad_number = fields.Char(string='External Reference', size=50)
    opportunity_subject = fields.Char(string='Subject')
    sale_order_id = fields.Many2one(related='so_line_id.order_id', relation='sale.order', store=True, string='Order Nr.')
    ad = fields.Boolean(related='so_line_id.advertising', string='Ad', store=True,
                                help="It indicates that the invoice line is from an Advertising Invoice.")

    # Report: retain initial
    from_date = fields.Date('Start of Validity')
    to_date = fields.Date('End of Validity')
    issue_date = fields.Date('Issue Date')

    
    def open_sale_order(self):
        view_id = self.env.ref('sale_advertising_order.view_order_form_advertising').id if self.sale_order_id.advertising else self.env.ref('sale.view_order_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            # 'view_type': 'form',
            'view_mode': 'form',
            'view_id':view_id,
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'target': 'current',
            'flags': {'initial_mode': 'view'},
        }
