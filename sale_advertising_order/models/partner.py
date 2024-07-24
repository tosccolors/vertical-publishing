# -*- coding: utf-8 -*-
# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from bs4 import BeautifulSoup


class Partner(models.Model):
    _inherit = 'res.partner'

    agency_discount = fields.Float('Agency Discount (%)', digits=(16, 2), default=0.0)
    is_ad_agency = fields.Boolean('Agency', default=False)

    @api.model
    def default_get(self, fields):
        """Function gets default values."""
        res = super().default_get(fields)
        res.update({"type": "contact"})
        return res
