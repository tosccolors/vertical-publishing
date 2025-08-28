# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from datetime import datetime

import logging
import json
_logger = logging.getLogger(__name__)


class UpdateSOL(models.TransientModel):
    """
    This wizard will confirm update changed Issue Date into Non-Invoiced Sale Orders
    """

    _name = "update.order.line"
    _description = "Update Sale Order Line"

    @api.depends('issue_id')
    def _compute_SOL_domain(self):
        """
        Compute the domain for the published_customer domain.
        """
        for rec in self:
            if rec.issue_id:
                SOL = self.env['sale.order.line'].search([('issue_date', '>=', datetime.now().strftime('%Y-%m-%d')),
                                                          ('adv_issue', '=', rec.issue_id.id)])
                rec.lines_domain = json.dumps(
                    [('id', 'in', SOL.ids)]
                )

    issue_id = fields.Many2one('sale.advertising.issue', 'Ads Issue')
    issue_date = fields.Date('New Issue Date')
    line_ids = fields.Many2many('sale.order.line', 'update_wiz_orderline_rel', 'wiz_id', 'sol_id',
                                                 string='Sale Order Lines')
    line_count = fields.Integer("Found Lines Count")
    lines_domain = fields.Char(compute=_compute_SOL_domain, string="Domain SOL")

    def default_get(self, fields):
        result = super(UpdateSOL, self).default_get(fields)
        if self._context.get('active_model') and self._context.get('active_ids') and self._context.get('active_model') == 'sale.advertising.issue':
            AdIssue = self.env['sale.advertising.issue'].browse(self._context.get('active_id'))
            SOL = self.env['sale.order.line'].search([('issue_date', '>=', datetime.now().strftime('%Y-%m-%d')),
                                                      ('adv_issue', '=', AdIssue.id)])

            result.update({'issue_id': AdIssue.id, 'line_ids': [(6,0, SOL.ids)], 'issue_date': AdIssue.issue_date,
                           'line_count': len(SOL.ids)})
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