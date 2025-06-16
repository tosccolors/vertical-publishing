from odoo import _, models
from odoo.exceptions import UserError


class SaleOrderAd4all(models.TransientModel):
    """
    This wizard will update all the selected orders in Ad4all
    """

    _name = "sale.order.ad4all"
    _description = "Update the selected sale orders in Ad4all"

    def sale_order_update_ad4all(self):
        context = dict(self._context or {})
        active_ids = context.get("active_ids", []) or []
        active_model = context.get("active_model")
        orders = self.env[active_model].browse(active_ids)
        for order in orders:
            if order.state not in ("sale",) or not order.advertising:
                raise UserError(
                    _(
                        "Selected order(s) cannot be updated to Ad4all as "
                        "they are not in 'Sale', or 'Done' state"
                        " or they are not Advertising Orders."
                    )
                )
            order.action_ad4all("update", False)
        return {"type": "ir.actions.act_window_close"}
