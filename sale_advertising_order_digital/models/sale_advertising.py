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

import logging
_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ad_class_digital = fields.Boolean(compute='_compute_digital', string='Advertising Class Digital', default=False, store=True)

    adv_class_issue_ids = fields.Many2many('sale.advertising.issue', compute='_compute_class_issue_matrix',
                                            string='Advertising Class Issue Link')


    @api.depends('ad_class')
    def _compute_digital(self):
        for ol in self:
            ol.ad_class_digital = ol.ad_class and ol.ad_class.digital or False


    @api.depends('ad_class', 'title', 'title_ids')
    def _compute_class_issue_matrix(self):
        for ol in self:
            adv_class_issue_ids = ol.ad_class.adv_class_issue_ids
            class_issue_ids = adv_class_issue_ids and adv_class_issue_ids.ids or []
            titles = ol.title + ol.title_ids
            domain =[('parent_id', 'in', titles.ids)]
            if class_issue_ids:
                domain += [('adv_class_issue_id', 'in', adv_class_issue_ids.ids)]

            ol.adv_class_issue_ids = self.env['sale.advertising.issue'].search(domain).ids


    @api.model
    def _get_domain4Issues(self):
        result = super()._get_domain4Issues()
        domain = [('digital','=', self.ad_class_digital)]

        if self.adv_class_issue_ids:
            domain = [('id', 'in', self.adv_class_issue_ids.ids)]

        return domain + result