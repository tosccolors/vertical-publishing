# -*- coding: utf-8 -*-
# Copyright 2018 Magnus ((www.magnus.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def _get_product_domain(self):
        domain = [('sale_ok', '=', True)]
        if 'default_advertising' not in self._context or not self._context.get('default_advertising'):
            id = self.env.ref('sale_advertising_order.advertising_category').id
            product_ids = self.env['product.product'].search([('categ_id', 'child_of', id)])
            domain.append(('id', 'not in', product_ids.ids))
        return domain

    product_id = fields.Many2one('product.product', string='Product', domain=_get_product_domain, change_default=True, ondelete='restrict', required=True)
