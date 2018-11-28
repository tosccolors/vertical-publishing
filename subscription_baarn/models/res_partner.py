# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Partner(models.Model):
    _inherit = 'res.partner'

    wijknummer = fields.Char('Wijknummer')
    even_oneven = fields.Char('Even-Oneven')
