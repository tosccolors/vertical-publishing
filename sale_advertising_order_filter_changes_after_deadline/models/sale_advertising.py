# -*- coding: utf-8 -*-
# Copyright 2018 Magnus ((www.magnus.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.one
    @api.depends('order_line','order_line.changes_after_deadline')
    def _compute_changes_after_deadline(self):
        if any([l.changes_after_deadline for l in self.order_line]):
            self.changes_after_deadline = True
        else:
            self.changes_after_deadline = False

    changes_after_deadline = fields.Boolean(compute='_compute_changes_after_deadline', string='Changes after deadline', store=True)

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.one
    @api.depends('write_date','adv_issue','adv_issue.deadline')
    def _compute_changes_after_deadline(self):
        if self.write_date and self.adv_issue.deadline:
            write_date = fields.Datetime.from_string(self.write_date)
            adv_issue_deadline = fields.Datetime.from_string(self.adv_issue.deadline)
            if write_date > adv_issue_deadline:
                self.changes_after_deadline = True
            else:
                self.changes_after_deadline = False
        else:
            self.changes_after_deadline = False

    changes_after_deadline = fields.Boolean(compute='_compute_changes_after_deadline', string='Changes after deadline', store=True)