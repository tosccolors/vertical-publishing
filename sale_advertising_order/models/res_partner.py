# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.tools.safe_eval import const_eval


class Partner(models.Model):
    _inherit = "res.partner"

    sao_order_count = fields.Integer(compute="_compute_sao_order_count")

    def _compute_sao_order_count(self):
        sao_type = self._sao_type()
        SaleOrder = self.env["sale.order"]
        for this in self:
            this.sao_order_count = SaleOrder.search_count(
                [
                    ("partner_id", "child_of", this.id),
                    ("type_id", "=", sao_type.id),
                ]
            )
    def _sao_type(self):
        return self.env.ref("sale_advertising_order.ads_sale_type")

    def _compute_sale_order_count(self):
        super()._compute_sale_order_count()
        for this in self:
            this.sale_order_count -= this.sao_order_count

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
            ("partner_id", "child_of", self.ids),
            ("type_id", "=", sao_type.id),
        ]
        result["context"] = dict(
            const_eval(result["context"] or "{}"), default_partner_id=self[:1].id
        )
        return result
