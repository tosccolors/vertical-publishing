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
    'name': 'Folders',
    'version': '1.0',
    'category': 'Others',
    'description': """
This module contains information about the geographic segmentation.
==============================================================================
It will help in determining the number of valid addresses for a specific product in a specific zip code range. It also helps in linking a zip code / title to a specific logistics service provider.

    """,
    'author': 'Magnus - Willem Hulshof',
    'website': 'http://www.magnus.nl',
    'depends': ['base', 'sale', 'sale_advertising_order'],
    'data': [
        "views/logistics_addres_table_view.xml",
    ],
    'installable': True
}