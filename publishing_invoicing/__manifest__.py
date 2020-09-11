# -*- coding: utf-8 -*-
{
    'name': "Publishing Invoicing",

    'summary': """
        Invoicing property feature added for invoicing""",

    'description': """
        
    """,
    'author': "Magnus",
    'website': "http://www.magnus.nl",

    'category': 'Sale',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['sale','base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/invoicing_property_view.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
}