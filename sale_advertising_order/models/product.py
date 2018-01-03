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


    complete_name = fields.Char(compute='_name_get_fnc', string='Name')
    date_type = fields.Selection([
            ('validity', 'Validity Date Range'),
            ('date', 'Date of Publication'),
            ('newsletter', 'Newsletter'),
            ('online', 'Online'),
            ('issue_date', 'Issue Date'),
        ], 'Date Type Advertising products')
    deadline_offset = fields.Integer('Hours offset from Issue Deadline', default=0)


class productTemplate(models.Model):
    _inherit = "product.template"

    height = fields.Integer('Height', help="Height advertising format in mm")
    width = fields.Integer('Width', help="Width advertising format in mm")

    default_code = fields.Char(default='/', string="ProductID")
    code = fields.Char(default='/')

    _sql_constraints = [('uniq_default_code', 'unique(default_code)', 'The reference must be unique'),]

    ## override to avoid default_code set to '' for multi
    @api.depends('code')
    def _compute_default_code(self):
        for template in self:
            template.default_code = template.code

    ## override to avoid default_code set based on variants
    @api.one
    def _set_default_code(self):
        pass

    @api.multi
    def write(self, vals):
        sequence = self.env.ref('sale_advertising_order.seq_product_auto_adver')
        for template in self:
            if template.code in [False, '/']:
                vals['code'] = sequence.next_by_id()
                vals['default_code'] = vals['code']
            elif template.code:
                vals['default_code'] = template.code
            super(productTemplate, template).write(vals)
        return True

    @api.multi
    def copy(self, default=None):
        if default is None:
            default = {}
        if self.default_code:
            default.update({
                'default_code': self.default_code + _('-copy'),
            })
        return super(productTemplate, self).copy(default)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    default_code = fields.Char(required=True, default='/', string="ProductID")

    _sql_constraints = [
        ('uniq_default_code',
         'unique(default_code)',
         'The reference must be unique'),
    ]

    @api.model
    def create(self, vals):
        if 'default_code' not in vals or vals['default_code'] == '/':
            sequence = self.env.ref('sale_advertising_order.seq_product_auto_adver')
            vals['default_code'] = sequence.next_by_id()
        return super(ProductProduct, self).create(vals)

    @api.multi
    def write(self, vals):
        for product in self:
            if product.default_code in [False, '/']:
                sequence = self.env.ref('sale_advertising_order.seq_product_auto_adver')
                vals['default_code'] = sequence.next_by_id()
            super(ProductProduct, product).write(vals)
        return True

    @api.multi
    def copy(self, default=None):
        if default is None:
            default = {}
        if self.default_code:
            default.update({
                'default_code': self.default_code + _('-copy'),
            })
        return super(ProductProduct, self).copy(default)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
