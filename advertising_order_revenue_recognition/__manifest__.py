# -*- coding: utf-8 -*-
{
    'name': "advertising_order_revenue_recognition",

    'summary': """
        Advertising Order Revenue Recognition""",

    'description': """
        Advertising Order Revenue Recognition
    """,

    'author': 'Magnus - K.Sushma',
    'website': 'http://www.magnus.nl',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sale',
    'version': '14.0.2.0',

    # any module necessary for this one to work correctly
    'depends': ['sale_advertising_order',
                'account_invoice_start_end_dates'],

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