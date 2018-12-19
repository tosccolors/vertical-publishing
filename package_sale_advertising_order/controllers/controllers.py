# -*- coding: utf-8 -*-
from odoo import http

# class PackageSaleAdvertisingOrder(http.Controller):
#     @http.route('/package_sale_advertising_order/package_sale_advertising_order/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/package_sale_advertising_order/package_sale_advertising_order/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('package_sale_advertising_order.listing', {
#             'root': '/package_sale_advertising_order/package_sale_advertising_order',
#             'objects': http.request.env['package_sale_advertising_order.package_sale_advertising_order'].search([]),
#         })

#     @http.route('/package_sale_advertising_order/package_sale_advertising_order/objects/<model("package_sale_advertising_order.package_sale_advertising_order"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('package_sale_advertising_order.object', {
#             'object': obj
#         })