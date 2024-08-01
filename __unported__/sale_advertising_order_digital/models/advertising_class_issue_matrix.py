# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AdvertisingClassIssueMatrix(models.Model):
    _name = 'advertising.class.issue.matrix'

    name = fields.Char(string="Advertising Class Issue Matrix", required=True)