# -*- coding: utf-8 -*-

from odoo import models, fields, api

# class AccountInvoice(models.Model):
#     _inherit = "account.invoice"

    # def _prepare_invoice_line_from_po_line(self, line):
    #     """
    #     :param line:
    #     :return: Update start_date & end_date from advertising.issue looking into PO line account_analytic_id
    #     """
    #     data = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(line)
    #     if line.account_analytic_id:
    #         adv_issue = self.env['sale.advertising.issue'].search(
    #             [('analytic_account_id', '=', line.account_analytic_id.id)])
    #         issue_date = adv_issue.issue_date if len(adv_issue) == 1 else False
    #         data['start_date'] = data['end_date'] = issue_date
    #     return data

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.onchange('account_analytic_id')
    def onchange_account_analytic_id(self):
        """
        :return: Update start_date & end_date from advertising.issue looking into account_analytic_id
        """
        vals = {}
        if self.sale_line_ids:
            return {'value': vals}
        if self.account_analytic_id:
            adv_issue = self.env['sale.advertising.issue'].search(
                [('analytic_account_id', '=', self.account_analytic_id.id)])
            issue_date = adv_issue.issue_date if len(adv_issue) == 1 else False
            vals['start_date'] = vals['end_date'] = issue_date
        else:
            vals['start_date'] = vals['end_date'] = False
        return {'value': vals}