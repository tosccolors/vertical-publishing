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


#    ad = fields.Boolean('Ad', help="It indicates that the invoice is an Advertising Invoice.", default=False)
    ad = fields.Boolean(related='invoice_line_ids.ad', string='Ad', help="It indicates that the invoice is an Advertising Invoice.", store=True)
    published_customer = fields.Many2one('res.partner', 'Advertiser', domain=[('customer', '=', True)])



class InvoiceLine(models.Model):
    """ Inherits invoice.line and adds advertising order line id and publishing date to invoice """
    _inherit = 'account.invoice.line'

    @api.depends('price_unit', 'quantity', 'so_line_id.subtotal_before_agency_disc', 'so_line_id.ad_number',
                 'so_line_id.opportunity_subject', 'so_line_id.nett_nett')
    @api.multi
    def _compute_from_sol(self):
        """
        Compute subtotal_before_agency_disc.
        """
        for line in self.filtered('ad'):
            if line.price_unit and line.quantity:
                line.subtotal_before_agency_disc = line.price_unit * line.quantity
            

    date_publish = fields.Date('Publishing Date')
    so_line_id = fields.Many2one('sale.order.line', 'link between Sale Order Line and Invoice Line')
    computed_discount = fields.Float(related='so_line_id.computed_discount', store=True, string='Discount' )
    subtotal_before_agency_disc = fields.Float(compute='_compute_from_sol', string='SBAD' )
    ad_number = fields.Char(compute='_compute_from_sol', store=True, string='External Reference')
    opportunity_subject = fields.Char(compute='_compute_from_sol', store=True, string='Subject')
    nett_nett = fields.Boolean(compute='_compute_from_sol', store=True, string='Nett Nett')
    sale_order_id = fields.Many2one(related='so_line_id.order_id', relation='sale.order', store=True, string='Order Nr.')
    ad = fields.Boolean(related='so_line_id.advertising', string='Ad', store=True,
                                help="It indicates that the invoice line is from an Advertising Invoice.")

    @api.onchange('nett_nett', 'invoice_id.partner_id')
    def onchange_discount(self):
        if self.ad:
            if self.nett_nett:
                self.discount = 0.0
            else:
                if self.invoice_id.partner_id.is_ad_agency or self.invoice_id.partner_id.parent_id.is_ad_agency:
                    self.discount = self.invoice_id.partner_id.agency_discount or self.invoice_id.partner_id.parent_id.agency_discount