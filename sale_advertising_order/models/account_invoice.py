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



class Invoice(models.Model):
    """ Inherits invoice and adds ad boolean to invoice to flag Advertising-invoices"""
    _inherit = 'account.invoice'

    ad = fields.Boolean(related='invoice_line_ids.ad', string='Ad', help="It indicates that the invoice is an Advertising Invoice.", store=True)
    published_customer = fields.Many2one('res.partner', 'Advertiser', domain=[('customer', '=', True)])


class InvoiceLine(models.Model):
    """ Inherits invoice.line and adds advertising order line id and publishing date to invoice """
    _inherit = 'account.invoice.line'


    @api.multi
    @api.depends('price_unit', 'quantity')
    def _compute_price(self):
        """
        Compute subtotal_before_agency_disc.
        """
        for line in self:
            if line.ad:
                price_unit = line.price_unit or 0.0
                qty = line.quantity or 0.0
                if price_unit and qty:
                    line.subtotal_before_agency_disc = price_unit * qty
            else:
                line.subtotal_before_agency_disc = 0.0
        super(InvoiceLine, self)._compute_price()


    date_publish = fields.Date('Publishing Date')
    so_line_id = fields.Many2one('sale.order.line', 'link between Sale Order Line and Invoice Line')
    computed_discount = fields.Float(string='Discount' )
    subtotal_before_agency_disc = fields.Float(compute='_compute_price', string='SBAD', readonly=True )
    ad_number = fields.Char(string='External Reference')
    opportunity_subject = fields.Char(string='Subject')
    sale_order_id = fields.Many2one(related='so_line_id.order_id', relation='sale.order', store=True, string='Order Nr.')
    ad = fields.Boolean(related='so_line_id.advertising', string='Ad', store=True,
                                help="It indicates that the invoice line is from an Advertising Invoice.")

    @api.multi
    def open_sale_order(self):
        view_id = self.env.ref('sale_advertising_order.view_order_form_advertising').id if self.sale_order_id.advertising else self.env.ref('sale.view_order_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id':view_id,
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'target': 'current',
            'flags': {'initial_mode': 'view'},
        }
