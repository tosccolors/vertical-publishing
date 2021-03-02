# -*- coding: utf-8 -*-
{
    'name': "update_start_end_date_in_orderline",

    'summary': """
        Update sale order line start and end date from issue date""",

    'description': """
        Update sale order line start and end date from issue date
    """,

    'author': 'Magnus - K.Sushma',
    'website': 'http://www.magnus.nl',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/10.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sale',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['sale_advertising_order'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}