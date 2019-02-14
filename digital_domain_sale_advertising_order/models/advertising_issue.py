# -*- coding: utf-8 -*-
# Copyright 2018 Magnus ((www.magnus.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api

class AdvertisingIssue(models.Model):
    _inherit = "sale.advertising.issue"

    digital = fields.Boolean('Digital')