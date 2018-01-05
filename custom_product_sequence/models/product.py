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

class productTemplate(models.Model):
    _inherit = "product.template"

    default_code = fields.Char(required=True, default='/', string="ProductID")
    sequence_code = fields.Char(default='/', copy=False)

    _sql_constraints = [('uniq_temp_default_code', 'unique(default_code)', 'The reference must be unique'),]

    #Imp: override to avoid default_code set to '' in multi variant
    @api.depends('sequence_code')
    def _compute_default_code(self):
        for template in self:
            template.default_code = template.sequence_code

    #Imp: override to avoid default_code set based on variants
    @api.one
    def _set_default_code(self):
        pass

    #on variant duplicate sequence generates else on write
    @api.model
    def create(self, vals):
        if 'variantCopy' in self.env.context:
            sequence = self.env.ref('custom_product_sequence.seq_product_auto_adver')
            vals['sequence_code'] = sequence.next_by_id()
            vals['default_code'] = vals['sequence_code']
        return super(productTemplate, self).create(vals)

    @api.multi
    def write(self, vals):
        sequence = self.env.ref('custom_product_sequence.seq_product_auto_adver')
        for template in self:
            if template.sequence_code in [False, '/']:
                vals['sequence_code'] = sequence.next_by_id()
                vals['default_code'] = vals['sequence_code']
            elif template.sequence_code:
                vals['default_code'] = template.sequence_code
            super(productTemplate, template).write(vals)
        return True

class ProductProduct(models.Model):
    _inherit = 'product.product'

    default_code = fields.Char(required=True, default='/', string="ProductID", copy=False)

    _sql_constraints = [('uniq_default_code','unique(default_code)','The reference must be unique'),]

    @api.model
    def create(self, vals):
        if 'default_code' not in vals or vals['default_code'] == '/':
            sequence = self.env.ref('custom_product_sequence.seq_product_auto_adver')
            vals['default_code'] = sequence.next_by_id()
        return super(ProductProduct, self).create(vals)

    @api.multi
    def write(self, vals):
        for product in self:
            if product.default_code in [False, '/']:
                sequence = self.env.ref('custom_product_sequence.seq_product_auto_adver')
                vals['default_code'] = sequence.next_by_id()
            super(ProductProduct, product).write(vals)
        return True

    #pass context{'variantCopy':True} for template add sequence on create from variant duplicate
    @api.multi
    def copy(self, default=None):
        return super(ProductProduct, self.with_context({'variantCopy':True})).copy(default)