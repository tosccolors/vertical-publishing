# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.multi
    def _create_invoice(self, order, so_line, amount):
        invoice = super(SaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)
        if order.customer_contact:
            invoice.customer_contact = order.customer_contact.id
        return invoice