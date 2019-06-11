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
    'name': 'Advertising invoice customisation',
    'version': '1.0',
    'category': 'Generic Modules',
    'description': """
This module improves the integration between sale advertising orders and advertising invoices generated from sale advertising orders.
============================================================================================================


    """,
    'author': 'Magnus - DK',
    'website': 'http://www.magnus.nl',
    'depends': [
                'sale_advertising_order','magnus_account'
                ],
    'data': [
             "views/account_invoice_view.xml",
             "views/report_invoice.xml",
             ],
    'demo': [],
    'installable': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

