# -*- coding: utf-8 -*-
# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class Invoice(models.Model):
    _inherit = 'account.move'

    published_customer = fields.Many2one('res.partner', 'Advertiser', domain=[('is_customer', '=', True)])
    invoice_description = fields.Text('Description')


    def _get_name_invoice_report(self):
        self.ensure_one()
        ref = self.env.ref

        if self.sale_type_id.id == ref('sale_advertising_order.ads_sale_type').id:
            return 'sale_advertising_order.report_invoice_document_sao'
        return super()._get_name_invoice_report()


class InvoiceLine(models.Model):
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
    computed_discount = fields.Float(string='Discount' )
    subtotal_before_agency_disc = fields.Float(compute='_compute_price', string='SBAD', readonly=True )
    # ad_number = fields.Char(string='External Reference', size=50)
    sale_order_id = fields.Many2one(related='so_line_id.order_id', relation='sale.order', store=True, string='Order Nr.')
    ad = fields.Boolean(related='so_line_id.advertising', string='Ad', store=True,
                                help="It indicates that the invoice line is from an Advertising Invoice.")

    
    def open_sale_order(self):
        # FIXME:
        view_id = self.env.ref('sale_advertising_order.view_order_form_advertising').id if self.sale_order_id.advertising else self.env.ref('sale.view_order_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'view_mode': 'form',
            'view_id':view_id,
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'target': 'current',
            'flags': {'initial_mode': 'view'},
        }
