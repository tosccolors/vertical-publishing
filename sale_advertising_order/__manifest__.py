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
    'name': 'Sale Advertising Order',
    'version': '14.0.19.1',
    'category': 'Sale',
    'description': """
This module allows you to use both CRM and Sales Management to run your advertising sales
============================================================================================


    """,
    'author': 'Deepa, Willem Hulshof, The Open Source Company (TOSC)',
    'website': 'http://www.tosc.nl',
    'depends': [
                'sale', 'sale_crm', 'sale_operating_unit', 'account',
                'product_variant_template_categ_id','project',
                'web_domain_field','account_payment_sale',
                'web_tree_many2one_clickable', 'crm_industry',
                'sale_order_type', 'base_address_extended',
                'partner_firstname', 'report_xlsx_helper',
                'partner_manual_rank', 'calendar',

                # Following dependency are for model access only
                'sale_management', 'sale_stock', 'delivery'
                ],
    'data': [
             "data/sale_advertising_data.xml",
             "data/crm_stage_data.xml",
             "data/mail_template_data.xml",
             "data/sale_order_type.xml",

             "security/security.xml",
             "security/ir.model.access.csv",

             "report/proof_number_delivery_list_xslx.xml",
             "report/report_external_views.xml",
             "report/invoice_report_template.xml",
             "report/sale_report_template.xml",
             "report/report_indeellijst_list_views.xml",

             "wizard/crm_lead_to_quote_view.xml",
             "wizard/sale_line_create_multi_view.xml",
             "wizard/crm_lead_to_opportunity_view.xml",
             "wizard/adv_line_invoice.xml",
             "wizard/sale_order_state_view.xml",
             "wizard/update_order_line_view.xml",

             "views/product_view.xml",
             "views/account_invoice_view.xml",
             "views/sale_advertising_view.xml",
             "views/proof_delivery_list_view.xml",
             "views/res_partner_view.xml",
             "views/menu_views.xml",
             "views/sale_config_settings.xml"
             ],
    'qweb': [
    ],
    'demo': ['demo/sale_advertising_demo.xml'],
    'installable': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

