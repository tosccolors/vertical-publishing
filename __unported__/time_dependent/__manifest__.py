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
    'name': 'Time Dependent',
    'version': '1.0',
    'category': 'Others',
    'description': """
This is a generic module which can be used on any object.
==============================================================================
In this module, user can input an object (such as res.partner) and it's fields (such as name, street, etc.) for tracking its's values changes for specific time period.

    """,
    'author': 'Magnus - Willem Hulshof',
    'website': 'http://www.magnus.nl',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron_data.xml',
        'views/time_dependent_view.xml',
        ],
    'installable': True
}