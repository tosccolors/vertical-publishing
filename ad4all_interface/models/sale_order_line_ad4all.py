import datetime
import logging

import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrderLineAd4all(models.Model):
    _name = "sale.order.line.ad4all"
    _description = "Sale Order Line Ad4all"
    _rec_name = "sale_line_id"
    _order = "create_date desc"

    sale_line_id = fields.Many2one(
        "sale.order.line",
        string="Order Line Reference",
        ondelete="cascade",
        required=False,
        index=True,
        copy=False,
    )
    not_applicable = fields.Boolean(default=False)
    no_copy_chase = fields.Boolean(
        related="sale_line_id.no_copy_chase",
    )
    ad4all_response = fields.Char("Ad4all Response")
    json_message = fields.Text("XML message")
    reply_message = fields.Text("Reply message")
    portal = fields.Char(string="Ad4all Portal")
    deliverer = fields.Char(string="Ad4all Deliverer")
    advert_id = fields.Integer(string="Line ID")
    mat_id = fields.Integer(string="Material ID")
    adgr_orde_id = fields.Many2one("sale.order", string="Sale Order ID")
    seq_adgr_orde_id = fields.Integer(string="Ad4all Order Code")
    adkind = fields.Char(string="Advertising Type", default="PRINT")
    adstatus = fields.Char(string="Advertising Status", default="Nieuw")
    cancelled = fields.Boolean()
    herplaats = fields.Boolean(string="Herplaatsing")
    materialtype = fields.Char(string="Material Type", default="PRINT")
    format_id = fields.Char(string="Product ID")
    format_height = fields.Integer(string="Page Height mm")
    format_width = fields.Integer(string="Page Width mm")
    format_trim_height = fields.Integer(string="Print Height mm")
    format_trim_width = fields.Integer(string="Print Width mm")
    format_spread = fields.Boolean(string="Spread")
    paper_pub_date = fields.Date(string="Issue Date")
    paper_deadline = fields.Date(string="Deadline Date")
    paper_id = fields.Char(string="Title Id")
    paper_name = fields.Char(string="Advertising Title Name", size=64)
    paper_issuenumber = fields.Char(string="Advertising Issue Name", size=64)
    placement_adclass = fields.Char(string="Advertising Class Name", size=64)
    placement_description = fields.Char(string="Advertising Description", size=254)
    placement_notice = fields.Char(string="Material Remarks")
    placement_position = fields.Char(string="Mapping Remarks")
    sales = fields.Char(string="User Name", size=32)
    sales_mail = fields.Char(string="User Email", size=64)
    reminder = fields.Boolean()
    customer_id = fields.Char(string="Advertiser Number")
    customer_name = fields.Char(string="Advertiser Name", size=64)

    customer_contacts = fields.Json(string="Customer Contacts storage")
    customer_contacts_display = fields.Html(
        compute="_compute_customer_contacts_display", string="Customer Contacts"
    )
    customer_address_street = fields.Char(string="Advertiser Address Street", size=64)
    customer_address_zip = fields.Char(string="Advertiser Address Zip Code", size=32)
    customer_address_city = fields.Char(string="Advertiser Address City", size=64)
    customer_address_phone = fields.Char(string="Advertiser Address Phone", size=64)
    agency = fields.Boolean()
    media_agency_code = fields.Char(string="Agency Number", size=32)
    media_agency_name = fields.Char(string="Agency Name", size=64)
    media_agency_email = fields.Char(string="Agency Email", size=64)
    media_agency_phone = fields.Char(string="Agency Email", size=64)
    media_agency_language = fields.Char(string="Agency Language", size=16, default="NL")
    media_agency_contacts_contact_id = fields.Char(
        string="Agency Contact Number", size=32
    )
    media_agency_contacts_contact_name = fields.Char(
        string="Agency Contact Name", size=64
    )
    media_agency_contacts_contact_email = fields.Char(
        string="Agency Contact Email", size=64
    )
    media_agency_contacts_contact_phone = fields.Char(
        string="Agency Contact Phone", size=64
    )
    media_agency_contacts_contact_type = fields.Char(
        string="Agency Contact Type", size=64
    )
    media_agency_contacts_contact_language = fields.Char(
        string="Agency Contact Language", size=16, default="NL"
    )
    media_agency_contacts_contact2_id = fields.Char(
        string="Agency Contact2 Number", size=32
    )
    media_agency_contacts_contact2_name = fields.Char(
        string="Agency Contact2 Name", size=64
    )
    media_agency_contacts_contact2_email = fields.Char(
        string="Agency Contact2 Email", size=64
    )
    media_agency_contacts_contact2_phone = fields.Char(
        string="Agency Contact2 Phone", size=64
    )
    media_agency_contacts_contact2_type = fields.Char(
        string="Agency Contact2 Type", size=64
    )
    media_agency_contacts_contact2_language = fields.Char(
        string="Agency Contact2 Language",
        size=16,
        # default='NL'
    )
    creative_agency_code = fields.Char(string="Creative Number", size=32)
    creative_agency_name = fields.Char(string="Creative Name", size=64)
    creative_agency_email = fields.Char(string="Creative Email", size=64)
    creative_agency_phone = fields.Char(string="Creative Email", size=64)
    creative_agency_language = fields.Char(
        string="Creative Language", size=16, default="NL"
    )
    creative_agency_contacts_contact_id = fields.Char(
        string="Creative Contact Number", size=32
    )
    creative_agency_contacts_contact_name = fields.Char(
        string="Creative Contact Name", size=64
    )
    creative_agency_contacts_contact_email = fields.Char(
        string="Creative Contact Email", size=64
    )
    creative_agency_contacts_contact_phone = fields.Char(
        string="Creative Contact Phone", size=64
    )
    creative_agency_contacts_contact_type = fields.Char(
        string="Creative Contact Type", size=64
    )
    creative_agency_contacts_contact_language = fields.Char(
        string="Creative Contact Language", size=16, default="NL"
    )
    ad4all_environment = fields.Char("Ad4all Environment")
    order_name = fields.Char("Order Description")
    reference = fields.Char("Order Reference")

    status = fields.Selection(
        [
            ("na", "Not Applicable"),
            ("draft", "Draft"),
            ("successful", "Successful"),
            ("failed", "Failed"),
        ],
        required=True,
        readonly=True,
        store=True,
        compute="_compute_response",
    )

    @api.depends("customer_contacts")
    def _compute_customer_contacts_display(self):
        for this in self:
            this.customer_contacts_display = self.env["ir.qweb"]._render(
                "ad4all_interface.contact_display", {"contacts": this.customer_contacts}
            )

    @api.depends("ad4all_response")
    def _compute_response(self):
        for line in self:
            line.status = "draft"
            if line.not_applicable:
                line.status = "na"
            if line.ad4all_response == "200":
                line.status = "successful"
            elif line.ad4all_response and line.ad4all_response != "200":
                line.status = "failed"

    def call_wsdl(self, xml=False):
        self.ensure_one()
        config = (
            self.env["ad4all.config"]
            .sudo()
            .search(
                [
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", self.sale_line_id.company_id.id),
                ],
                order="company_id",
                limit=1,
            )
        )
        url = str(config.host)
        user = str(config.username)
        pwd = str(config.password)
        self.ad4all_environment = url

        if url[-1] == "/":
            url += "api/rest_order"
        else:
            url += "/api/rest_order"

        xml_data = self.env["ir.qweb"]._render(
            "ad4all_interface.rest_payload", {"line": self}
        )

        data = {
            "portal": config.portal,
            "deliverer": config.deliverer,
            "order_code": str(self.seq_adgr_orde_id),
            "xml_data": xml_data,
        }

        try:
            response = requests.post(url, json=data, auth=(user, pwd), timeout=60)
            response.raise_for_status()
            response = response.json()
            self.write(
                {
                    "ad4all_response": response.get("code"),
                    "json_message": str(xml_data),
                    "reply_message": response.get("message"),
                    "portal": config.portal,
                    "deliverer": config.deliverer,
                }
            )
            return response
        except Exception as e:
            msg = "Odoo Interface Ad4all Error: " + str(e)
            self.write(
                {
                    "reply_message": str(e),
                    "json_message": str(xml_data),
                    "portal": config.portal,
                    "deliverer": config.deliverer,
                }
            )
            _logger.info(msg)
            return {}

    def wsdl_content(self, xml=False):
        self.ensure_one()
        if self.ad4all_response:
            raise UserError(
                _("This Sale Order already has been successfully sent to Ad4all.")
            )
        response = self.call_wsdl(xml)
        AdSent = False
        if response and response.get("code") == 200:
            AdSent = True

        sol = self.env["sale.order.line"].search([("id", "=", self.sale_line_id.id)])
        sol_vals = {
            "date_sent_ad4all": datetime.datetime.now(),
            "publog_id": self.id,
            "ad4all_tbu": False,
            "ad4all_sent": AdSent,
        }
        sol.with_context(no_checks=True).write(sol_vals)
        return True

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
            if "seq_adgr_orde_id" in item:
                vals = args[index][2].replace(",", "")
                args[index][2] = vals
        return super()._search(
            args, offset, limit, order, count=count, access_rights_uid=access_rights_uid
        )
