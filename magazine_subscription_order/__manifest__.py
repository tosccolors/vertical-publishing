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
    'name': 'magazine_subscription_order',
    'version': '1.0',
    'category': 'Sale',
    'description': """
This module allows you to use Sales Management to run your subscription sales
==============================================================================


    """,
    'author': 'Magnus - Willem Hulshof',
    'website': 'http://www.magnus.nl',
    'depends': ['sale_advertising_order','sale_operating_unit','time_dependent'],
    'data': [
        "views/res_partner_view.xml",
        "views/sale_subscription_view.xml",
        "views/product_view.xml",
        "views/account_invoice_view.xml",
        "views/account_move_view.xml",
        "views/res_config_view.xml",
        "views/subscription_prepaid_view.xml",
    ],
    'installable': True
}