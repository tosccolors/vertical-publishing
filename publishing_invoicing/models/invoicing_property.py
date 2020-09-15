# -*- coding: utf-8 -*-

from odoo import models, fields, api

class nsm_invoicing_property(models.Model):
    _name = 'invoicing.property'

    name = fields.Char(string="Invoicing Property")
    
    group_invoice_lines_per_period = fields.Boolean(string="Group invoice lines per period")
    group_invoice_lines_per_title = fields.Boolean(string="Group invoice lines per title")
    group_invoice_lines_per_po_number = fields.Boolean(string="Group invoice lines per PO number")

    pre_pay_publishing_add = fields.Boolean(string="Pre-pay publishing advertisements")
    pre_pay_online_add = fields.Boolean(string="Pre-pay online advertisements")
