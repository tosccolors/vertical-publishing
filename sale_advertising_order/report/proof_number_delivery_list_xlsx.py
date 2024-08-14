
import logging

from odoo import models
# from odoo.tools.translate import translate

from odoo.addons.report_xlsx_helper.report.report_xlsx_format import (
    FORMATS,
    XLS_HEADERS,
)

_logger = logging.getLogger(__name__)

IR_TRANSLATION_NAME = "proof.number.delivery.list.xls"


class ProofNumberDeliveryListXlsx(models.AbstractModel):
    _name = "report.pndl_report_xls.proof_number_delivery_list_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "XLSX report for proof number delivery list."

    def _(self, src):
        lang = self.env.context.get("lang", "en_US")
        # val = translate(self.env.cr, IR_TRANSLATION_NAME, "report", lang, src) or src
        val = src
        return val

    def _get_ws_params(self, workbook, data, pndls):

        # XLSX Template
        col_specs = {
            "papercode": {
                "header": {"value": self._("PAPERCODE")},
                "lines": {"value": self._render("papercode")},
                "width": 12,
            },
            "custname": {
                "header": {"value": self._("CUSTOMER NAME")},
                "lines": {"value": self._render("line.proof_number_payer.name")},
                "width": 32,
            },
            "initials": {
                "header": {"value": self._("INITIALS")}, # FIXME -- Needed?
                "lines": {"value": self._render("line.proof_number_payer.id")},
                "width": 10,
            },
            "infix": {
                "header": {"value": self._("INFIX")}, # FIXME -- Needed?
                "lines": {
                    "value": self._render("line.proof_number_payer.id"),
                },
                "width": 10,
            },
            "lastname": {
                "header": {"value": self._("LAST NAME")},
                "lines": {
                    "value": self._render("line.proof_number_payer.lastname")
                },
                "width": 25,
            },
            "country_code": {
                "header": {"value": self._("COUNTRY CODE")},
                "lines": {
                    "value": self._render("line.proof_number_payer.country_id.code or line.proof_number_payer.parent_id.country_id.code or ''")
                },
                "width": 10,
            },
            "addr_zip": {
                "header": {"value": self._("ADDRESS ZIP")},
                "lines": {
                    "value": self._render("line.proof_number_payer.zip or line.proof_number_payer.parent_id.zip or ''")
                },
                "width": 10,
            },
            "house_num": {
                "header": {"value": self._("HOUSE #")},
                "lines": {
                    "value": self._render("line.proof_number_payer.street_number or line.proof_number_payer.parent_id.street_number or ''")
                },
                "width": 10,
            },
            "door_num": {
                "header": {
                    "value": self._("ADDITION #"),
                },
                "lines": {
                    "value": self._render("line.proof_number_payer.street_number2 or line.proof_number_payer.parent_id.street_number2 or ''")
                },
                "width": 10,
            },
            "addr_street": {
                "header": {
                    "value": self._("ADDRESS STREET"),
                },
                "lines": {
                    "value": self._render("line.proof_number_payer.street_name or line.proof_number_payer.parent_id.street_name or ''")
                },
                "width": 18,
            },
            "addr_city": {
                "header": {
                    "value": self._("ADDRESS CITY"),
                    "format": FORMATS["format_theader_yellow_right"],
                },
                "lines": {
                    "value": self._render("line.proof_number_payer.city or line.proof_number_payer.parent_id.city or ''")
                },
                "width": 10,
            },
            "number": {
                "header": {
                    "value": self._("NUMBER"),
                },
                "lines": {
                    # "value": self._render("pncopies")
                    "value": self._render("line.proof_number_amt")
                },
                "width": 10,
            },
            "con_person": {
                "header": {
                    "value": self._("CONTACT PERSON"),
                    "format": FORMATS["format_theader_yellow_right"],
                },
                "lines": {
                    "value": self._render("line.proof_number_payer.name if line.proof_number_payer.parent_id else ''")
                },
                "width": 18,
            },
            "email": {
                "header": {
                    "value": self._("EMAIL"),
                    "format": FORMATS["format_theader_yellow_right"],
                },
                "lines": {
                    "value": self._render("line.proof_number_payer.email or line.proof_number_payer.parent_id.email or ''")
                },
                "width": 20,
            },
        }


        wanted_list = ['papercode', 'custname', 'lastname', 'country_code', 'addr_zip', 'house_num', 'door_num'
                     , 'addr_street', 'addr_city', 'number', 'con_person', 'email'] # self.env["proof.number.delivery.list"]._report_xlsx_fields()
        title = self._("Proof Number Delivery List")

        return [
            {
                "ws_name": title,
                "generate_ws_method": "_pndls_export",
                "title": title,
                "wanted_list": wanted_list,
                "col_specs": col_specs,
            }
        ]

    def _pndls_export(self, workbook, ws, ws_params, data, pndls):

        ws.set_landscape()
        ws.fit_to_pages(1, 0)
        ws.set_header(XLS_HEADERS["xls_headers"]["standard"])
        ws.set_footer(XLS_HEADERS["xls_footers"]["standard"])

        self._set_column_width(ws, ws_params)

        row_pos = 0
        # row_pos = self._write_ws_title(ws, row_pos, ws_params)

        row_pos = self._write_line(
            ws,
            row_pos,
            ws_params,
            col_specs_section="header",
            default_format=FORMATS["format_theader_yellow_left"],
        )
        ws.freeze_panes(row_pos, 0)

        # Copies / Number:
        # def _get_PDCopies(orderLine):
        #     amount = 0
        #     if not orderLine: return amount
        #
        #     SO = orderLine.order_id
        #     _logger.info("\n\n\n _get_PDCopies ******************* order %s"%(orderLine.order_id.name))
        #
        #     customerID = SO.published_customer and SO.published_customer.id or False
        #     payerID = SO.partner_id and SO.partner_id.id or False
        #     _logger.info("\n\n\n _get_PDCopies ******************* Customer %s "
        #                  "\n _get_PDCopies ******************* payerID %s"%(customerID, payerID))
        #
        #
        #     # Adv Customer
        #     if len(orderLine.proof_number_adv_customer.ids) > 0:
        #         amount += orderLine.proof_number_amt_adv_customer
        #
        #     # Payer
        #     if orderLine.proof_number_payer_id:
        #         amount += orderLine.proof_number_amt_payer
        #     return amount

        # Title / PaperCode
        def _get_titles(orderLine):
            title = []
            if not orderLine: return ''

            for advtitle in orderLine.title_ids:
                if advtitle.product_attribute_value_id:
                    title.append(advtitle.product_attribute_value_id.name)
            if orderLine.title.product_attribute_value_id:
                title.append(orderLine.title.product_attribute_value_id.name)
            title = ",".join(list(set(title))) if title else ' '
            return title

        for line in pndls:
            paperCode = _get_titles(line.line_id)
            # copies = _get_PDCopies(line.line_id)

            row_pos = self._write_line(
                ws,
                row_pos,
                ws_params,
                col_specs_section="lines",
                render_space={"line": line,
                              "papercode": paperCode,
                              # "pncopies": copies
                              },
                default_format=FORMATS["format_tcell_left"],
            )
