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
                olines = so.order_line.filtered('multi_line')
                if not olines: continue
                for ol in olines:
                    all_lines.append(ol.id)
                    n += 1
            if n == 0:
                raise UserError(_('There are no Sales Order Lines with Multi Lines in the selected Sales Orders.'))
            self.create_multi_from_order_lines(orderlines=all_lines)

        elif model and model == 'sale.order.line':
            line_ids = context.get('active_ids', [])
            all_lines = self.env['sale.order.line'].search([('id','in', line_ids),('multi_line','=', True)])
            if not all_lines:
                raise UserError(_('There are no Sales Order Lines with Multi Lines in the selection.'))
            self.create_multi_from_order_lines(orderlines=all_lines)
        return

    @api.multi
    def create_multi_from_order_lines(self, orderlines=[]):
        return self.suspend_security().cmfol(orderlines=orderlines)

    @api.multi
    def cmfol(self, orderlines=[]):

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
                    csa = ol.color_surcharge_amount * (ad_iss.price / ol.comb_list_price)  / ol.product_uom_qty if ol.color_surcharge else 0.0
                    sbad = (ad_iss.price_unit + csa) * ol.product_uom_qty  * (1 - ol.computed_discount / 100.0)
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

                ol.with_context(multi=True).unlink()

        return lines

    @api.multi
    def create_multi_from_order_lines_sql(self, orderlines=[]):
        sol_obj = self.env['sale.order.line']
        olines = sol_obj.browse(orderlines)
        lines = []
        for ol in olines:
            if ol.adv_issue_ids and not ol.issue_product_ids:
                raise UserError(
                    _('The Order Line is in error. Please correct!'))
            elif ol.issue_product_ids:
                number_ids = len(ol.issue_product_ids)
                uom_qty = ol.multi_line_number / number_ids
                if uom_qty != 1:
                    raise UserError(_(
                        'The number of Lines is different from the number of Issues in the multi line.'))

                sql_query = '''
                INSERT INTO sale_order_line
                (
                product_uom,
                product_uom_qty,
                price_subtotal,
                currency_id,
                price_reduce_taxexcl,
                price_tax,
                qty_to_invoice,
                customer_lead,
                company_id,
                state,
                order_partner_id,
                order_id,
                qty_invoiced,
                sequence,
                discount,
                price_reduce,
                qty_delivered,
                price_reduce_taxincl,
                price_total,
                invoice_status,
                salesman_id,
                is_delivery,
                ad_class,
                product_template_id,
                deadline_offset,
                
                title, 
                adv_issue, 
                partner_id, 
                product_id, 
                name,
                price_unit, 
                color_surcharge_amount, 
                subtotal_before_agency_disc, 
                actual_unit_price,
                order_id, 
                comb_list_price, 
                multi_line_number, 
                multi_line, 
                ad_number,
                page_reference,
                url_to_material,
                create_uid,
                create_date,
                write_uid,
                write_date
                )
                SELECT
                title.id AS title,
                issue.id AS adv_issue, 
                solip.product_id AS product_id, 
                so.name AS name,
                solip.price_unit AS price_unit, 
                (sol.color_surcharge_amount * 
                                solip.price / 
                                sol.comb_list_price) / 
                                (CASE WHEN sol.color_surcharge = true
                                THEN sol.product_uom_qty 
                                ELSE 0.0 END)  
                                AS color_surcharge_amount, 
                (solip.price_unit + 
                    (sol.color_surcharge_amount * 
                                    solip.price / 
                                    sol.comb_list_price) / 
                                    (CASE WHEN sol.color_surcharge = true
                                    THEN sol.product_uom_qty 
                                    ELSE 0.0 END)) * 
                sol.product_uom_qty * 
                    (1 - sol.computed_discount / 100.0) 
                    AS subtotal_before_agency_disc, 
                (sol.color_surcharge_amount * 
                                solip.price / 
                                sol.comb_list_price) / 
                                (CASE WHEN sol.color_surcharge = true
                                THEN sol.product_uom_qty 
                                ELSE 0.0 END)  
                                AS color_surcharge_amount, 
                (solip.price_unit + 
                    (sol.color_surcharge_amount * 
                                    solip.price / 
                                    sol.comb_list_price) / 
                                    (CASE WHEN sol.color_surcharge = true
                                    THEN sol.product_uom_qty 
                                    ELSE 0.0 END)) * 
                sol.product_uom_qty * 
                    (1 - sol.computed_discount / 100.0)/
                sol.product_uom_qty AS actual_unit_price,
                so.id AS order_id, 
                0.0 AS comb_list_price, 
                1 AS multi_line_number, 
                'false' AS multi_line, 
                CASE
                 WHEN solip.ad_number is not NULL
                    THEN solip.ad_number
                        WHEN sol.ad_number is not NULL
                            THEN sol.ad_number
                 ELSE NULL
                END AS ad_number,
                CASE
                 WHEN solip.page_reference is not NULL
                    THEN solip.page_reference
                        WHEN sol.page_reference is not NULL
                            THEN sol.page_reference
                 ELSE NULL
                END AS page_reference,
                CASE
                 WHEN solip.url_to_material is not NULL
                    THEN solip.url_to_material
                        WHEN sol.url_to_material is not NULL
                            THEN sol.url_to_material
                 ELSE NULL
                END AS url_to_material,
                {16} AS create_uid,
                {17} AS create_date,
                {18} AS write_uid,
                {19} AS write_date
                FROM 
                sale_order_line_issues_products solip
                JOIN 
                sale_order_line sol
                ON (sol.id = solip.order_line_id)
                JOIN 
                    (sale_advertising_issue issue
                    JOIN
                    sale_advertising_issue title
                    ON (title.id = issue.parent_id))
                ON (issue.id = solip.adv_issue_id)
                JOIN sale_order so
                ON (so.id = sol.order_id)
                WHERE
                solip.id IN ({})
                
                
                ;
                '''

                solip_ids = [ad_iss.id for ad_iss in ol.issue_product_ids]
                    ad_issue = self.env['sale.advertising.issue'].search(
                        [('id', '=', ad_iss.adv_issue_id.id)])
                    csa = ol.color_surcharge_amount * (
                                ad_iss.price / ol.comb_list_price) / ol.product_uom_qty if ol.color_surcharge else 0.0
                    sbad = (ad_iss.price_unit + csa) * ol.product_uom_qty * (
                                1 - ol.computed_discount / 100.0)
                    aup = sbad / ol.product_uom_qty
                    res = {'title': ad_issue.parent_id.id,
                           'adv_issue': ad_issue.id,
                           'title_ids': False,
                           'product_id': ad_iss.product_id.id,
                           'name': ol.order_id.name or False,
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
                           'page_reference': ad_iss.page_reference or ol.page_reference or False,
                           'url_to_material': ad_iss.url_to_material or ol.url_to_material or False,
                           }
                    vals = ol.copy_data(default=res)[0]
                    mol_rec = sol_obj.create(vals)

                    lines.append(mol_rec.id)

                sol_obj.search([('id', '=', ol.id)]).with_context(
                    multi=True).unlink()

        return lines



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
