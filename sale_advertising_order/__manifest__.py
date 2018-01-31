# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2016 Magnus (<http://www.magnus.nl>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'sale_advertising_order',
    'version': '1.0',
    'category': 'Sale',
    'description': """
This module allows you to use both CRM and Sales Management to run your advertising sales
=========================================================================================


    """,
    'author': 'Magnus - Willem Hulshof',
    'website': 'http://www.magnus.nl',
    'depends': [
                'sale_crm', 'sale_operating_unit',
                'product_variant_template_categ_id','project',
                'web_domain_field'
                ],
    'data': [
             "data/sale_advertising_data.xml",
             "security/ir.model.access.csv",
             "security/security.xml",
             "wizard/sale_line_create_multi_view.xml",
             "wizard/crm_lead_to_opportunity_view.xml",
             "wizard/adv_line_invoice.xml",
             "wizard/sale_order_state_view.xml",
             "views/res_partner_view.xml",
             "views/res_company_view.xml",
             "views/product_view.xml",
             "views/sale_advertising_view.xml",
             "views/crm_lead_view.xml",
             "views/crm_menu_view.xml",
             "views/sale_dashboard_view.xml",
             ],
    'qweb': [
        "static/src/xml/sales_team_dashboard.xml",
    ],
    'demo': ['demo/sale_advertising_demo.xml'],
    'installable': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

