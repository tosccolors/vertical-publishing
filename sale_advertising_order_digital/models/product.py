# -*- coding: utf-8 -*-
# Copyright 2018 Magnus ((www.magnus.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api

class ProductCategory(models.Model):
    _inherit = "product.category"

    digital = fields.Boolean('Digital')
    # adv_class_issue_ids = fields.Many2many('advertising.class.issue.matrix', string='Advertising Class Issue Types')
