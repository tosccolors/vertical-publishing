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
    'name': 'publishing_subscription_order',
    'version': '1.0',
    'category': 'Sale',
    'description': """
This module allows you to use Sales Management to run your subscription sales
==============================================================================


    """,
    'author': 'Magnus - Willem Hulshof',
    'website': 'http://www.magnus.nl',
    'depends': [
        'sale_advertising_order',
        'sale_operating_unit',
        'account_payment_mode',
        'time_dependent',
        'account_invoice_start_end_dates',
        'report_xlsx',
        'report_xml',
        'l10n_nl_partner_name',
        'hr',
        'project_issue', #for positioning "subs as reader smart button" 
    ],
    'data': [
        "data/ir_sequence_data.xml",
        "security/ir.model.access.csv",
        "demo/subscription_demo.xml",
        "report/subscription_delivery_report.xml",
        "report/report_delivery_list.xml",
        "data/cron_data.xml",
        # "data/payment_data.xml",
        "data/delivery_type_data.xml",
        "views/sale_subscription_view.xml",
        "views/res_partner_view.xml",
        "views/product_view.xml",
        "views/res_config_view.xml",
        "views/subscription_delivery_view.xml",
        "views/crm_lead_view.xml",
        "views/subscription_config_view.xml",
        "views/subscription_wizard_view.xml"
    ],
    'qweb': [
        "static/src/xml/sales_team_dashboard.xml",
        "static/src/xml/qweb.xml",
    ],
    'installable': True
}