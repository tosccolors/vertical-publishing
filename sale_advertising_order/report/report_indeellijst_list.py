# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError

class IndeellijstListReport(models.AbstractModel):
    _name = "report.indeellijst_report_xls.indeellijst_report_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "XLSX report for indeellijst xls."


    def generate_xlsx_report(self, workbook, data, orderLines):

        def _form_data(sol):
            sline = []
            pro_name = sol.product_template_id.name
            if sol.product_id.width and sol.product_id.height:
                pro_name += ', ' + str(sol.product_id.width) + 'x' + str(sol.product_id.height) + 'mm'
            if sol.product_uom_qty > 1:
                pro_name += '('+str(int(sol.product_uom_qty)) + 'p)'
            sline.append(sol.order_advertiser_id.name)
            sline.append(sol.order_id.name)
            sline.append(sol.order_id.user_id.name)
            sline.append(sol.order_id.id)
            sline.append(pro_name)
            ref = sol.page_reference or ''
            if sol.layout_remark:
                ref += '\n'+sol.layout_remark or ''
            if sol.name:
                ref += '\n'+sol.name or ''
            sline.append(ref)
            sline.append(', '.join((map(lambda l: l.name, sol.analytic_tag_ids))))
            return sline

        line_count = orderLines.read_group([('id', 'in', orderLines.ids)],['title', 'adv_issue'], ['title', 'adv_issue'])
        if len(line_count) > 1:
            raise UserError(_("Selected records must be identical to 'Title' and 'Advertising Issue'!"))

        orderByAdClass = orderLines.read_group([('id', 'in', orderLines.ids)], ['ad_class'], ['ad_class'])

        bold_format = workbook.add_format({'bold': True})
        bold_format.set_border(style=2)

        cell_format = workbook.add_format()
        cell_format.set_border(style=2)

        adClsFmt = workbook.add_format({'bold': True})

        date_style = workbook.add_format({'text_wrap': True, 'num_format': 'dd/mm/yyyy'})
        date_style.set_border(style=2)

        title = orderLines[0].title
        adv_issue = orderLines[0].adv_issue
        issue_date = orderLines[0].issue_date
        report_name = title.name if title else adv_issue.name if adv_issue else ""
        if title and title.name and adv_issue and adv_issue.name:
            report_name = title.name + '-' + adv_issue.name
        sheet = workbook.add_worksheet(report_name[:31])

        row = 0
        #add title and it's values
        sheet.write(row, 0, 'Titel', bold_format)
        sheet.write(row, 1, title.name, cell_format)
        row += 1

        # add issue and it's values
        sheet.write(row, 0, 'Editie', bold_format)
        sheet.write(row, 1, adv_issue.name, cell_format)
        row += 1

        # add issue_date
        sheet.write(row, 0, 'Editiedatum', bold_format)
        sheet.write(row, 1, issue_date, date_style)
        row += 2

        ad_class_header = ['Adverteerder', 'Sale Order', 'Salesperson', 'Order ID', 'Product', 'Opmerkingen', 'Paginasoort']

        for rdata in orderByAdClass:
            ad_class_id = rdata['ad_class'][0]
            ad_class = self.env['product.category'].browse(ad_class_id)
            sheet.write(row, 0, ad_class.name, adClsFmt)
            row += 1
            for i, title in enumerate(ad_class_header):
                sheet.write(row, i, title, bold_format)
                sheet.set_column(row, i, 20)
            row += 1
            for sol in orderLines.filtered(lambda sl: sl.ad_class.id == ad_class_id):
                row_datas = _form_data(sol)
                for cell_index, cell_value in enumerate(row_datas):
                    sheet.write(row, cell_index, cell_value, cell_format)
                row += 1
            row += 2

        workbook.close()
