# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import logging
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero, float_round

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends(
        "product_uom_qty",
        "order_id.partner_id",
        "order_id.nett_nett",
        "nett_nett",
        "subtotal_before_agency_disc",
        "price_unit",
        "tax_id",
    )
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        super(
            SaleOrderLine, self.filtered(lambda record: not record.advertising)
        )._compute_amount()
        price_precision = (
            self.env["decimal.precision"].precision_get("Product Price") or 4
        )
        discount_precision = (
            self.env["decimal.precision"].precision_get("Discount") or 6
        )

        for line in self.filtered("advertising"):
            nn = True if line.order_id.nett_nett or line.nett_nett else False
            comp_discount = line.computed_discount or 0.0
            price_unit = line.price_unit or 0.0
            unit_price = line.actual_unit_price or 0.0
            qty = line.product_uom_qty or 0.0
            subtotal_bad = line.subtotal_before_agency_disc or 0.0
            if line.order_id.partner_id.is_ad_agency and not nn:
                discount = line.order_id.partner_id.agency_discount
            else:
                discount = 0.0

            # Single Edition:
            if not line.multi_line:
                if float_is_zero(price_unit, price_precision) or float_is_zero(
                    qty, price_precision
                ):
                    unit_price = 0.0
                    comp_discount = 0.0
                else:
                    comp_discount = float_round(
                        (1.0 - subtotal_bad / (price_unit * qty)) * 100.0,
                        discount_precision,
                    )
                    unit_price = float_round(
                        price_unit * (1 - comp_discount / 100), price_precision
                    )

                price = float_round(
                    unit_price * (1 - discount / 100.0), price_precision
                )

                taxes = line.tax_id.compute_all(
                    price,
                    line.order_id.currency_id,
                    line.product_uom_qty,
                    product=line.product_id,
                    partner=line.order_id.partner_id,
                )

                line.update(
                    {
                        "actual_unit_price": unit_price,
                        "price_tax": taxes["total_included"] - taxes["total_excluded"],
                        "price_total": taxes["total_included"],
                        "price_subtotal": taxes["total_excluded"],
                        "computed_discount": comp_discount,
                        "discount": discount,
                    }
                )
            else:
                clp = line.comb_list_price
                if not float_is_zero(clp, discount_precision):
                    comp_discount = float_round(
                        (1.0 - subtotal_bad / clp) * 100.0, discount_precision
                    )
                else:
                    comp_discount = 0.0
                unit_price = 0.0
                price_unit = 0.0

                price = float_round(
                    subtotal_bad * (1 - discount / 100.0), price_precision
                )

                taxes = line.tax_id.compute_all(
                    price,
                    line.order_id.currency_id,
                    quantity=1,
                    product=line.product_template_id,
                    partner=line.order_id.partner_id,
                )

                line.update(
                    {
                        "price_tax": taxes["total_included"] - taxes["total_excluded"],
                        "price_total": taxes["total_included"],
                        "price_subtotal": taxes["total_excluded"],
                        "computed_discount": comp_discount,
                        "actual_unit_price": unit_price,
                        "price_unit": price_unit,
                        "discount": discount,
                    }
                )
        return True

    @api.depends("issue_product_ids.price")
    def _compute_multi_price(self):
        """
        Compute the combined price in the multi_line.
        """
        for order_line in self.filtered("advertising"):
            if order_line.issue_product_ids:
                price_tot = 0.0
                count = 0
                for ipi in order_line.issue_product_ids:
                    price_tot += ipi.price
                    count += 1
                order_line.update(
                    {
                        "comb_list_price": price_tot,
                        "multi_line_number": count,
                    }
                )

    @api.model
    def _get_adClass_domain(self):
        if not self.medium:
            return [
                (
                    "id",
                    "child_of",
                    self.env.ref(
                        "sale_advertising_order.advertising_category",
                        raise_if_not_found=False,
                    ).id,
                )
            ]

        return [("id", "child_of", self.medium.id), ("id", "!=", self.medium.id)]

    @api.depends("product_id")
    def _compute_product_data(self):
        for line in self:
            prod = line.product_id
            line.product_width = prod.width or 0.0
            line.product_height = prod.height or 0.0

    @api.depends("title", "product_template_id")
    def _compute_price_edit(self):
        """
        Compute if price_unit should be editable.
        """
        for line in self.filtered("advertising"):
            line.price_edit = False
            if (
                line.product_template_id
                and line.product_template_id.price_edit
                or line.title.price_edit
            ):
                line.price_edit = True

    @api.depends("adv_issue_ids")
    def _compute_Issuedt(self):
        """Compute the Issue date"""
        for line in self.filtered("advertising"):
            # First advIssue's date
            line.issue_date = (
                line.adv_issue_ids and line.adv_issue_ids[0].issue_date or False
            )

    @api.depends("adv_issue", "ad_class", "from_date")
    def _compute_deadline(self):
        """
        Compute the deadline for this placement.
        """
        user = self.env["res.users"].browse(self.env.uid)
        for line in self.filtered("advertising"):
            line.deadline_passed = False
            line.deadline = False
            line.deadline_offset = False
            if line.date_type == "issue_date":
                line.deadline = line.adv_issue.deadline
            elif line.date_type == "validity" and line.from_date:
                deadline_dt = (
                    datetime.strptime(str(line.from_date), "%Y-%m-%d")
                    + timedelta(hours=3, minutes=30)
                ) - timedelta(days=14)
                line.deadline = deadline_dt
            if line.ad_class:
                if not user.has_group("sale_advertising_order.group_no_deadline_check"):
                    dt_offset = timedelta(hours=line.ad_class.deadline_offset or 0)
                    line.deadline_offset = fields.Datetime.to_string(
                        datetime.now() + dt_offset
                    )
                    if (
                        line.adv_issue
                        and line.adv_issue.deadline
                        and line.adv_issue.issue_date
                    ):
                        dt_deadline = fields.Datetime.from_string(
                            line.adv_issue.deadline
                        )
                        line.deadline = fields.Datetime.to_string(
                            dt_deadline - dt_offset
                        )
                        line.deadline_passed = datetime.now() > (
                            dt_deadline - dt_offset
                        ) and datetime.now() < fields.Datetime.from_string(
                            line.adv_issue.issue_date
                        )

    @api.depends("ad_class", "title_ids")
    def _get_prodTemplate2filter(self):
        "Explicit Domain to filter Product based on Title Attribute"

        AdsSOT = self.env.ref("sale_advertising_order.ads_sale_type").id
        defSOT = self._context.get("default_type_id", False)

        for line in self:
            ptmplIDs = []

            # Check SO type: Ads SOT
            if (line.order_id and line.order_id.type_id.id == AdsSOT) or (
                defSOT == AdsSOT
            ):

                if line.ad_class and line.title_ids:
                    ATpavIds = line.title_ids.mapped("product_attribute_value_id").ids
                    prodTmpls = (
                        self.env["product.product"]
                        .search(
                            [
                                ("sale_ok", "=", True),
                                ("categ_id", "=", line.ad_class.id),
                                (
                                    "product_template_attribute_value_ids."
                                    "product_attribute_value_id",
                                    "in",
                                    ATpavIds,
                                ),
                                ("active", "=", True),
                            ]
                        )
                        .mapped("product_tmpl_id")
                    )

                    # Ensure all Title's PAV combination exists:
                    for pt in prodTmpls:
                        validPAV = (
                            pt.valid_product_template_attribute_line_ids.mapped(
                                "product_template_value_ids"
                            )
                            .mapped("product_attribute_value_id")
                            .ids
                        )
                        if all(i in validPAV for i in ATpavIds):
                            ptmplIDs.append(pt.id)

            line.domain4prod_ids = [(6, 0, ptmplIDs)]

    @api.depends("recurring_id", "product_id")
    def _compute_material_id(self):
        for line in self:
            line.material_id = line.recurring_id.id if line.recurring_id else line.id

    mig_remark = fields.Text("Migration Remark")
    layout_remark = fields.Text("Material Remark")

    advertising = fields.Boolean(related="order_id.advertising", store=True)

    medium = fields.Many2one("product.category")
    title = fields.Many2one(
        "sale.advertising.issue", domain=[("child_ids", "<>", False)]
    )
    title_ids = fields.Many2many(
        "sale.advertising.issue",
        "sale_order_line_adv_issue_title_rel",
        "order_line_id",
        "adv_issue_id",
        "Titles",
    )
    adv_issue = fields.Many2one("sale.advertising.issue", "Advertising Issue")
    adv_issue_ids = fields.Many2many(
        "sale.advertising.issue",
        "sale_order_line_adv_issue_rel",
        "order_line_id",
        "adv_issue_id",
        "Advertising Issues",
    )

    ad_class = fields.Many2one(
        "product.category", "Advertising Class", domain=_get_adClass_domain
    )
    ad_class_tags_ids = fields.Many2many(related="ad_class.tag_ids", string="Tags")

    issue_date = fields.Date(compute="_compute_Issuedt", store=True)
    date_type = fields.Selection(
        related="ad_class.date_type", type="selection", readonly=True
    )
    issue_product_ids = fields.One2many(
        "sale.order.line.issues.products",
        "order_line_id",
        "Adv. Issues with Product Prices",
    )

    deadline_passed = fields.Boolean(compute="_compute_deadline", store=False)
    deadline = fields.Datetime(compute="_compute_deadline", store=False)
    deadline_offset = fields.Datetime(compute="_compute_deadline", store=False)

    product_template_id = fields.Many2one(
        "product.template",
        string="Product",
        domain=[("sale_ok", "=", True)],
        change_default=True,
        ondelete="restrict",
    )
    domain4prod_ids = fields.Many2many(
        "product.template",
        string="Domain for Product Template",
        compute=_get_prodTemplate2filter,
    )

    page_reference = fields.Char(size=32)
    ad_number = fields.Char("External Reference", size=50)
    url_to_material = fields.Char("URL Material")
    from_date = fields.Date("Start of Validity")
    to_date = fields.Date("End of Validity")

    multi_line = fields.Boolean()
    multi_line_number = fields.Integer(
        compute="_compute_multi_price", string="Number of Lines", store=True
    )

    order_partner_id = fields.Many2one(
        related="order_id.partner_id", string="Customer", store=True
    )
    order_advertiser_id = fields.Many2one(
        related="order_id.published_customer", string="Advertising Customer", store=True
    )
    order_agency_id = fields.Many2one(
        related="order_id.advertising_agency", string="Advertising Agency", store=True
    )
    order_pricelist_id = fields.Many2one(
        related="order_id.pricelist_id", string="Pricelist"
    )
    partner_acc_mgr = fields.Many2one(
        related="order_id.partner_acc_mgr",
        store=True,
        string="Account Manager",
        readonly=True,
    )

    price_unit_dummy = fields.Float(
        related="price_unit", string="Unit Price", readonly=True
    )
    actual_unit_price = fields.Float(
        compute="_compute_amount",
        digits="Product Price",
        default=0.0,
        readonly=True,
    )
    comb_list_price = fields.Monetary(
        compute="_compute_multi_price",
        string="Combined_List Price",
        default=0.0,
        store=True,
    )
    computed_discount = fields.Float(string="Discount", digits="Discount", default=0.0)
    subtotal_before_agency_disc = fields.Monetary(string="Subtotal before Commission")
    price_edit = fields.Boolean(compute="_compute_price_edit", string="Price Editable")

    nett_nett = fields.Boolean(string="Netto Netto Line")
    discount_reason_id = fields.Many2one(
        "discount.reason", "Discount Reason", ondelete="restrict"
    )

    proof_number_payer = fields.Boolean(default=False)
    proof_number_payer_id = fields.Many2one("res.partner", "Proof Number Payer ID")
    proof_number_adv_customer = fields.Many2many(
        "res.partner",
        "partner_line_proof_rel",
        "line_id",
        "partner_id",
        string="Proof Number Advertising Customer",
    )
    proof_number_amt_payer = fields.Integer("Proof Number Amount Payer", default=1)
    proof_number_amt_adv_customer = fields.Integer(
        "Proof Number Amount Advertising", default=1
    )

    product_width = fields.Float(
        compute="_compute_product_data", readonly=True, store=True, string="Width"
    )
    product_height = fields.Float(
        compute="_compute_product_data", readonly=True, store=True, string="Height"
    )

    recurring = fields.Boolean("Recurring Advertisement")
    material_id = fields.Integer(
        compute="_compute_material_id", readonly=True, store=True, string="Material ID"
    )
    recurring_id = fields.Many2one(
        "sale.order.line",
        string="Recurring Order Line",
    )
    can_edit = fields.Boolean(compute="_compute_can_edit")
    # emulate webclient's parent variable to be able to reuse embedded form standalone
    parent = fields.Json(compute="_compute_parent")

    def _compute_parent(self):
        for this in self:
            this.parent = {
                field_name: this.order_id._fields[field_name].convert_to_write(
                    this.order_id[field_name],
                    this.order_id,
                )
                for field_name in (
                    "partner_id",
                    "pricelist_id",
                    "company_id",
                    "published_customer",
                )
            }

    @api.model
    def default_get(self, fields_list):
        result = super(SaleOrderLine, self).default_get(fields_list)
        if "customer_contact" in self.env.context:
            result.update(
                {"proof_number_payer_id": self.env.context["customer_contact"]}
            )
            result.update({"proof_number_amt_payer": 1})

        result.update({"proof_number_adv_customer": False})
        result.update({"proof_number_amt_adv_customer": 0})
        return result

    def name_get(self):
        if self._name == "sale.order" or "show_material_ref" not in self.env.context:
            return super().name_get()
        result = []
        for so_line in self.sudo():
            if so_line.material_id:
                name = "%s - %s - %s" % (
                    so_line.order_id.name,
                    so_line.material_id,
                    so_line.product_id.name,
                )

                title_lists = so_line.product_id.mapped(
                    "product_template_attribute_value_ids"
                )
                if title_lists:
                    titles = ", ".join(map(lambda l: l.name, title_lists))
                    name += "(%s)" % titles
                if so_line.order_partner_id.ref:
                    name = "%s (%s)" % (name, so_line.order_partner_id.ref)
            else:
                name = "%s - %s" % (so_line.order_id.name, so_line.product_id.name)
                if so_line.order_partner_id.ref:
                    name = "%s (%s)" % (name, so_line.order_partner_id.ref)
            result.append((so_line.id, name))
        return result

    @api.onchange("medium")
    def onchange_medium(self):
        vals, data = {}, {}
        if not self.advertising:
            return {"value": vals}

        # Unchanged
        if self._origin.medium == self.medium:
            data = {'ad_class': [('id', 'child_of', self.medium.id), ('id', '!=', self.medium.id)]}
            return {'domain': data}

        # Reset
        if not self.medium:
            vals['ad_class'] = False
            data = {'ad_class': []}

        if self.medium:
            child_id = [(x.id != self.medium.id) and x.id for x in self.medium.child_id]

            if len(child_id) == 1:
                vals["ad_class"] = child_id[0]
            else:
                vals["ad_class"] = False
                data = {
                    "ad_class": [
                        ("id", "child_of", self.medium.id),
                        ("id", "!=", self.medium.id),
                    ]
                }
            titles = (
                self.env["sale.advertising.issue"]
                .search(
                    [("parent_id", "=", False), ("medium", "child_of", self.medium.id)]
                )
                .ids
            )
            if titles and len(titles) == 1:
                vals["title"] = titles[0]
                vals["title_ids"] = [(6, 0, titles)]
            else:
                vals["title"] = False
                vals["title_ids"] = [(6, 0, [])]
        return {"value": vals, "domain": data}

    @api.onchange("ad_class")
    def onchange_ad_class(self):
        vals = {}
        if not self.advertising:
            return {"value": vals}

        # Reset
        if self._origin.ad_class != self.ad_class or not self.ad_class:
            self.title = False
            self.title_ids = [(6, 0, [])]
            self.from_date = False
            self.to_date = False

    @api.onchange("title", "title_ids")
    def onchange_title(self):
        vals = {}
        if not self.advertising:
            return {"value": vals}

        # Reset
        if not self.title_ids:
            self.adv_issue = False
            self.adv_issue_ids = [(6, 0, [])]
            self.product_template_id = False

        # Single Title: pre-populate Issue if only one present:
        if len(self.title_ids) == 1 and not self.adv_issue_ids:
            self.title = self.title_ids[0]
            adissue_ids = self.title_ids.child_ids.ids
            if len(adissue_ids) == 1:
                self.adv_issue = adissue_ids[0]
                self.adv_issue_ids = [(6, 0, adissue_ids)]

        elif len(self.title_ids) > 1:  # Multi Titles:
            self.title = False

        # Multi Titles & Multi Editions:
        if self.title_ids and self.adv_issue_ids:
            titles = self.title_ids.ids
            issue_ids = self.adv_issue_ids.ids
            adv_issues = self.env["sale.advertising.issue"].search(
                [("id", "in", issue_ids)]
            )
            issue_parent_ids = [x.parent_id.id for x in adv_issues]
            # for title in titles: # FIXME: Redundant Trigger !! can be removed
            #     if not (title in issue_parent_ids):
            #         raise UserError(_('Not for every selected Title an Issue is selected.'))

        elif self.title_ids and self.issue_product_ids:
            titles = self.title_ids.ids
            adv_issues = self.env["sale.advertising.issue"].search(
                [("id", "in", [x.adv_issue_id.id for x in self.issue_product_ids])]
            )
            issue_parent_ids = [x.parent_id.id for x in adv_issues]
            back = False
            for title in titles:
                if not (title in issue_parent_ids):
                    back = True
                    break
            if back:
                self.adv_issue_ids = [(6, 0, adv_issues.ids)]
                self.issue_product_ids = [(6, 0, [])]
            self.titles_issues_products_price()


    @api.onchange("product_template_id")
    def titles_issues_products_price(self):  # noqa: C901
        vals = {}
        if not self.advertising:
            return {"value": vals}

        # Reset
        if not self.product_template_id:
            self.issue_product_ids = [(6, 0, [])]

        if self.title_ids and (len(self.adv_issue_ids) == 0):
            raise UserError(_("Please select Advertising Issue(s) to proceed further."))

        # issue_parent_ids = [x.parent_id.id for x in self.adv_issue_ids]
        # for title in self.title_ids:
        #     if not (title in issue_parent_ids):
        #         raise UserError(_('Not for every selected Title an Issue is selected. [PT]'))

        if (
            self.product_template_id
            and self.adv_issue_ids
            and len(self.adv_issue_ids) > 1
        ):
            self.product_uom = self.product_template_id.uom_id
            adv_issues = self.env["sale.advertising.issue"].search(
                [("id", "in", self.adv_issue_ids.ids)]
            )
            values = []
            self.issue_product_ids = []  # reset
            product_id = False
            price = 0
            issues_count = len(adv_issues)
            for adv_issue in adv_issues:
                if (
                    adv_issue.parent_id.id in self.title_ids.ids
                    or adv_issue.parent_id.id == self.title.id
                ):
                    value = {}
                    if adv_issue.product_attribute_value_id:
                        pav = adv_issue.product_attribute_value_id.id
                    else:
                        pav = adv_issue.parent_id.product_attribute_value_id.id
                    product_id = self.env["product.product"].search(
                        [
                            ("product_tmpl_id", "=", self.product_template_id.id),
                            (
                                "product_template_attribute_value_ids."
                                "product_attribute_value_id",
                                "=",
                                pav,
                            ),
                        ]
                    )
                    if product_id:
                        self.product_id = product_id.id
                        product = product_id.with_context(
                            lang=self.order_id.partner_id.lang,
                            partner=self.order_id.partner_id.id,
                            quantity=self.product_uom_qty,
                            date=self.order_id.date_order,
                            pricelist=self.order_id.pricelist_id.id,
                            uom=self.product_uom.id,
                        )

                        value["product_id"] = product_id.id
                        value["adv_issue_id"] = adv_issue.id
                        self = self.with_company(self.company_id)
                        price = self._get_display_price()
                        value[
                            "price_unit"
                        ] = product._get_tax_included_unit_price_from_price(
                            price,
                            self.currency_id or self.order_id.currency_id,
                            product_taxes=self.product_id.taxes_id.filtered(
                                lambda tax: tax.company_id == self.env.company
                            ),
                            fiscal_position=self.order_id.fiscal_position_id,
                        )

                        price += value["price_unit"] * self.product_uom_qty
                        values.append((0, 0, value))

            if product_id:
                self.update(
                    {
                        "issue_product_ids": values,
                        # 'product_id': product_id.id, # FIXME
                        "multi_line_number": issues_count,
                        "multi_line": True,
                    }
                )
            self.comb_list_price = price
            self.subtotal_before_agency_disc = price

        # Issue Products
        elif (
            self.product_template_id
            and self.issue_product_ids
            and len(self.issue_product_ids) > 1
        ):
            self.product_uom = self.product_template_id.uom_id
            adv_issues = self.env["sale.advertising.issue"].search(
                [("id", "in", [x.adv_issue_id.id for x in self.issue_product_ids])]
            )
            values = []
            self.issue_product_ids = []  # reset
            product_id = False
            price = 0
            issues_count = len(adv_issues)
            for adv_issue in adv_issues:
                if (
                    adv_issue.parent_id.id in self.title_ids.ids
                    or adv_issue.parent_id.id == self.title.id
                ):
                    value = {}
                    if adv_issue.product_attribute_value_id:
                        pav = adv_issue.product_attribute_value_id.id
                    else:
                        pav = adv_issue.parent_id.product_attribute_value_id.id
                    product_id = self.env["product.product"].search(
                        [
                            ("product_tmpl_id", "=", self.product_template_id.id),
                            (
                                "product_template_attribute_value_ids."
                                "product_attribute_value_id",
                                "=",
                                pav,
                            ),
                        ]
                    )
                    if product_id:
                        self.product_id = product_id.id
                        product = product_id.with_context(
                            lang=self.order_id.partner_id.lang,
                            partner=self.order_id.partner_id.id,
                            quantity=self.product_uom_qty,
                            date=self.order_id.date_order,
                            pricelist=self.order_id.pricelist_id.id,
                            uom=self.product_uom.id,
                        )
                        value["product_id"] = product_id.id
                        value["adv_issue_id"] = adv_issue.id
                        self = self.with_company(self.company_id)
                        price = self._get_display_price()
                        value[
                            "price_unit"
                        ] = product._get_tax_included_unit_price_from_price(
                            price,
                            self.currency_id or self.order_id.currency_id,
                            product_taxes=self.product_id.taxes_id.filtered(
                                lambda tax: tax.company_id == self.env.company
                            ),
                            fiscal_position=self.order_id.fiscal_position_id,
                        )

                        price += value["price_unit"] * self.product_uom_qty
                        values.append((0, 0, value))
            if product_id:
                self.update(
                    {
                        "issue_product_ids": values,
                        # 'product_id': product_id.id,
                        "multi_line_number": issues_count,
                        "multi_line": True,
                    }
                )
            self.comb_list_price = price
            self.subtotal_before_agency_disc = price

        elif self.product_template_id and (
            self.adv_issue or len(self.adv_issue_ids) == 1
        ):
            if self.adv_issue_ids and len(self.adv_issue_ids) == 1:
                self.adv_issue = self.adv_issue_ids.id
            if self.adv_issue.parent_id.id == self.title.id:
                if self.adv_issue.product_attribute_value_id:
                    pav = self.adv_issue.product_attribute_value_id.id
                else:
                    pav = self.adv_issue.parent_id.product_attribute_value_id.id
                product_id = self.env["product.product"].search(
                    [
                        ("product_tmpl_id", "=", self.product_template_id.id),
                        (
                            "product_template_attribute_value_ids."
                            "product_attribute_value_id",
                            "=",
                            pav,
                        ),
                    ]
                )
                if product_id:
                    self.product_id = product_id.id
                    self.update(
                        {
                            "multi_line_number": 1,
                            "multi_line": False,
                        }
                    )
        elif not self.product_template_id: # Fallback
            self.product_id = False


    @api.onchange("product_id")
    def product_id_change(self):
        if not self.advertising:
            return
        self.product_uom_qty = 1
        self.computed_discount = 0.0
        if not self.multi_line:
            self.subtotal_before_agency_disc = self.price_unit
        else:
            self.price_unit = 0.0
            self.subtotal_before_agency_disc = self.comb_list_price
        pt = self.product_template_id
        name = pt.name or ""
        if pt.description_sale:
            name += "\n" + pt.description_sale
        self.name = name

    @api.onchange("date_type", "issue_date")
    def onchange_date_type(self):
        if not self.advertising:
            return

        if self.date_type == "validity":
            self.adv_issue_ids = [(6, 0, [])]

        elif self.date_type == "issue_date":
            self.from_date = self.issue_date
            self.to_date = self.issue_date

    @api.onchange("price_unit")
    def onchange_price_unit(self):
        stprice = 0
        if not self.advertising:
            return
        if self.price_unit > 0 and self.product_uom_qty > 0:
            stprice = self.price_unit * self.product_uom_qty

        self.subtotal_before_agency_disc = stprice

    @api.onchange("computed_discount")
    def onchange_actualcd(self):
        result = {}
        if not self.advertising:
            return {"value": result}
        comp_discount = self.computed_discount
        if comp_discount < 0.0:
            comp_discount = self.computed_discount = 0.000
        if comp_discount > 100.0:
            comp_discount = self.computed_discount = 100.0
        price = self.price_unit or 0.0
        fraction_param = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("sale_advertising_order.fraction")
        )

        if self.multi_line:
            clp = self.comb_list_price or 0.0

            fraction = float(clp) / fraction_param
            subtotal_bad = round(float(clp) * (1.0 - float(comp_discount) / 100.0), 2)

        # Single Edition:
        else:
            gross_price = float(price) * float(self.product_uom_qty)
            fraction = gross_price / fraction_param
            subtotal_bad = round(
                float(gross_price) * (1.0 - float(comp_discount) / 100.0), 2
            )

        if self.subtotal_before_agency_disc == 0 or (
            self.subtotal_before_agency_disc > 0
            and abs(float(subtotal_bad) - float(self.subtotal_before_agency_disc))
            > fraction
        ):
            result["subtotal_before_agency_disc"] = subtotal_bad
        return {"value": result}

    @api.onchange("product_uom_qty", "comb_list_price")
    def onchange_actualqty(self):
        if not self.advertising:
            return

        if not self.multi_line:
            self.subtotal_before_agency_disc = round(
                float(self.price_unit)
                * float(self.product_uom_qty)
                * float(1.0 - self.computed_discount / 100.0),
                2,
            )
        else:
            self.subtotal_before_agency_disc = round(float(self.comb_list_price), 2)

    @api.onchange("adv_issue_ids", "issue_product_ids")
    def onchange_getQty(self):  # noqa: C901
        if not self.advertising:
            return
        ml_qty = 0
        ai = False  # self.adv_issue
        ais = self.adv_issue_ids
        # ds = self.dates  # FIXME: deprecated
        iis = self.issue_product_ids
        user = self.env["res.users"].browse(self.env.uid)

        # consider 1st Issue (as Single Edition) for computation
        if len(ais) == 1:
            ai = self.adv_issue_ids.ids[0]

        # Force assign 1st Issue, always
        if ais:
            self.adv_issue = self.adv_issue_ids.ids[0]
        else:
            self.adv_issue = False

        if ais:
            if len(ais) > 1:
                ml_qty = len(ais)
                ai = False
            else:
                ai = ais.id
                ais = [(6, 0, [])]
                ml_qty = 1
        elif ai:
            ml_qty = 1
        # elif ds:  # FIXME: deprecated
        #     if len(ds) >= 1:
        #         ml_qty = 1
        #         self.product_uom_qty = len(ds)
        elif iis:
            if len(iis) > 1:
                ml_qty = len(iis)
        if ml_qty > 1:
            self.multi_line = True
        else:
            self.multi_line = False
        self.multi_line_number = ml_qty

        # Reset
        if len(self.adv_issue_ids) > 1 and not self.issue_product_ids:
            self.product_template_id = False
        elif not self.adv_issue_ids:
            self.product_template_id = False

        if user.has_group("sale_advertising_order.group_no_deadline_check"):
            return {}
        for adv_issue in self.adv_issue_ids:
            if (
                adv_issue.deadline
                and fields.Datetime.from_string(adv_issue.deadline) < datetime.now()
            ):
                warning = {
                    "title": _("Warning"),
                    "message": _(
                        "You are adding an advertising issue after deadline. "
                        "Are you sure about this?"
                    ),
                }
                return {"warning": warning}

        exRef = ""
        for idx, i in enumerate(self.issue_product_ids):
            if idx == 0:
                exRef = i.ad_number
                continue
            if not i.ad_number:
                i.ad_number = exRef

    @api.onchange("proof_number_adv_customer")
    def onchange_proof_number_adv_customer(self):
        "Migration: from nsm_sale_advertising_order"
        self.proof_number_amt_adv_customer = 1 if self.proof_number_adv_customer else 0

    @api.onchange("proof_number_amt_adv_customer")
    def onchange_proof_number_amt_adv_customer(self):
        "Migration: from nsm_sale_advertising_order"
        if self.proof_number_amt_adv_customer <= 0:
            self.proof_number_adv_customer = False

    @api.onchange("proof_number_amt_payer")
    def onchange_proof_number_amt_payer(self):
        "Migration: from nsm_sale_advertising_order"
        if self.proof_number_amt_payer < 1:
            self.proof_number_payer_id = False

    @api.onchange("proof_number_payer_id")
    def onchange_proof_number_payer_id(self):
        "Migration: from nsm_sale_advertising_order"
        self.proof_number_amt_payer = 1 if self.proof_number_payer_id else 0

    # reset material_id as original ID
    @api.onchange("recurring")
    def _onchange_recurring(self):
        if not self.recurring and self.recurring_id:
            self.recurring_id = False

    def cancel_line(self):
        "Allow cancel of SOL by resetting qty to Zero"
        self.ensure_one()
        if self.invoice_status != "to invoice":
            return
        self.product_uom_qty = 0

    @api.constrains("title_ids", "adv_issue_ids")
    def _validate_AdvIssues(self):
        "Check if Issues for every Titles"
        for case in self:
            if len(case.title_ids.ids) > 0 and len(case.adv_issue_ids.ids) > 0:
                issue_parent_ids = [x.parent_id.id for x in case.adv_issue_ids]
                for title in case.title_ids.ids:
                    if not (title in issue_parent_ids):
                        raise ValidationError(
                            _("Not for every selected Title an Issue is selected. [%s]")
                            % (case.name)
                        )

    @api.onchange("from_date", "to_date")
    def _check_validity_dates(
        self,
    ):
        "Check correctness of date"
        if self.from_date and self.to_date:
            if self.from_date > self.to_date:
                raise UserError(
                    _(
                        "Please make sure that the start date is smaller than or "
                        "equal to the end date."
                    )
                )

    @api.constrains("from_date", "to_date")
    def _check_start_end_dates(self):
        "Check correctness of date"
        for case in self:
            if case.from_date and case.to_date:
                if case.from_date > case.to_date:
                    raise ValidationError(
                        _(
                            "Please make sure that the start date is smaller than or "
                            "equal to the end date '%s'."
                        )
                        % (case.name)
                    )

    def _convert_to_tax_base_line_dict(self):
        """
        Convert the current record to a dictionary in order to use the generic taxes
        computation method defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()

        if not self.advertising:
            return super(SaleOrderLine, self)._convert_to_tax_base_line_dict()

        return self.env["account.tax"]._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.actual_unit_price
            if not self.multi_line
            else self.price_subtotal,
            quantity=self.product_uom_qty if not self.multi_line else 1,
            discount=self.discount,
            price_subtotal=self.price_subtotal,
        )

    def deadline_check(self):
        self.ensure_one()
        user = self.env["res.users"].browse(self.env.uid)
        issue_date = (
            (self.issue_date or self.adv_issue_ids[0].issue_date)
            if len(self.adv_issue_ids) == 1
            else self.issue_date
        )
        if issue_date and fields.Datetime.from_string(issue_date) <= datetime.now():
            return False
        elif (
            not user.has_group("sale_advertising_order.group_no_deadline_check")
            and self.deadline
        ):
            if fields.Datetime.from_string(self.deadline) < datetime.now():
                raise UserError(
                    _("The deadline %s for this Category/Advertising Issue has passed.")
                    % (self.deadline)
                )
        return True

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)

        if self.advertising:
            res["analytic_distribution"] = {self.adv_issue.analytic_account_id.id: 100}
            res["price_unit"] = self.actual_unit_price
            res["ad_number"] = self.ad_number
            res["computed_discount"] = self.computed_discount
            res["from_date"] = self.from_date
            res["to_date"] = self.to_date
            res["issue_date"] = self.issue_date

        # support account_invoice_start_end_dates without depending on it
        move_line_fields = self.env["account.move.line"]._fields
        if "end_date" in move_line_fields and "start_date" in move_line_fields:
            res.update(
                end_date=self.to_date,
                start_date=self.from_date,
            )
        res["so_line_id"] = self.id

        return res

    def _sao_expand_multi_for_report(self):
        """
        Yield lines or new() object with split values depending on company configuration
        """
        MultiLineWizard = self.env["sale.order.line.create.multi.lines"]
        for this in self:
            if (
                not this.multi_line
                or not this.order_id.company_id.sao_split_lines_in_report
            ):
                yield this
            else:
                for issue_product in this.issue_product_ids:
                    split_line_default = MultiLineWizard._prepare_default_vals_copy(
                        this, issue_product
                    )
                    new_record = self.new(this.copy_data(default=split_line_default)[0])
                    new_record._compute_amount()
                    yield new_record

    def _compute_can_edit(self):
        for this in self:
            this.can_edit = self.env.user.has_groups(
                "sale_advertising_order.group_ads_traffic_user"
            ) and this.invoice_status not in ("invoiced", "upselling")
