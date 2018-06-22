# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2013 Megis - Willem Hulshof - www.megis.nl
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs.
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company like Veritos.
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
##############################################################################
{
    'name': 'Folders',
    'version': '1.0',
    'category': 'Others',
    'description': """
This module contains information about the geographic segmentation.
==============================================================================
It will help in determining the number of valid addresses for a specific product
in a specific zip code range. It also helps in linking a zip code / title to a 
specific logistics service provider.

    """,
    'author': 'Magnus - Willem Hulshof',
    'website': 'http://www.magnus.nl',
    'depends': ['base', 'sale', 'sale_advertising_order', 'bdu_crm'],
    'data': [
        "views/logistics_addres_table_view.xml",
        "security/ir.model.access.csv"
    ],
    'installable': True
}