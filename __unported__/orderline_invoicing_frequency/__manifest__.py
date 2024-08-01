# -*- encoding: utf-8 -*-
{
    'name': 'orderline_invoicing_frequency',
    'version': '1.0',
    'category': 'Sale',
    'description': """
This module allows you to set partner invoicing frequency for advertising sale order lines.
===========================================================================================
    """,
    'author': 'Magnus - Willem Hulshof',
    'website': 'http://www.magnus.nl',
    'depends': [
                'sale_advertising_order',
                'mass_mail_invoice'
                ],
    'data': [
                "views/res_partner_view.xml"
             ],
    'installable': True
}