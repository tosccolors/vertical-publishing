
from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    invoicing_property_id = fields.Many2one('invoicing.property',string="Invoicing Property")

    @api.multi
    @api.onchange('partner_id')
    def update_invoicing_property(self):
        for line in self:
            if line.partner_id:
                if line.partner_id.invoicing_property_id:
                    line.invoicing_property_id = line.partner_id.invoicing_property_id.id