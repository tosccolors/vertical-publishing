# -*- coding: utf-8 -*-
# Copyright 2018 Willem Hulshof Magnus (www.magnus.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "sale_advertising_order_filter_changes_after_deadline",

    'summary': "",

    'description': """
        This module adds a custom filter which should show the records that meet the following criterium:\n
        In sale.order, is/has one or more sale order line(s) that has been created or changed after the sale.advertising.issue.deadline has passed.\n
        In sale.order.line, the records created or changed after the sale.advertising.issue.deadline has passed.
    """,

    'author': "Magnus",
    'website': "http://www.magnus.nl",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sale',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['sale_advertising_order'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/sale_advertising_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}
