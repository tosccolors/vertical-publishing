# -*- coding: utf-8 -*-
from odoo import http

# class AdvertisingOrderPrintDeferredCosts(http.Controller):
#     @http.route('/advertising_order_print_deferred_costs/advertising_order_print_deferred_costs/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/advertising_order_print_deferred_costs/advertising_order_print_deferred_costs/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('advertising_order_print_deferred_costs.listing', {
#             'root': '/advertising_order_print_deferred_costs/advertising_order_print_deferred_costs',
#             'objects': http.request.env['advertising_order_print_deferred_costs.advertising_order_print_deferred_costs'].search([]),
#         })

#     @http.route('/advertising_order_print_deferred_costs/advertising_order_print_deferred_costs/objects/<model("advertising_order_print_deferred_costs.advertising_order_print_deferred_costs"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('advertising_order_print_deferred_costs.object', {
#             'object': obj
#         })