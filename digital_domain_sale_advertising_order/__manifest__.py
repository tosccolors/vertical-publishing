# -*- coding: utf-8 -*-
# Copyright 2018 Willem Hulshof Magnus (www.magnus.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "digital_domain_sale_advertising_order",

    'summary': """
        Creates a boolean field "Digital".
        """,

    'description': """
        This module takes care of a link between advertising class and advertising issues. 
        The cases where this is relevant is for digital media and for (also mainly digital) media where the issue itself is an advertising product. [? Is this true?]
        It also contains a boolean "digital", which provided the same function, but only for classes and issues, where the boolean was true. This boolean will be deprecated.
    """,

    'author': "Magnus",
    'website': "http://www.magnus.nl",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sale',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['sale_advertising_order'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/product_view.xml',
        'views/sale_advertising_view.xml',
        'views/advertising_class_issue_matrix_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}
