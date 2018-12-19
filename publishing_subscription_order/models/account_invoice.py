# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016 Magnus NL (<http://magnus.nl>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from odoo import api, fields, models, _



class Invoice(models.Model):
    """ Inherits invoice and adds ad boolean to invoice to flag Subscription-invoices"""
    _inherit = 'account.invoice'

    subs = fields.Boolean(related='invoice_line_ids.subs', string='subs', help="It indicates that the invoice is an Subscription Invoice.", store=True)



class InvoiceLine(models.Model):
    """ Inherits invoice.line and adds Subscription boolean to invoice """
    _inherit = 'account.invoice.line'


    subs = fields.Boolean(related='so_line_id.subscription', string='Subs',
                       store=True,
                                help="It indicates that the invoice line is "
                                     "from an Subscription Invoice.")

