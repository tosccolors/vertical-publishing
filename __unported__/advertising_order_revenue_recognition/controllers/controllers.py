# -*- coding: utf-8 -*-
from odoo import http

# class AdvertisingOrderPrintRevenue(http.Controller):
#     @http.route('/advertising_order_print_revenue/advertising_order_print_revenue/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/advertising_order_print_revenue/advertising_order_print_revenue/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('advertising_order_print_revenue.listing', {
#             'root': '/advertising_order_print_revenue/advertising_order_print_revenue',
#             'objects': http.request.env['advertising_order_print_revenue.advertising_order_print_revenue'].search([]),
#         })

#     @http.route('/advertising_order_print_revenue/advertising_order_print_revenue/objects/<model("advertising_order_print_revenue.advertising_order_print_revenue"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('advertising_order_print_revenue.object', {
#             'object': obj
#         })