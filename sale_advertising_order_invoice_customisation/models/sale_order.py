# -*- encoding: utf-8 -*-

from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.customer_contact:
            invoice_vals['customer_contact'] = self.customer_contact.id
        return invoice_vals