# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class AccountInvoice(models.Model):
	_inherit = ['account.move']

	modify_refund_created = fields.Boolean(string="Modified refund created using this invoice")


