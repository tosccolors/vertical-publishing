# -*- coding: utf-8 -*-
from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx
# import StringIO
# import base64

class DeliveryListReport(ReportXlsx):

    def generate_xlsx_report(self, workbook, data, deliveryLists):

        def _form_data(deliverylistobj):
            row_datas = []
            seq=1
            for deliverylineobj in deliverylistobj.delivery_line_ids:
                records =[]
                add = (deliverylineobj.partner_id.street+' '+deliverylineobj.partner_id.street2) if deliverylineobj.partner_id.street2 else deliverylineobj.partner_id.street
                records.append(seq)
                records.append(deliverylineobj.subscription_number.name)
                records.append(deliverylineobj.product_uom_qty)
                records.append(deliverylineobj.partner_id.name)
                records.append(add)
                records.append(deliverylineobj.partner_id.street_number or '-')
                records.append(deliverylineobj.partner_id.city)
                records.append(deliverylineobj.partner_id.zip)
                seq+=1
                row_datas.append(records)
            return row_datas

        header = ['S.No', 'Subscription Number', 'Quantity', 'Partner', 'Street', 'Street Number', 'City', 'Zip Code']

        merge_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })
        bold_format = workbook.add_format({'bold': True})

        for deliveryobj in deliveryLists:
            row_datas = _form_data(deliveryobj)
            if row_datas:
                report_name = deliveryobj.issue_id.name + '('+deliveryobj.type.name+')'
                sheet = workbook.add_worksheet(report_name[:31])
                sheet.merge_range(0, 0, 0, 10,report_name, merge_format) #(first row, first col, last row, last col)
                for i, title in enumerate(header):
                    sheet.write(1, i, title, bold_format)

                for row_index, row in enumerate(row_datas):
                    for cell_index, cell_value in enumerate(row):
                        sheet.write(row_index + 2, cell_index, cell_value)
        workbook.close()


DeliveryListReport('report.report_subscription_delivery.xlsx', 'subscription.delivery.list')