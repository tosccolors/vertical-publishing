# -*- coding: utf-8 -*-
from odoo import tools, api, fields, models, _

class Partner(models.Model):
    _inherit = ['res.partner']

    invoice_frequency = fields.Selection([('weekly','Weekly'),('monthly','Monthly')], string = 'Invoicing Frequency')
    last_invoice_sent_date = fields.Date(string="Last Invoice Sent Date")

Partner()