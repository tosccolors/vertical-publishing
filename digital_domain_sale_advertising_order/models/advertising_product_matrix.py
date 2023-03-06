# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AdvertisingProductMatrix(models.Model):
    _name = 'advertising.product.matrix'

    name = fields.Char(string="Advertising Product Type", required=True)