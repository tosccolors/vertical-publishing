# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2016 Magnus (<http://www.magnus.nl>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models, _

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ad_class_digital = fields.Boolean(compute='_compute_digital', string='Advertising Class Digital')

    matrix_adv_issue_ids = fields.Many2many('sale.advertising.issue', compute='_compute_matrix_issue_pro_type',
                                            string='Advertising Issue Pro Type')

    @api.multi
    @api.depends('ad_class')
    def _compute_digital(self):
        for ol in self:
            ol.ad_class_digital = ol.ad_class and ol.ad_class.digital or False

    @api.multi
    @api.depends('ad_class', 'title', 'title_ids')
    def _compute_matrix_issue_pro_type(self):
        for ol in self:
            ad_class_pro_type = ol.ad_class.adv_pro_type_ids
            categ_pro_type_ids = ad_class_pro_type and ad_class_pro_type.ids or []
            titles = self.title + self.title_ids
            domain =[('parent_id', 'in', titles.ids)]
            if categ_pro_type_ids:
                domain += [('adv_pro_type_id', 'in', ad_class_pro_type.ids)]

            issue_ids = self.env['sale.advertising.issue'].search(domain).ids
            ol.matrix_adv_issue_ids = issue_ids

