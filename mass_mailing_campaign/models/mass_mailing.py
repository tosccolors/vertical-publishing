# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class MassMailingCampaign(models.Model):
    _inherit = "mail.mass_mailing.campaign"

    description = fields.Text(string='Description')
    start_date = fields.Date(string='Start date')
    end_date = fields.Date(string='End date')
    currency_id = fields.Many2one('res.currency', related='user_id.company_id.currency_id', string='Currency')
    budgeted_cost = fields.Float(string='Budgeted costs')
    actual_cost = fields.Float(string='Actual costs')
    budgeted_result = fields.Text(string='Budgeted result')
    actual_result = fields.Text(string='Actual result')
