
from odoo import api, fields, models, _

class Partner(models.Model):
    _inherit = 'res.partner'

    invoicing_property_id = fields.Many2one('invoicing.property', string="Invoicing Property")
