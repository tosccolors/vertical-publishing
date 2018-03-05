# -*- coding: utf-8 -*-
import werkzeug
from werkzeug import url_encode
from odoo.http import request
from odoo.addons.mail.controllers.main import MailController

class ExtensionMailController(MailController):

    @classmethod
    def _redirect_to_record(cls, model, res_id):
        response = super(ExtensionMailController, cls)._redirect_to_record(model, res_id)
        if model == 'sale.order':
            if request.env[model].sudo().search([('id', '=', res_id), ('advertising', '=', True)]):
                url_params = {
                    'view_type': 'form',
                    'model': model,
                    'id': res_id,
                    'active_id': res_id,
                    'view_id': request.env.ref('sale_advertising_order.view_order_form_advertising').id or False,
                    'action': request.env.ref('sale_advertising_order.action_orders_advertising').id or False,
                }
                url = '/web?#%s' % url_encode(url_params)
                return werkzeug.utils.redirect(url)
        return response