# -*- coding: utf-8 -*-

import logging

from odoo import models
from odoo.tools.translate import translate

from odoo.addons.report_xlsx_helper.report.report_xlsx_format import (
    FORMATS,
    XLS_HEADERS,
)

_logger = logging.getLogger(__name__)

IR_TRANSLATION_NAME = "indeellijst.report.xls"

class IndeellijstListReport(models.AbstractModel):
    _name = "report.indeellijst_report_xls.indeellijst_report_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "XLSX report for indeellijst xls."

    def _(self, src):
        lang = self.env.context.get("lang", "en_US")
        val = translate(self.env.cr, IR_TRANSLATION_NAME, "report", lang, src) or src
        return val

    def _get_ws_params(self, workbook, data, pndls):
        col_specs = {
            "adverteerder": {
                "header": {"value": self._("ADVERTEERDER")},
                "lines": {
                    "value": self._render("line.order_advertiser_id.name if line.order_advertiser_id else ''")
                },
                "width": 18,
            },
            "opportunity_subject": {
                "header": {"value": self._("OPPORTUNITY SUBJECT")},
                "lines": {
                    "value": self._render("line.order_id.opportunity_subject")
                },
                "width": 25,
            },
            "sale_order": {
                "header": {"value": self._("SALE ORDER")},
                "lines": {
                    "value": self._render("line.order_id.name")
                },
                "width": 14,
            },
            "salesperson": {
                "header": {"value": self._("SALESPERSON")},
                "lines": {
                    "value": self._render("line.order_id.user_id.name")
                },
                "width": 18,
            },
            "order_id": {
                "header": {"value": self._("ORDER ID")},
                "lines": {
                    "value": self._render("line.order_id.id")
                },
                "width": 12,
            },
            "material_id": {
                "header": {"value": self._("MATERIAL ID")},
                "lines": {
                    "value": self._render("line.recurring_id.id if line.recurring_id else line.id")
                },
                "width": 14,
            },
            "product": {
                "header": {"value": self._("PRODUCT")},
                "lines": {"value": self._render("product")},
                "width": 25,
            },
            "opmerkingen": {
                "header": {"value": self._("OPMERKINGEN")},
                "lines": {"value": self._render("opmerkingen")},
                "width": 18,
            },
            "paginasoort": {
                "header": {"value": self._("PAGINASOORT")},
                "lines": {"value": self._render("paginasoort")},
                "width": 18,
            },

        }
        wanted_list = ['adverteerder', 'opportunity_subject', 'sale_order', 'salesperson',
                       'order_id', 'material_id', 'product', 'opmerkingen', 'paginasoort']
        title = self._("Indeellijst XLSX")

        return [
            {
                "ws_name": title,
                "generate_ws_method": "_indeellijst_export",
                "title": title,
                "wanted_list": wanted_list,
                "col_specs": col_specs,
            }
        ]

    def _indeellijst_export(self, workbook, ws, ws_params, data, soLines):

        ws.set_landscape()
        ws.fit_to_pages(1, 0)
        ws.set_header(XLS_HEADERS["xls_headers"]["standard"])
        ws.set_footer(XLS_HEADERS["xls_footers"]["standard"])

        self._set_column_width(ws, ws_params)

        row_pos = 0

        row_pos = self._write_line(
            ws,
            row_pos,
            ws_params,
            col_specs_section="header",
            default_format=FORMATS["format_theader_yellow_left"],
        )
        ws.freeze_panes(row_pos, 0)

        for sol in soLines:
            pro_name = sol.product_template_id.name
            if sol.product_id.width and sol.product_id.height:
                pro_name += ', ' + str(sol.product_id.width) + 'x' + str(sol.product_id.height) + 'mm'
            if sol.product_uom_qty > 1:
                pro_name += '(' + str(int(sol.product_uom_qty)) + 'p)'

            ref = sol.page_reference or ''
            if sol.layout_remark:
                ref += '\n'+sol.layout_remark or ''
            if sol.name:
                ref += '\n'+sol.name or ''
            pages = ', '.join((map(lambda l: l.name, sol.analytic_tag_ids)))

            row_pos = self._write_line(
                ws,
                row_pos,
                ws_params,
                col_specs_section="lines",
                render_space={"line": sol,
                              "product": pro_name,
                              "opmerkingen": ref,
                              "paginasoort": pages,
                              },
                default_format=FORMATS["format_tcell_left"],
            )