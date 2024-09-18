# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class UpdateSOL(models.TransientModel):
    """
    This wizard will confirm update changed Issue Date into Non-Invoiced Sale Orders
    """

    _name = "update.order.line"
    _description = "Update Sale Order Line"

    issue_id = fields.Many2one('sale.advertising.issue', 'Ads Issue')
    issue_date = fields.Date('New Issue Date')
    line_ids = fields.Many2many('sale.order.line', 'update_wiz_orderline_rel', 'wiz_id', 'sol_id',
                                                 string='Sale Order Lines')


    def default_get(self, fields):
        result = super(UpdateSOL, self).default_get(fields)
        if self._context.get('active_model') and self._context.get('active_ids') and self._context.get('active_model') == 'sale.advertising.issue':
            AdIssue = self.env['sale.advertising.issue'].browse(self._context.get('active_id'))
            SOL = self.env['sale.order.line'].search([('invoice_status', '!=', 'invoiced'),
                                                      ('adv_issue', '=', AdIssue.id)])

            result.update({'issue_id': AdIssue.id, 'line_ids': [(6,0, SOL.ids)], 'issue_date': AdIssue.issue_date})
        return result

    def action_confirm(self):
        'Update Sale Order Line'

        for sol in self.line_ids:
            # Ensure date type
            if sol.date_type == 'issue_date':
                sol.write({'issue_date': self.issue_date,
                           'from_date': self.issue_date,
                           'to_date': self.issue_date})
            else:
                sol.issue_date = self.issue_date

        self.issue_id.to_update_issdt = False
        return True