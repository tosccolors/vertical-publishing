# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class sale_order_line_create_multi_lines(models.TransientModel):

    _name = "sale.order.line.create.multi.lines"
    _description = "Sale OrderLine Create Multi"


    
    def create_multi_lines(self):
        context = self._context
        model = context.get('active_model', False)
        n = 0
        all_lines = []
        if model and model == 'sale.order':
            order_ids = self.env['sale.order'].search([
                ('id','in', context.get('active_ids', []))])
            for so in order_ids:
                olines = so.order_line.filtered('multi_line')
                if not olines: continue
                for ol in olines:
                    all_lines.append(ol.id)
                    n += 1
            if n == 0:
                raise UserError(_
                        ('There are no Sales Order Lines with Multi Lines in '
                         'the selected Sales Orders.'))
            self.create_multi_from_order_lines(orderlines=all_lines, orders=order_ids)

        elif model and model == 'sale.order.line':
            line_ids = context.get('active_ids', [])
            all_lines = self.env['sale.order.line'].search([
                ('id','in', line_ids),
                ('multi_line','=', True)
            ])
            if not all_lines:
                raise UserError(_('There are no Sales Order Lines with '
                                  'Multi Lines in the selection.'))
            orders = self.env['sale.order'].search([('id','in', all_lines.mapped('order_id'))])
            self.create_multi_from_order_lines(orderlines=all_lines.ids, orders=orders)
        return

    
    def create_multi_from_order_lines(self, orderlines=[], orders=None):
        return self.sudo().cmfol(orderlines=orderlines)

    
    def cmfol(self, orderlines=[]):
        sol_obj = self.env['sale.order.line']
        olines = sol_obj.browse(orderlines)
        lines = []
        for ol in olines:
            if ol.adv_issue_ids and not ol.issue_product_ids:
                raise UserError(_
                                ('The Order Line is in error. Please correct!'))
            elif ol.issue_product_ids:
                number_ids = len(ol.issue_product_ids)
                uom_qty = ol.multi_line_number / number_ids
                if uom_qty != 1:
                    raise UserError(_
                                    ('The number of Lines is different from the'
                                     ' number of Issues in the multi line.'))
                for ad_iss in ol.issue_product_ids:
                    res = self._prepare_default_vals_copy(ol, ad_iss)
                    vals = ol.copy_data(default=res)[0]
                    mol_rec = sol_obj.create(vals)
                    lines.append(mol_rec.id)
                ol.with_context(multi=True).unlink()
        return lines

    def _prepare_default_vals_copy(self, ol, ad_iss):
        ad_issue = self.env['sale.advertising.issue'].search([
                                ('id', '=', ad_iss.adv_issue_id.id)])
        csa = ol.color_surcharge_amount * \
              (ad_iss.price / ol.comb_list_price) / \
              ol.product_uom_qty if ol.color_surcharge else 0.0
        sbad = (ad_iss.price_unit + csa) * \
               ol.product_uom_qty * (1 - ol.computed_discount / 100.0)
        aup = sbad / ol.product_uom_qty
        res = {'title': ad_issue.parent_id.id,
                 'adv_issue': ad_issue.id,
                 'title_ids': [(6, 0, [ad_issue.parent_id.id])],
                 'adv_issue_ids': [(6, 0, [ad_issue.id])],
                 'product_id': ad_iss.product_id.id,
                 'price_unit': ad_iss.price_unit,
                 'issue_product_ids': False,
                 'color_surcharge_amount': csa,
                 'subtotal_before_agency_disc': sbad,
                 'actual_unit_price': aup,
                 'order_id': ol.order_id.id or False,
                 'comb_list_price': 0.0,
                 'multi_line_number': 1,
                 'multi_line': False,
                 'ad_number': ad_iss.ad_number or ol.ad_number or False,
                 'page_reference': ad_iss.page_reference or
                                   ol.page_reference or False,
                 'url_to_material': ad_iss.url_to_material or
                                    ol.url_to_material or False,
               'from_date': ol.date_type == 'issue_date' and ad_issue.issue_date or ol.from_date,
               'to_date': ol.date_type == 'issue_date' and ad_issue.issue_date or ol.to_date,
         }

        return res



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
