# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = ["sale.order"]

    seq_adgr_orde_id = fields.Integer(string="Ad4all Order Code", copy=False)
    mig_adgr_orde_id = fields.Integer(string="Migrated Sale Order ID", copy=False)
    order_ad4all_allow = fields.Boolean(
        compute="_compute_order_ad4all_allow",
        default=False,
        store=True,
        string="Allow to Ad4all",
        copy=False,
    )

    @api.depends("order_line.line_ad4all_allow")
    def _compute_order_ad4all_allow(self):
        for order in self:
            order.order_ad4all_allow = False
            for line in order.order_line:
                if line.line_ad4all_allow:
                    order.order_ad4all_allow = True
                    break

    def action_ad4all(self, arg, xml=False):
        for order in self.filtered(lambda s: s.state == "sale" and s.advertising):
            for line in order.order_line:
                res = line.transfer_order_to_ad4all(arg)
                if res.status != "na":
                    line.with_context(no_checks=True).write({"ad4all_tbu": True})
                    res.wsdl_content(xml=xml)
        return True

    def action_confirm(self):
        res = super().action_confirm()
        self.action_ad4all("update", False)
        return res

    def action_submit(self):
        orders = self.filtered(lambda s: s.state in ["draft"])
        for o in orders:
            if o.order_line.filtered(lambda s: s.line_ad4all_allow):
                if not o.material_contact_person:
                    raise UserError(
                        _(
                            "You have to fill in a material contact person.\n"
                            "Be aware, that the contact must have email and phone filled in."
                        )
                    )
        return super().action_submit()

    def action_approve1(self):
        res = super().action_approve1()
        orders = self.filtered(lambda s: s.state in ["approved1"])
        for order in orders:
            olines = []
            for line in order.order_line:
                if line.multi_line:
                    olines.append(line.id)
            if olines:
                line_ids = self.env[
                    "sale.order.line.create.multi.lines"
                ].create_multi_from_order_lines(orderlines=olines)
                newlines = self.env["sale.order.line"].browse(line_ids)
                for newline in newlines:
                    if newline.deadline_check():
                        newline.page_qty_check_create()
        return res

    def write(self, vals):
        res = super().write(vals)
        for order in self.filtered(lambda s: s.advertising and s.state == "sale"):
            if (
                ("published_customer" in vals)
                or ("partner_id" in vals)
                or ("customer_contact" in vals)
                or ("advertising_agency" in vals)
                or ("order_line" in vals)
            ):
                order.action_ad4all("update", False)
        return res

    def action_cancel(self):
        self.action_ad4all("delete", False)

        return super().action_cancel()

    def action_ad4all_xml(self):
        self.action_ad4all("update", True)

    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        for index, item in enumerate(args):
            if "seq_adgr_orde_id" in item and isinstance(args[index][2], str):
                vals = args[index][2].replace(",", "")
                args[index][2] = vals
        return super()._search(
            args, offset, limit, order, count=count, access_rights_uid=access_rights_uid
        )
