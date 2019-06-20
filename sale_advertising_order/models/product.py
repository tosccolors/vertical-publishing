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
    _inherit = "product.category"


    @api.multi
    @api.depends('name', 'parent_id')
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.parent_id:
                name = record.parent_id.name_get()[0][1] + ' / ' + name
            result.append((record.id, name))
        return result

    @api.one
    @api.depends('name', 'parent_id')
    def _name_get_fnc(self):
        name = self.name
        if self.parent_id:
            name = self.parent_id.name_get()[0][1] + ' / '+name
        self.complete_name = name

    def _get_topmost_parent(self):
        adv_parent = False
        parent = self.parent_id
        if parent and parent.parent_id:
            parent_left = self.parent_id.parent_left
            self.env.cr.execute("""
                SELECT adv_parent
                FROM product_category
                WHERE parent_left < %s
                AND parent_right > %s
                AND parent_id IS NULL
                
                 """, (parent_left, parent_left)
                 )
            result = self.env.cr.fetchall()
            adv_parent = result and result[0][0] or False
        elif parent:
            adv_parent = parent.adv_parent
        return adv_parent

    @api.onchange('parent_id')
    def onchange_adv_parent(self):
        adv_parent = self._get_topmost_parent()
        self.adv_parent = adv_parent

    complete_name = fields.Char(compute='_name_get_fnc', string='Name')
    date_type = fields.Selection([
            ('validity', 'Validity Date Range'),
            ('date', 'Date of Publication'),
            ('newsletter', 'Newsletter'),
            ('online', 'Online'),
            ('issue_date', 'Issue Date'),
        ], 'Date Type Advertising products')
    deadline_offset = fields.Integer('Hours offset from Issue Deadline', default=0)
    tag_ids = fields.Many2many('account.analytic.tag', 'product_category_tag_rel', 'categ_id', 'tag_id', string='Analytic Tags', copy=True)
    adv_parent = fields.Boolean('Advertising Parent Category')



class productTemplate(models.Model):
    _inherit = "product.template"

    height = fields.Integer('Height', help="Height advertising format in mm")
    width = fields.Integer('Width', help="Width advertising format in mm")
    page_id = fields.Many2one('sale.advertising.page', string='Issue Page')
    space = fields.Integer('Space', help="Space taken by ad")
    price_edit = fields.Boolean('Price Editable')
    booklet_surface_area = fields.Float('Booklet Surface Area', help="Page surface booklet (newspaper) format in cm2",
                                        digits=dp.get_precision('Product Unit of Measure'))
    volume_discount = fields.Boolean('Volume Discount', help='Setting this flag makes that price finding in a multi-line '
                                                             'advertising sale order line, uses the multi_line_number '
                                                             'instead of product_uom_qty to implement volume discount' )


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
