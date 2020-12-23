# -*- coding: utf-8 -*-
# Copyright 2018 Eficent Business and IT Consulting Services, S.L.

from odoo import fields, models


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    call_onchange_for_payers_advertisers = fields.Boolean(
        'Call onchange for Payers & Advertisers', related='company_id.call_onchange_for_payers_advertisers',
        help="Set if you want to call onchange function for Payers and Advertisers available in Quotation and Sale forms.")
