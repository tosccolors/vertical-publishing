import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from unidecode import unidecode

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ad4all_sent = fields.Boolean("Order Line sent to Ad4all", copy=False, default=False)
    line_ad4all_allow = fields.Boolean(
        compute="_compute_line_ad4all_allow",
        string="Ad4all Allowed",
        store=True,
        copy=False,
    )
    no_copy_chase = fields.Boolean("No Copy Chasing", default=False)

    date_sent_ad4all = fields.Datetime(
        "Datetime Sent to Ad4all",
        index=True,
        copy=False,
        help="Datetime on which sales order is sent to Ad4all.",
    )

    ad4all_write_after_sent = fields.Boolean(
        compute="_compute_ad4all_write_after_sent",
        string="Written after transferred to Ad4all",
        default=False,
        store=True,
        copy=False,
    )
    ad4all_tbu = fields.Boolean(
        string="Ad4all to be updated", default=False, copy=False
    )
    publog_id = fields.Many2one("sale.order.line.ad4all", copy=False)
    advert_id = fields.Integer(
        compute="_compute_advert_id", store=True, string="Line ID"
    )
    seq_advert_id = fields.Integer(
        string="Seq Line ID",
        copy=False,
    )
    seq_mat_id = fields.Integer(string="Seq Material ID", copy=False)

    @api.depends("ad_class", "adv_issue_ids.medium")
    def _compute_line_ad4all_allow(self):
        for line in self.filtered("advertising"):
            res = False
            if (
                len(line.adv_issue_ids) == 1
                and line.ad_class.ad4all
                and line.adv_issue_ids.medium.filtered(lambda m: m.ad4all)
            ):
                res = True
            line.line_ad4all_allow = res

    @api.depends("date_sent_ad4all", "write_date")
    def _compute_ad4all_write_after_sent(self):
        for order in self:
            if order.date_sent_ad4all:
                order.ad4all_write_after_sent = (
                    order.date_sent_ad4all < order.write_date
                )

    @api.depends("publog_id", "line_ad4all_allow", "seq_advert_id")
    def _compute_advert_id(self):
        for line in self:
            AdvertID = False

            if line.advertising:
                # Last sent Line ID
                if line.publog_id:
                    AdvertID = line.publog_id.advert_id
                else:
                    AdvertID = line.seq_advert_id

            line.advert_id = AdvertID

    def transfer_order_to_ad4all(self, arg):
        self.ensure_one()
        order = self.order_id

        del_param = False
        if (
            int(self.product_uom_qty) == 0
            or arg == "delete"
            or (self.ad4all_sent and not self.line_ad4all_allow)
        ):
            del_param = True

        # Check: valid Adlines
        if not self.line_ad4all_allow and not self.ad4all_sent:
            vals = {
                "sale_line_id": self.id,
                "adgr_orde_id": order.id,
                "order_name": order.name,
                "status": "na",
                "cancelled": del_param,
                "advert_id": self.advert_id,
                "mat_id": self.material_id,
                "not_applicable": True,
                "reference": "This order line is not eligible to be sent to Ad4all.",
            }
            res = self.env["sale.order.line.ad4all"].sudo().create(vals)

        # Check if already cancelled:
        elif del_param and self.publog_id.cancelled:
            vals = {
                "sale_line_id": self.id,
                "adgr_orde_id": order.id,
                "order_name": order.name,
                "status": "na",
                "cancelled": del_param,
                "advert_id": self.advert_id,
                "mat_id": self.material_id,
                "not_applicable": True,
                "reference": "This order line has been already cancelled.",
            }
            res = self.env["sale.order.line.ad4all"].sudo().create(vals)

        # If Qty is 0 Initially:
        elif del_param and not self.ad4all_sent:
            vals = {
                "sale_line_id": self.id,
                "adgr_orde_id": order.id,
                "order_name": order.name,
                "status": "na",
                "cancelled": del_param,
                "advert_id": self.advert_id,
                "mat_id": self.material_id,
                "not_applicable": True,
                "reference": "This order line with Zero Qty cannot be sent.",
            }
            res = self.env["sale.order.line.ad4all"].sudo().create(vals)

        else:
            if not order.material_contact_person:
                raise UserError(
                    _(
                        "You have to fill in a material contact person.\n"
                        "Be aware, that the contact must have email and phone filled in."
                    )
                )
            lang_code = "NL"
            if order.published_customer:
                partner = order.published_customer
                if partner.lang:
                    lang_code = partner.lang.split("_")[1]
                    if lang_code == "US":
                        lang_code = "EN"

            vals = {
                "sale_line_id": self.id,
                "adgr_orde_id": order.id,
                "order_name": order.name or "",
                "reference": "Subject:"
                + unidecode(order.client_order_ref or "")
                + "\n"
                + "Order Nr.:"
                + unidecode(order.name or ""),
                "customer_id": str(order.published_customer.id),
                "customer_name": order.published_customer.name,
                "customer_address_street": order.published_customer.street or "",
                "customer_address_zip": order.published_customer.zip or "",
                "customer_address_city": order.published_customer.city or "",
                "customer_address_phone": order.published_customer.phone or "",
                "customer_contacts_contact_id": str(order.material_contact_person.id),
                "customer_contacts_contact_name": order.material_contact_person.name
                or False,
                "customer_contacts_contact_email": order.material_contact_person.email
                or False,
                "customer_contacts_contact_phone": order.material_contact_person.phone
                or order.material_contact_person.mobile
                or False,
                "customer_contacts_contact_type": "",
                "customer_contacts_contact_language": "NL",
                "media_agency_contacts_contact2_language": lang_code,
                "status": "draft",
                "paper_pub_date": self.issue_date or self.from_date or False,
                "paper_deadline": self.adv_issue.deadline or self.deadline or False,
                "placement_notice": unidecode(self.layout_remark or ""),
                "placement_description": unidecode(self.product_id.name or "")
                + "\n"
                + unidecode(self.name or ""),
                "placement_position": unidecode(self.page_reference or ""),
            }

            adportal_required_dict = {
                "customer_id": "Advertiser Reference",
                "customer_address_street": "Advertiser Street",
                "customer_address_zip": "Advertiser Zip",
                "customer_address_city": "Advertiser City",
                "customer_address_phone": "Advertiser Phone",
                "customer_contacts_contact_id": "Material Contact Person Reference",
                "customer_contacts_contact_email": "Material Contact Person Email",
                "customer_contacts_contact_phone": "Material Contact Person Phone or "
                "Material Contact Person Mobile",
                "paper_pub_date": "Issue Date or From Date",
                "paper_deadline": "Issue Deadline Or Line Deadline",
            }

            for key, value in vals.items():
                if value is False:
                    raise UserError(
                        _("AdPortal required field %s is missing")
                        % (adportal_required_dict.get(key, key))
                    )

            vals.update(
                {
                    "sale_line_id": self.id,
                    "adgr_orde_id": order.id,
                    "cancelled": del_param,
                    "herplaats": self.recurring,
                    "materialtype": self.ad_class.ad4all_material_type,
                    "sales": unidecode(
                        order.user_id and order.user_id.name or self.env.user.name
                    ),
                    "sales_mail": order.user_id.email,
                    "reminder": not self.no_copy_chase,
                    "format_id": self.product_template_id.name,
                    "format_height": self.product_id.height or False,
                    "format_trim_height": self.product_id.height or False,
                    "format_width": self.product_id.width or False,
                    "format_trim_width": self.product_id.width or False,
                    "format_spread": self.product_template_id.spread,
                    "paper_id": self.title_ids[0].code,
                    "paper_name": self.title_ids[0].name,
                    "paper_issuenumber": self.adv_issue_ids[0].name,
                    "placement_adclass": self.ad_class.name,
                }
            )

            seq_advert_id = self.seq_advert_id

            # check previous interface is cancelled or not,
            # if cancelled set sequence to generate
            re_confirmed_order = self.publog_id.cancelled if self.publog_id else False
            if re_confirmed_order:
                seq_advert_id = 0

            if not seq_advert_id:
                seq_advert_id = self.env["ir.sequence"].next_by_code("ad4all.advert.id")
                self.seq_advert_id = seq_advert_id
                self.advert_id = seq_advert_id

            vals.update({"advert_id": self.advert_id})
            vals.update({"mat_id": self.material_id})

            if order.mig_adgr_orde_id:
                vals.update({"seq_adgr_orde_id": order.mig_adgr_orde_id})
            else:
                seq_adgr_orde_id = order.seq_adgr_orde_id
                if not order.seq_adgr_orde_id:
                    seq_adgr_orde_id = self.env["ir.sequence"].next_by_code(
                        "ad4all.adgr.orde.id"
                    )
                    order.seq_adgr_orde_id = seq_adgr_orde_id
                vals.update({"seq_adgr_orde_id": seq_adgr_orde_id})

            if order.advertising_agency:
                vals.update(
                    {
                        "media_agency_code": str(order.advertising_agency.id),
                        "media_agency_name": order.advertising_agency.name,
                        "media_agency_email": order.advertising_agency.email,
                        "media_agency_phone": order.advertising_agency.phone
                        or order.advertising_agency.mobile,
                    }
                )
            res = self.env["sale.order.line.ad4all"].sudo().create(vals)
        return res

    def action_ad4all(self, arg, xml=False):
        order = self.order_id
        if order.state == "sale" and order.advertising:
            res = self.transfer_order_to_ad4all(arg)
            if res.status != "na":
                self.with_context(no_checks=True).write({"ad4all_tbu": True})
                res.wsdl_content(xml=xml)
        return True

    def action_ad4all_xml(self):
        self.action_ad4all("update", True)

    def cancel_line(self):
        "Allow cancel of SOL by resetting qty to Zero"
        result = super().cancel_line()
        if self.ad4all_sent or self.publog_id:
            self.action_ad4all("delete", False)
        return result

    @api.model
    def create(self, vals):
        # FIXME: to generate Seq only for Ads Lines?
        seq_advert_id = self.env["ir.sequence"].next_by_code("ad4all.advert.id")
        vals["seq_advert_id"] = seq_advert_id
        seq_mat_id = self.env["ir.sequence"].next_by_code("ad4all.mat.id")
        vals["seq_mat_id"] = seq_mat_id
        return super(SaleOrderLine, self).create(vals)

    def unlink(self):
        if self.filtered("ad4all_sent"):
            raise UserError(
                _(
                    "You can not remove a sale order line after it has been"
                    " sent to Ad4all.\n"
                    "Discard changes and try setting the quantity to 0."
                )
            )
        return super(SaleOrderLine, self).unlink()

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
                name = "%s (%s)" % (name, so_line.order_partner_id.id)
            else:
                name = "%s - %s" % (so_line.order_id.name, so_line.product_id.name)
                name = "%s (%s)" % (name, so_line.order_partner_id.id)
            result.append((so_line.id, name))
        return result
