# -*- coding: utf-8 -*-
from odoo import http

# class SubscriptionBaarn(http.Controller):
#     @http.route('/subscription_baarn/subscription_baarn/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/subscription_baarn/subscription_baarn/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('subscription_baarn.listing', {
#             'root': '/subscription_baarn/subscription_baarn',
#             'objects': http.request.env['subscription_baarn.subscription_baarn'].search([]),
#         })

#     @http.route('/subscription_baarn/subscription_baarn/objects/<model("subscription_baarn.subscription_baarn"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('subscription_baarn.object', {
#             'object': obj
#         })