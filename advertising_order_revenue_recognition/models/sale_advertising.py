# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        if self.advertising:
            start_date = None
            end_date = None
            if self.to_date and self.from_date:
                start_date = self.from_date
                end_date = self.to_date
            else:
                if self.issue_date:
                    start_date = self.issue_date
                    end_date = self.issue_date
            res['start_date'] = start_date,
            res['end_date'] = end_date,
        return res

    @api.onchange('issue_date')
    def onchange_issue_date(self):
        vals = {}
        if not self.advertising:
            return {'value':vals}
        if self.date_type == 'issue_date' and self.issue_date:
            vals['from_date'] = vals['to_date'] = self.issue_date
        return {'value': vals}