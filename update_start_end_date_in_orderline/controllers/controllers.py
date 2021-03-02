# -*- coding: utf-8 -*-
from odoo import http

# class Magnus/vertical-publishing/updateStartEndDateInOrderline(http.Controller):
#     @http.route('/magnus/vertical-publishing/update_start_end_date_in_orderline/magnus/vertical-publishing/update_start_end_date_in_orderline/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/magnus/vertical-publishing/update_start_end_date_in_orderline/magnus/vertical-publishing/update_start_end_date_in_orderline/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('magnus/vertical-publishing/update_start_end_date_in_orderline.listing', {
#             'root': '/magnus/vertical-publishing/update_start_end_date_in_orderline/magnus/vertical-publishing/update_start_end_date_in_orderline',
#             'objects': http.request.env['magnus/vertical-publishing/update_start_end_date_in_orderline.magnus/vertical-publishing/update_start_end_date_in_orderline'].search([]),
#         })

#     @http.route('/magnus/vertical-publishing/update_start_end_date_in_orderline/magnus/vertical-publishing/update_start_end_date_in_orderline/objects/<model("magnus/vertical-publishing/update_start_end_date_in_orderline.magnus/vertical-publishing/update_start_end_date_in_orderline"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('magnus/vertical-publishing/update_start_end_date_in_orderline.object', {
#             'object': obj
#         })