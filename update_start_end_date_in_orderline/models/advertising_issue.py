# -*- coding: utf-8 -*-
# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _

class AdvertisingIssue(models.Model):
    _inherit = "sale.advertising.issue"

    @api.multi
    def write(self, vals):
        result = super(AdvertisingIssue, self).write(vals)
        issue_date = vals.get('issue_date', False)
        if issue_date:
            issue_date = str(issue_date)
            op, ids = ('IN', tuple(self.ids)) if len(self.ids) > 1 else ('=', self.id)
            self.env.cr.execute("""
                    UPDATE sale_order_line
                    SET from_date = {0},
                        to_date = {0}
                    WHERE adv_issue {1} {2}
                    """.format(
                    "'%s'" % issue_date,
                    op,
                    ids
                ))
        return result
