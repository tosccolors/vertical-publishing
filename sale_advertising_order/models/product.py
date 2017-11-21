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

from odoo import api, fields, models


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
    deadline_offset = fields.Integer('Days offset from Issue Deadline', default=0)


class productTemplate(models.Model):
    _inherit = "product.template"

    height = fields.Integer('Height', help="Height advertising format in mm")
    width = fields.Integer('Width', help="Width advertising format in mm")
    booklet_surface_area = fields.Integer('Booklet Surface Area', help="Page surface booklet (newspaper) format in cm2")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
