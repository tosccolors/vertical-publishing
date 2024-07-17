# -*- coding: utf-8 -*-
{
    'name': "Publishing Refunds",

    'summary': """
        Invoice Refund validation feature added for invoicing""",

    'description': """ """,
    'author': "Magnus",
    'website': "http://www.magnus.nl",

    'category': 'Sale',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['sale','account','sale_advertising_order_invoice_customisation'],

    # always loaded
    'data': [
        'views/account_invoice_views.xml',
    ],
}