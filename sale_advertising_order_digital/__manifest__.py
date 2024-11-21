# -*- coding: utf-8 -*-
# Copyright 2018 Willem Hulshof Magnus (www.magnus.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "Sale advertising order - Digital",

    'summary': """
        Creates a boolean field "Digital".
        """,

    'description': """
         1. It creates a link between advertising class and advertising issues through the 'digital' boolean. Whenever the 'digital' boolean in the advertising class is set to true, this module makes sure only advertising issues will be shown that have the 'digital' boolean set to true as well.
         2. This also applies vice versa: whenever the 'digital' boolean in the advertising class is set to false, only advertising issues will be shown that have the 'digital' boolean set to false.
         3. This module adds an editable boolean 'Issue date >= today' in the sale advertising order line as well. This boolean is only applicable when the medium sale_advertising_order.magazine_advertising_category ('Print') is selected. The boolean 'Issue date >= today' is set to true by default and makes sure only advertising issues equal to or larger than today are selectable. The user can manually set the boolean 'Issue date >= today' to false to be able to select any advertising issue, even if it's issue date is in the past.
    """,

    'author': "TOSC",
    'website': "http://www.tosc.nl",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sale',
    'version': '16.0.2.6',

    # any module necessary for this one to work correctly
    'depends': ['sale_advertising_order'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/product_view.xml',
        'views/sale_advertising_view.xml',
        # 'views/advertising_class_issue_matrix_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}
