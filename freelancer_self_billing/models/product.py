# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2016 Magnus www.magnus.nl
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
import odoo.addons.decimal_precision as dp


class PartnerProductPrice(models.Model):
    _name = "partner.product.price"

    name = fields.Char('Description', size=64, )
    product_id = fields.Many2one('product.product', 'Product', )
    partner_id = fields.Many2one('res.partner', 'Vendor', required=True,)
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self.env['res.company']._company_default_get('account.invoice'))
    price_unit = fields.Float('Unit Price', digits=dp.get_precision('Product Price'))
    comment = fields.Text('Additional Information')


class Category(models.Model):
    _inherit = "product.category"

    hon_type = fields.Selection([('letter_a', 'Letter declaring Payment'),
            ('letter_b', 'Letter requiring Invoice'),],
            string='Letter Type',
            help="Indicator that determines the print layout of the invoice based on products in this category.")



