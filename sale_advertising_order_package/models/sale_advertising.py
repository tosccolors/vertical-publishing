# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = ["sale.order"]

    package = fields.Boolean(string='Package', index=True, copy=False)
    package_description = fields.Char(string='Package Description', copy=False)


class SaleOrderLine(models.Model):
    _inherit = ["sale.order.line"]

    package = fields.Boolean(related='order_id.package', string='Package', readonly=True, store=True)