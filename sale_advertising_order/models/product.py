# -*- coding: utf-8 -*-
# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _

class productCategory(models.Model):
    _inherit = ["product.category"]

    date_type = fields.Selection([
            ('validity', 'Validity Date Range'),
            ('date', 'Date of Publication'),
            ('issue_date', 'Issue Date'),
        ], 'Date Types', help="Date Types for Advertising Products")
    deadline_offset = fields.Integer('Hours offset from Issue Deadline', default=0)
    tag_ids = fields.Many2many('account.analytic.tag', 'product_category_tag_rel',
                               'categ_id', 'tag_id', string='Analytic Tags', copy=True)



class productTemplate(models.Model):
    _inherit = "product.template"

    @api.depends('categ_id')
    def _compute_ads_products(self):
        """
        Compute the boolean for ads products.
        """
        ads_cat = self.env.ref('sale_advertising_order.advertising_category').id
        title_categ = self.env.ref('sale_advertising_order.interface_portal_category').id
        for rec in self:
            parent_categ_ids = [int(p) for p in rec.categ_id.parent_path.split('/')[:-1]]
            if ads_cat in parent_categ_ids or title_categ in parent_categ_ids:
                rec.is_ads_products = True
            else:
                rec.is_ads_products = False


    height = fields.Integer('Height', help="Height advertising format in mm")
    width = fields.Integer('Width', help="Width advertising format in mm")
    # page_id = fields.Many2one('sale.advertising.page', string='Issue Page') #FIXME: Need?
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
