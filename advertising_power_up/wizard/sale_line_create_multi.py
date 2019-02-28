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

    _inherit = "sale.order.line.create.multi.lines"



    @api.multi
    def create_multi_from_order_lines(self, orderlines=[], orders= None):
        sol_obj = self.env['sale.order.line']
        olines = sol_obj.browse(orderlines)
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

        query =("""
        INSERT INTO sale_order_line 
                       (product_uom,
                        product_uom_qty,
                        currency_id,
                        price_reduce,
                        price_reduce_taxexcl,
                        price_reduce_taxinc,
                        price_tax,
                        qty_to_invoice,
                        customer_lead,
                        company_id,
                        state,
                        order_partner_id,
                        qty_invoiced,
                        sequence,
                        discount,
                        qty_delivered,
                        invoice_status,
                        salesman_id,
                        is_delivery,
                        ad_class,
                        product_template_id,
                        deadline_offset, 
                        layout_remark,
                        discount_reason_id,
                        color_surcharge,
                        advertising,
                        nett_nett,
                        to_date,
                        computed_discount,
                        from_date,
                        medium,
                        partner_acc_mgr,
                        issue_date,
                        order_advertiser_id,
                        order_agency_id,
                        title,
                        adv_issue,
                        product_id,
                        name,
                        price_unit,
                        subtotal_before_agency_disc,
                        color_surcharge_amount,
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
                        write_date,
                        price_subtotal,
                        price_total,
                        line_pubble_allow )
                SELECT
                sol.product_uom AS product_uom,
                sol.product_uom_qty AS product_uom_qty,
                sol.currency_id AS currency_id,
                CASE
                    WHEN sol.comb_list_price > 0.0 
                        AND sol.product_uom_qty > 0.0 
                    THEN sol.subtotal_before_agency_disc * solip.price_unit / 
                         sol.comb_list_price / sol.product_uom_qty
                    ELSE 0.0
                END AS price_reduce,
                CASE
                    WHEN sol.comb_list_price > 0.0 
                        AND sol.product_uom_qty > 0.0 
                    THEN sol.price_subtotal * solip.price_unit / 
                         sol.comb_list_price / sol.product_uom_qty
                    ELSE 0.0
                END AS price_reduce_taxexcl,
                CASE
                    WHEN sol.comb_list_price > 0.0 
                        AND sol.product_uom_qty > 0.0 
                    THEN sol.price_total * solip.price_unit / 
                         sol.comb_list_price / sol.product_uom_qty
                    ELSE 0.0
                END AS price_reduce_taxinc,
                CASE
                    WHEN sol.comb_list_price > 0.0 
                    THEN sol.price_tax * solip.price_unit / 
                         sol.comb_list_price
                    ELSE 0.0
                END AS price_tax,
                sol.qty_to_invoice AS qty_to_invoice,
                sol.customer_lead AS customer_lead,
                sol.company_id AS company_id,
                sol.state AS state,
                sol.order_partner_id AS order_partner_id,
                sol.qty_invoiced AS qty_invoiced,
                sol.sequence AS sequence,
                sol.discount AS discount,
                sol.qty_delivered AS qty_delivered,
                sol.invoice_status AS invoice_status,
                sol.salesman_id AS salesman_id,
                sol.is_delivery AS is_delivery,
                sol.ad_class AS ad_class,
                sol.product_template_id AS product_template_id,
                sol.deadline_offset AS deadline_offset, 
                sol.layout_remark AS layout_remark,
                sol.discount_reason_id AS discount_reason_id,
                sol.color_surcharge AS color_surcharge,
                sol.advertising AS advertising,
                sol.nett_nett AS nett_nett,
                sol.to_date AS to_date,
                sol.computed_discount AS computed_discount,
                sol.from_date AS from_date,
                sol.medium AS medium,
                sol.partner_acc_mgr AS partner_acc_mgr,
                issue.issue_date AS issue_date,
                sol.order_advertiser_id AS order_advertiser_id,
                sol.order_agency_id AS order_agency_id,
                title.id AS title,
                issue.id AS adv_issue, 
                solip.product_id AS product_id, 
                so.name AS name,
                solip.price_unit AS price_unit,
                CASE
                    WHEN sol.comb_list_price > 0.0
                    THEN sol.subtotal_before_agency_disc * solip.price_unit / 
                         sol.comb_list_price
                    ELSE 0.0
                END AS subtotal_before_agency_disc, 
                CASE
                    WHEN sol.comb_list_price > 0.0
                    THEN sol.color_surcharge_amount * solip.price_unit / 
                         sol.comb_list_price
                    ELSE 0.0
                END AS color_surcharge_amount, 
                sol.order_id AS order_id, 
                0.0 AS comb_list_price, 
                1 AS multi_line_number, 
                'false' AS multi_line, 
                CASE
                    WHEN solip.ad_number is not NULL THEN solip.ad_number
                    WHEN sol.ad_number is not NULL THEN sol.ad_number
                    ELSE NULL
                END AS ad_number,
                CASE
                    WHEN solip.page_reference is not NULL
                    THEN solip.page_reference  
                    WHEN sol.page_reference is not NULL
                    THEN sol.page_reference
                    ELSE NULL
                END 
                AS page_reference,
                CASE
                    WHEN solip.url_to_material is not NULL
                    THEN solip.url_to_material
                    WHEN sol.url_to_material is not NULL
                    THEN sol.url_to_material
                    ELSE NULL
                END 
                AS url_to_material,
                {0} AS create_uid,
                {1} AS create_date,
                {0} AS write_uid,
                {1} AS write_date,
                CASE
                    WHEN sol.comb_list_price > 0.0 
                    THEN sol.price_subtotal * solip.price_unit / 
                         sol.comb_list_price
                    ELSE 0.0
                END AS price_subtotal,
                CASE
                    WHEN sol.comb_list_price > 0.0 
                    THEN sol.price_total * solip.price_unit / 
                         sol.comb_list_price
                    ELSE 0.0
                END AS price_total,
                CASE
                    WHEN adclass.pubble is true AND medium.pubble is true
                    THEN true
                    ELSE false
                END 
                AS line_pubble_allow
                FROM sale_order_line sol
                LEFT JOIN sale_order_line_issues_products solip
                ON (sol.id = solip.order_line_id)
                LEFT JOIN sale_advertising_issue issue
                ON (issue.id = solip.adv_issue_id)
                LEFT JOIN sale_advertising_issue title
                ON (title.id = issue.parent_id)
                LEFT JOIN sale_order so
                ON (so.id = sol.order_id)
                LEFT JOIN product_category adclass
                ON (adclass.id = sol.ad_class)
                LEFT JOIN product_category medium
                ON (medium.id = issue.medium)
                WHERE
                sol.id {2} '{3}'
                RETURNING id
                ;""".format(
        self._uid,
        "'%s'" % str(fields.Datetime.to_string(fields.datetime.now())),
        'IN' if len(orderlines) > 1 else '=',
        tuple(orderlines) if len(orderlines) > 1 else orderlines[0]
        ))
        self.env.cr.execute(query )
        lines = [r[0] for r in self.env.cr.fetchall()]
        del_query = ("""
        DELETE FROM sale_order_line 
                WHERE id IN (
                SELECT sol.id 
                FROM sale_order_line sol
                JOIN sale_order_line_issues_products solip
                ON (sol.id = solip.order_line_id)
                WHERE
                sol.id {0} '{1}')
                ;""".format(
        'IN' if len(orderlines) > 1 else '=',
        tuple(orderlines) if len(orderlines) > 1 else orderlines[0]
        ))
        ## m2m:tax_ids and analytic_tag_ids still to update
        ## o2m: nothing
        self.env.cr.execute(del_query)
        self.env.invalidate_all()
        if orders:
            orders._pubble_allow()
        return lines



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
