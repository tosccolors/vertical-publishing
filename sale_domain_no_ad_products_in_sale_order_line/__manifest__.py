# -*- coding: utf-8 -*-
# Copyright 2018 Willem Hulshof Magnus (www.magnus.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "sale_domain_no_ad_products_in_sale_order_line",

    'summary': "This module implements domain on product_id in regular sale.order.line",

    'description': """
        This module implements domain on product_id in regular sale.order.line.\n
        When selecting the product_id in the regular sale.order.line, it only shows the products that:\n

        1. Do NOT have product.category (or a child of) "Ads" set as categ_id. So we do NOT show Advertising products when selecting product_id in the sale.order.line.\n

        2. Have the boolean "Can be sold" set to TRUE.
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
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}
