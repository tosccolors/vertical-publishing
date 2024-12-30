# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Not needed anymore here
# class sale_order_line_create_multi_lines(models.TransientModel):
#     _inherit = "sale.order.line.create.multi.lines"
#
#     def _prepare_default_vals_copy(self, ol, ad_iss):
#         res = super(sale_order_line_create_multi_lines, self)._prepare_default_vals_copy(ol, ad_iss)
#         if ol.date_type == 'issue_date':
#             res['from_date'] = res['to_date'] = ad_iss.adv_issue_id.issue_date
#         return res