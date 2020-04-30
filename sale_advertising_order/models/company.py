# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    call_onchange_for_payers_advertisers = fields.Boolean(
        'Call onchange for Payers & Advertisers',
        help="Set if you want to call onchange function for Payers and Advertisers available in Quotation and Sale forms.")
