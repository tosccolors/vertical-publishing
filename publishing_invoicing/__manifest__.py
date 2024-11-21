# -*- coding: utf-8 -*-
{
    'name': "Publishing Invoicing",

    'summary': """
        Invoicing property feature added for invoicing""",

    'description': """This module is an add-on for the advertising sales modules. 
    It facilitates easier invoicing, without the usage of filters for sale order lines which is the traditional method. 
    This module facilitates invoice properties. This module provides a new menu, which one can use to create invoicing property objects per customer. 
    In these objects, one specifies how to invoice for this customer, e.g. per advertiser, per edition, per period, online and print separated etc. 
    When placing a new order, it is allowed to choose another invoicing property when desired, 
    although the default choice is the invoice property belonging to the customer. 
    The invoicing_property object has a one2many relation with res.partner, and a one2many relation with sale.order.
        
    """,
    'author': "Magnus, Deepa (TOSC)",
    'website': "http://www.magnus.nl",

    'category': 'Sale',
    'version': '16.0.5.3',

    # any module necessary for this one to work correctly
    'depends': [ 'sale_advertising_order_package'
               , 'sale_advertising_order_digital'],

    #FIXME: 'sale_advertising_order_invoice_customisation' -- does this app needed?

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/invoicing_property_view.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
}