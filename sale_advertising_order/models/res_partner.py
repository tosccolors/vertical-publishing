# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.tools.safe_eval import const_eval


class Partner(models.Model):
    _inherit = "res.partner"

    agency_discount = fields.Float("Agency Discount (%)", digits=(16, 2), default=0.0)
    is_ad_agency = fields.Boolean("Agency", default=False)
    sao_order_count = fields.Integer(compute="_compute_sao_order_count")

    def _compute_sao_order_count(self):
        sao_type = self._sao_type()
        SaleOrder = self.env["sale.order"]
        for this in self:
            this.sao_order_count = SaleOrder.search_count(
                [
                    ("partner_id", "=", this.id),
                    ("type_id", "=", sao_type.id),
                ]
            )

    @api.model
    def default_get(self, fields):
        """Function gets default values."""
        res = super().default_get(fields)
        res.update({"type": "contact"})
        return res

    def _sao_type(self):
        return self.env.ref("sale_advertising_order.ads_sale_type")

    @api.model
    def _get_sale_order_domain_count(self):
        """
        Differentiate between "normal" SOs and advertising orders
        """
        return super()._get_sale_order_domain_count() + [
            ("type_id", "!=", self._sao_type().id)
        ]

    def action_view_sale_order(self):
        """
        Differentiate between "normal" SOs and advertising orders
        """
        result = super().action_view_sale_order()
        sao_type = self._sao_type()
        result["domain"] += [("type_id", "!=", sao_type.id)]
        return result

    def action_view_sao_order(self):
        """
        Show only advertising orders
        """
        result = self.env["ir.actions.act_window"]._for_xml_id(
            "sale_advertising_order.action_orders_advertising"
        )
        sao_type = self._sao_type()
        result["domain"] = [
            ("partner_id", "in", self.ids),
            ("type_id", "=", sao_type.id),
        ]
        result["context"] = dict(
            const_eval(result["context"] or "{}"), default_partner_id=self[:1].id
        )
        return result
