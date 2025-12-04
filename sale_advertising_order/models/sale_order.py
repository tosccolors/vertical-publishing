# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import logging
from datetime import date
from functools import partial

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang
from odoo.tools.translate import unquote

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = ["sale.order"]

    # backported:
    amount_by_group = fields.Binary(
        string="Tax amount by group",
        compute="_compute_amount_by_group",
        help="type: [(name, amount, base, formated amount, formated base)]",
    )

    # overridden:
    state = fields.Selection(
        selection=[
            ("draft", "Draft Quotation"),
            ("sent", "Quotation Sent"),
            ("submitted", "Submitted for Approval"),
            ("approved1", "Approved by Sales Mgr"),
            ("sale", "Sales Order"),
            ("done", "Locked"),
            ("cancel", "Cancelled"),
        ]
    )

    published_customer = fields.Many2one(
        "res.partner",
        "Advertiser",
        domain=[("parent_id", "=", False), ("is_customer", "=", True)],
    )
    advertising_agency = fields.Many2one(
        "res.partner", domain=[("is_customer", "=", True)]
    )
    nett_nett = fields.Boolean("Netto Netto Deal", default=False)
    customer_contact = fields.Many2one(
        "res.partner", "Contact Person", domain=[("is_customer", "=", True)]
    )
    advertising = fields.Boolean(default=False)

    agency_is_publish = fields.Boolean("Agency is Publishing Customer?", default=False)
    partner_acc_mgr = fields.Many2one(
        related="published_customer.user_id",
        string="Account Manager",
        store=True,
        readonly=True,
    )
    display_discount_to_customer = fields.Boolean(
        "Display Discount", default=False
    )  # TODO: take action later
    material_contact_person_ids = fields.Many2many(
        "res.partner",
        relation="sale_order_material_contact_person_rel",
    )
    # Overridden: SOT
    type_id = fields.Many2one(
        comodel_name="sale.order.type",
        string="Type",
        compute="_compute_sale_type_id",
        store=True,
        readonly=True,
        states={
            "draft": [("readonly", False)],
        },
        ondelete="restrict",
        copy=True,
        check_company=True,
        tracking=True,
    )

    @api.depends()
    def _compute_user_id(self):
        result = super()._compute_user_id()
        for this in self:
            if not this.user_id and self.user_has_groups(
                "sale_advertising_order.group_ads_sales_user"
            ):
                this.user_id = self.env.user
        return result

    @api.depends("partner_id", "company_id")
    def _compute_sale_type_id(self):

        AdsSOT = self.env.ref("sale_advertising_order.ads_sale_type").id
        defSOT = self._context.get("default_type_id", False)

        for record in self:
            sale_type = False

            # Enforce
            if record.advertising or (defSOT == AdsSOT):
                sale_type = AdsSOT

            elif record.type_id:
                sale_type = record.type_id

            # else:
            #     # Specific partner sale type value
            #     sale_type = (
            #         record.partner_id.with_company(record.company_id).sale_type
            #         or record.partner_id.commercial_partner_id.with_company(
            #             record.company_id
            #         ).sale_type
            #     )

            # Default user sale type value
            if not sale_type:
                sale_type = record.default_get(["type_id"]).get("type_id", False)

            # Get first sale type value
            if not sale_type:
                sale_type = record._default_type_id()
            record.type_id = sale_type

    def _ctx_4_action_orders_advertising_smart_button(self):
        "Context to use both active & ref"
        ref = self.env.ref
        active_id = unquote("active_id")

        return {
            "type_id": ref("sale_advertising_order.ads_sale_type").id,
            "default_advertising": True,
            "default_published_customer": active_id,
        }

    def _domain_4_action_orders_advertising_smart_button(self):
        "Domain to use both active & ref"
        ref = self.env.ref
        active_id = unquote("active_id")

        return [
            ("type_id", "=", ref("sale_advertising_order.ads_sale_type").id),
            ("advertising", "=", True),
            ("state", "in", ("sale", "done")),
            "|",
            ("published_customer", "=", active_id),
            ("advertising_agency", "=", active_id),
        ]

    def _ctx_4_sale_action_quotations_new_adv(self):
        "Context to use both active & ref"
        ref = self.env.ref
        active_id = unquote("active_id")

        return {
            "default_advertising": 1,
            "default_type_id": ref("sale_advertising_order.ads_sale_type").id,
            "search_default_opportunity_id": active_id,
            "default_opportunity_id": active_id,
        }

    def _domain_4_sale_action_quotations_new_adv(self):
        "Domain to use both active & ref"
        ref = self.env.ref
        active_id = unquote("active_id")

        return [
            ("type_id", "=", ref("sale_advertising_order.ads_sale_type").id),
            ("opportunity_id", "=", active_id),
            ("advertising", "=", True),
        ]

    def _ctx_4_sale_action_quotations_adv(self):
        "Context to use both active & ref"
        ref = self.env.ref
        active_id = unquote("active_id")

        return {
            "hide_sale": True,
            "default_advertising": 1,
            "default_type_id": ref("sale_advertising_order.ads_sale_type").id,
            "search_default_opportunity_id": [active_id],
            "default_opportunity_id": active_id,
        }

    def _domain_4_sale_action_quotations_adv(self):
        "Domain to use both active & ref"
        ref = self.env.ref
        active_id = unquote("active_id")

        return [
            ("type_id", "=", ref("sale_advertising_order.ads_sale_type").id),
            ("opportunity_id", "=", active_id),
            ("advertising", "=", True),
        ]

    @api.onchange("agency_is_publish")
    def _onchange_agencyIspublish(self):
        if self.agency_is_publish:
            self.published_customer = False

    @api.onchange("advertising_agency")
    def _onchange_advertiser(self):
        if self.advertising_agency:
            self.partner_id = self.advertising_agency

    @api.onchange("partner_id")
    def _onchange_partner2(self):
        if not self.partner_id:
            self.customer_contact = False

        if self.partner_id.type == "contact":
            contact = self.env["res.partner"].search(
                [
                    ("is_company", "=", False),
                    ("type", "=", "contact"),
                    ("parent_id", "=", self.partner_id.id),
                ]
            )
            if len(contact) >= 1:
                contact_id = contact[0]
            else:
                contact_id = False
        else:
            addr = self.partner_id.address_get(["delivery", "invoice"])
            contact_id = addr["contact"]
        if not self.partner_id.is_company and not self.partner_id.parent_id:
            contact_id = self.partner_id

        self.customer_contact = contact_id

        # Existing SAO orderlines
        if self.order_line and self.advertising:
            warning = {
                "title": _("Warning"),
                "message": _(
                    "Changing the Customer can have a change in Agency Discount as a result."
                    "This change will only show after saving the order!"
                    "Before saving the order the order lines and the total amounts may therefor"
                    "show wrong values."
                ),
            }
            return {"warning": warning}

    def _check_archivedIssue(self):
        "Check for any archived Adv Issues used in Order"
        for o in self.filtered("advertising"):
            archived = any(not ol.adv_issue.active for ol in o.order_line)
            if archived:
                raise UserError(
                    _(
                        "Cannot process! One or more lines contains archived "
                        "Advertising Issue in this Order [%s]"
                    )
                    % (o.name)
                )

    def _check_archivedProduct(self):
        "Check for any archived products used in Order"
        for o in self.filtered("advertising"):
            archived = any(not ol.product_id.active for ol in o.order_line)
            if archived:
                raise UserError(
                    _(
                        "Cannot process! One or more lines contains archived Product "
                        "in this Order [%s]"
                    )
                    % (o.name)
                )

    def action_submit(self):
        orders = self.filtered(lambda s: s.state in ["draft"])
        for o in orders:
            if not o.order_line:
                raise UserError(
                    _("You cannot submit a quotation/sales order which has no line.")
                )
        orders._check_archivedIssue()
        orders._check_archivedProduct()
        return self.write({"state": "submitted"})

    # --added deep
    def action_approve1(self):
        orders = self.filtered(lambda s: s.state in ["submitted"])
        orders._check_archivedIssue()
        orders._check_archivedProduct()
        orders.write({"state": "approved1"})
        return True

    # --added deep
    def action_refuse(self):
        orders = self.filtered(
            lambda s: s.state in ["submitted", "sale", "sent", "approved1"]
        )
        orders.write({"state": "draft"})
        return True

    # TODO: move this into SAO Stock
    # def action_cancel(self):
    #     for order in self.filtered(lambda s: s.state == 'sale' and s.advertising):
    #         for line in order.order_line:
    #             line.page_qty_check_unlink()
    #     return super(SaleOrder, self).action_cancel()

    def _action_cancel(self):
        postedInv = self.invoice_ids.filtered(
            lambda inv: inv.state not in ("draft", "cancel")
        )

        if postedInv:
            if len(self.ids) == 1:
                raise UserError(
                    _(
                        "Cannot cancel this Sale Order! "
                        "Invoice has been posted. Please check."
                    )
                )
            else:
                self -= postedInv
        return super(SaleOrder, self)._action_cancel()

    def action_confirm(self):
        adsOrders = self.filtered("advertising")
        adsOrders._check_archivedIssue()
        adsOrders._check_archivedProduct()
        return super(SaleOrder, self).action_confirm()

    @api.model
    def create(self, vals):
        # FIXME: custom Warn block?
        if vals.get("partner_id", False):
            partner = self.env["res.partner"].browse(vals.get("partner_id"))
            if partner.sale_warn == "block":
                raise UserError(_(partner.sale_warn_msg))

        result = super().create(vals)

        result._sao_split_multi_lines()

        return result

    def write(self, vals):
        result = super().write(vals)

        if "state" or "line_ids" in vals:
            self._sao_split_multi_lines()

        return result

    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order.
        This method may be overridden to implement custom invoice generation
        (making sure to call super() to establish a clean extension chain).
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.advertising:
            invoice_vals["published_customer"] = self.published_customer.id

        # Generic
        invoice_vals["customer_contact"] = self.customer_contact.id
        return invoice_vals

    def _get_name_quotation_report(self):
        self.ensure_one()
        ref = self.env.ref
        template = "sale.report_saleorder_document"

        if self.type_id.id == ref("sale_advertising_order.ads_sale_type").id:
            template = "sale_advertising_order.report_saleorder_document_sao"

        return template

    # Backported
    def _compute_amount_by_group(self):
        """ported from v14, for backward compatibility"""

        # Advertising Orders Only:
        for order in self.filtered("advertising"):
            currency = order.currency_id or order.company_id.currency_id
            fmt = partial(
                formatLang,
                self.with_context(lang=order.partner_id.lang).env,
                currency_obj=currency,
            )
            res = {}
            for line in order.order_line._sao_expand_multi_for_report():
                discount = 0.0
                # At this point, it will always be Single Edition:
                nn = True if order.nett_nett or line.nett_nett else False
                if order.partner_id.is_ad_agency and not nn:
                    discount = order.partner_id.agency_discount

                price_reduce = line.actual_unit_price * (1.0 - discount / 100.0)

                taxes = line.tax_id.compute_all(
                    price_reduce,
                    quantity=line.product_uom_qty,
                    product=line.product_id,
                    partner=order.partner_shipping_id,
                )["taxes"]
                for tax in line.tax_id:
                    group = tax.tax_group_id
                    res.setdefault(group, {"amount": 0.0, "base": 0.0})
                    for t in taxes:
                        if t["id"] == tax.id or t["id"] in tax.children_tax_ids.ids:
                            res[group]["amount"] += t["amount"]
                            res[group]["base"] += t["base"]
            res = sorted(res.items(), key=lambda lines: lines[0].sequence)

            # round amount and prevent -0.00
            for group_data in res:
                group_data[1]["amount"] = currency.round(group_data[1]["amount"]) + 0.0
                group_data[1]["base"] = currency.round(group_data[1]["base"]) + 0.0

            order.amount_by_group = [
                (
                    _l[0].name,
                    _l[1]["amount"],
                    _l[1]["base"],
                    fmt(_l[1]["amount"]),
                    fmt(_l[1]["base"]),
                    len(res),
                )
                for _l in res
            ]

    def _find_mail_template(self):
        self.ensure_one()
        if not self.advertising:
            return super(SaleOrder, self).action_quotation_send()

        if self.env.context.get("proforma") or self.state not in ("sale", "done"):
            return self.env.ref(
                "sale_advertising_order.email_template_edi_sale_ads",
                raise_if_not_found=False,
            )
        else:
            return self._get_confirmation_template()

    def _get_confirmation_template(self):
        """Get the mail template sent on SO confirmation (or for confirmed SO's).

        :return: `mail.template` record or None if default template wasn't found
        """
        self.ensure_one()
        if not self.advertising:
            return super(SaleOrder, self)._get_confirmation_template()

        return self.env.ref(
            "sale_advertising_order.mail_template_sale_confirmation_ads",
            raise_if_not_found=False,
        )

    def _sao_split_multi_lines(self):
        """
        Split lines with multi=True if order is in the company's sao_split_line_state
        """
        for this in self:
            if this.state == this.company_id.sao_split_line_state:
                self.env["sale.order.line.create.multi.lines"].with_context(
                    active_model=self._name,
                    active_id=this.id,
                    active_ids=this.ids,
                ).create_multi_lines(raise_exception=False)

    def _sao_get_lines_for_report(self):
        """
        Yield order lines sorted and expanded as per configuration
        """
        SaleOrderLine = self.env["sale.order.line"].browse([])
        order_key = self.sudo().company_id.sao_orderline_order_field_id.name
        if order_key and SaleOrderLine._fields[order_key].type == "date":

            def order_key(x, field_name=order_key):
                return x[field_name] or date.min

        return sum(
            (
                sum(line._sao_expand_multi_for_report(), SaleOrderLine)
                for line in self.order_line
            ),
            SaleOrderLine,
        ).sorted(key=order_key or None)
