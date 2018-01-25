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


    @api.multi
    def create_multi_lines(self):
        context = self._context

        model = context.get('active_model', False)
        n = 0
        all_lines = []
        if model and model == 'sale.order':
            order_ids = context.get('active_ids', [])
            for so in self.env['sale.order'].search([('id','in', order_ids)]):
                olines = so.order_line.filtered(lambda x: x.multi_line)
                if not olines: continue
                all_lines.append(olines)
                n += 1
            if n == 0:
                raise UserError(_('There are no Sales Order Lines with Multi Lines in the selected Sales Orders.'))
            self.create_multi_from_order_lines(orderlines=all_lines)

        elif model and model == 'sale.order.line':
            orders = []
            line_ids = context.get('active_ids', [])
            for line in self.env['sale.order.line'].search([('id','in', line_ids)]):
                orders.append(line.order_id.id)
            for oid in orders:
                lines = self.env['sale.order.line'].search([('order_id','=', oid),('id','in', line_ids),
                                                                   ('multi_line','=', True)])
                if not lines:
                    continue
                n += 1
                all_lines.append(lines)
            if n == 0:
                raise UserError(_('There are no Sales Order Lines with Multi Lines in the selection.'))
            self.create_multi_from_order_lines(orderlines=all_lines)
        return

    @api.model
    def create_multi_from_order_lines(self, orderlines=[]):
        sol_obj = self.env['sale.order.line']
        olines = sol_obj.browse(orderlines)
        lines = []
        for ol in olines:
            if ol.adv_issue_ids and not ol.issue_product_ids:
                raise UserError(_('The Order Line is in error. Please correct!'))
            elif ol.issue_product_ids:
                number_ids = len(ol.issue_product_ids)
                uom_qty = ol.multi_line_number / number_ids
                if uom_qty != 1:
                    raise UserError(_('The number of Lines is different from the number of Issues in the multi line.'))

                for ad_iss in ol.issue_product_ids:
                    ad_issue = self.env['sale.advertising.issue'].search([('id', '=', ad_iss.adv_issue_id.id)])
                    csa = ol.color_surcharge_amount / ol.comb_list_price * ad_iss.price_unit * ol.product_uom_qty if ol.color_surcharge else 0.0
                    sbad = (ad_iss.price_unit * ol.product_uom_qty + csa) * (1 - ol.computed_discount / 100.0)
                    aup = sbad / ol.product_uom_qty
                    res = {'title': ad_issue.parent_id.id,
                           'adv_issue': ad_issue.id,
                           'title_ids': False,
                           'product_id': ad_iss.product_id.id,
                           'name': ol.order_id.name or False,
                           'price_unit': ad_iss.price_unit,
                           'issue_product_ids': False,
                           'color_surcharge_amount':  csa,
                           'subtotal_before_agency_disc': sbad,
                           'actual_unit_price': aup,
                           'order_id': ol.order_id.id or False,
                           'comb_list_price': 0.0,
                           'multi_line_number': 1,
                           'multi_line': False,
                           'ad_number': ad_iss.ad_number or ol.ad_number or False,
                           'page_reference': ad_iss.page_reference or ol.page_reference or False,
                           'url_to_material': ad_iss.url_to_material or ol.url_to_material or False,
                           }
                    vals = ol.copy_data(default=res)[0]
                    mol_rec = sol_obj.create(vals)

                    lines.append(mol_rec.id)
                self._cr.execute("delete from sale_order_line where id = %s" % (ol.id))
        return lines


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
