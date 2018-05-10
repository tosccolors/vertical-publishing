# -*- coding: utf-8 -*-
{
    'name': 'Mass Mailing Campaigns Details',
    'summary': '[Supporting Module] to the Mass Mailing Campaigns',
    'description': """
[Supporting Module] to the Mass Mailing Campaigns
=================================================
Adds the following fields to the mail.mass_mailing.campaign object:
---------------------------------------------------------------------
* Field name = Description, field type = text
* Field name = Start date, field type = date
* Fiels name = End date, field type = date
* Field name = Budgeted costs, field type = monetary
* Field name = Actual costs, field type = monetary
* Field name = Budgeted result, field type = text
* Field name = Actual result, field type = text
    """,
    'version': '2.0',
    'sequence': 110,
    'website': 'https://www.odoo.com/page/mailing',
    'category': 'Marketing',
    'depends': [
        'mass_mailing',
    ],
    'data': [
        'views/mass_mailing_views.xml'
    ],
    'demo' : [],
    'installable': True,
    'images': [],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
