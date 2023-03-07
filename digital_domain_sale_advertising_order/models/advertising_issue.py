# -*- coding: utf-8 -*-
# Copyright 2018 Magnus ((www.magnus.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api

class AdvertisingIssue(models.Model):
    _inherit = "sale.advertising.issue"

    digital = fields.Boolean('Digital')
    adv_pro_type_id = fields.Many2one('advertising.product.matrix', string='Advertising Product Types')

    @api.onchange('medium')
    def onchange_medium(self):
        data = {}
        matrix_ids = []
        for categ in self.medium:
            matrix_ids += categ.adv_pro_type_ids.ids
        if matrix_ids:
            data = {'adv_pro_type_id': [('id', 'in', matrix_ids)]}
        return {'domain': data}
