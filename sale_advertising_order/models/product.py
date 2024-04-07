# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2016 Magnus www.magnus.nl w.hulshof@magnus.nl
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


class productCategory(models.Model):
    _inherit = ["product.category"]

    
    @api.depends('name', 'parent_id')
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.parent_id:
                name = record.parent_id.name_get()[0][1] + ' / ' + name
            result.append((record.id, name))
        return result

    
    # @api.depends('name', 'parent_id')
    # def _name_get_fnc(self):
    #     for rec in self:
    #         name = rec.name
    #         if rec.parent_id:
    #             name = rec.parent_id.name_get()[0][1] + ' / '+name
    #         rec.complete_name = name

    # def _get_topmost_parent(self):
    #     adv_parent = False
    #     parent = self.parent_id
    #     if parent and parent.parent_id:
    #         parent_left = self.parent_id.parent_left
    #         self.env.cr.execute("""
    #             SELECT adv_parent
    #             FROM product_category
    #             WHERE parent_left < %s
    #             AND parent_right > %s
    #             AND parent_id IS NULL
    #
    #              """, (parent_left, parent_left)
    #              )
    #         result = self.env.cr.fetchall()
    #         adv_parent = result and result[0][0] or False
    #     elif parent:
    #         adv_parent = parent.adv_parent
    #     return adv_parent

    # @api.onchange('parent_id')
    # def onchange_adv_parent(self):
        # adv_parent = self._get_topmost_parent()
        # self.adv_parent = adv_parent




    # complete_name = fields.Char(compute='_name_get_fnc', string='Name') # deepa: In V14.0 This field exists with standard.

    date_type = fields.Selection([
            ('validity', 'Validity Date Range'),
            ('date', 'Date of Publication'),
            ('newsletter', 'Newsletter'),
            ('online', 'Online'),
            ('issue_date', 'Issue Date'),
        ], 'Date Type Advertising products')
    deadline_offset = fields.Integer('Hours offset from Issue Deadline', default=0)
    tag_ids = fields.Many2many('account.analytic.tag', 'product_category_tag_rel', 'categ_id', 'tag_id', string='Analytic Tags', copy=True)

    # adv_parent = fields.Boolean('Advertising Parent Category') # deepa: deprecated, this doesn't have any major impact.



class productTemplate(models.Model):
    _inherit = "product.template"

    @api.depends('categ_id')
    def _compute_ads_products(self):
        """
        Compute the boolean for ads products.
        """
        ads_cat = self.env.ref('sale_advertising_order.advertising_category').id
        title_categ = self.env.ref('sale_advertising_order.title_pricelist_category').id
        for rec in self:
            parent_categ_ids = [int(p) for p in rec.categ_id.parent_path.split('/')[:-1]]
            if ads_cat in parent_categ_ids or title_categ in parent_categ_ids:
                rec.is_ads_products = True
            else:
                rec.is_ads_products = False


    height = fields.Integer('Height', help="Height advertising format in mm")
    width = fields.Integer('Width', help="Width advertising format in mm")
    page_id = fields.Many2one('sale.advertising.page', string='Issue Page')
    space = fields.Integer('Space', help="Space taken by ad")
    price_edit = fields.Boolean('Price Editable')
    booklet_surface_area = fields.Float('Booklet Surface Area', help="Page surface booklet (newspaper) format in cm2",
                                        digits='Product Unit of Measure')
    volume_discount = fields.Boolean('Volume Discount', help='Setting this flag makes that price finding in a multi-line '
                                                             'advertising sale order line, uses the multi_line_number '
                                                             'instead of product_uom_qty to implement volume discount' )
    is_ads_products = fields.Boolean("Is Ads Products?", compute=_compute_ads_products)

    @api.onchange('height', 'width')
    def onchange_height_width(self):
        product_variant_ids = self.env['product.product'].search([('product_tmpl_id', '=', self._origin.id)])
        for variant in product_variant_ids:
            variant.write({'height': self.height})
            variant.write({'width': self.width})


class ProductProduct(models.Model):
    _inherit = 'product.product'

    height = fields.Integer('Height', help="Height advertising format in mm", store=True)
    width = fields.Integer('Width', help="Width advertising format in mm", store=True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
