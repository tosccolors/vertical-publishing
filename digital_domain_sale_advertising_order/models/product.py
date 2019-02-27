# -*- coding: utf-8 -*-
# Copyright 2018 Magnus ((www.magnus.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api

class productCategory(models.Model):
    _inherit = "product.category"

    digital = fields.Boolean('Digital')
