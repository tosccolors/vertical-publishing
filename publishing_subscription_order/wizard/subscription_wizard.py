# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2016 Magnus (<http://www.magnus.nl>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, exceptions, models, _

class SubscriptionConfig(models.TransientModel):
    _name = "subscription.config.wizard"
    _description = "Subscription Config"

    name = fields.Char('Message')

    @api.multi
    def genrated_message(self, message, name='Message/Summary'):
        new_rec = self.create({'name': message})
        return {
            'name': name,
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'subscription.config.wizard',
            'res_id': new_rec.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
        }

    def generate_delivery_title(self):
        DeliveryTitle = self.env['subscription.title.delivery']
        totrec = len(DeliveryTitle.search([]))
        DeliveryTitle.generate_delivery_title()
        totrec = abs(len(DeliveryTitle.search([])) - totrec) if totrec else len(DeliveryTitle.search([]))
        msg = "%s new delivery titles has been created" % str(totrec)
        return self.genrated_message(msg)

    def generate_all_delivery_list(self):
        DeliveryList = self.env['subscription.delivery.list']
        totrec = len(DeliveryList.search([]))
        self.env['subscription.title.delivery'].generate_all_delivery_list()
        totrec = abs(len(DeliveryList.search([])) - totrec) if totrec else len(DeliveryList.search([]))
        msg = "%s new delivery lists has been created" % str(totrec)
        return self.genrated_message(msg)

    def generate_all_delivery_lines(self):
        DeliveryLine = self.env['subscription.delivery.line']
        totrec = len(DeliveryLine.search([]))
        self.env['subscription.delivery.list'].generate_all_delivery_lines()
        totrec = abs(len(DeliveryLine.search([])) - totrec) if totrec else len(DeliveryLine.search([]))
        msg = "%s new delivery lines has been created" % str(totrec)
        return self.genrated_message(msg)

class SubscriptionMultiWizard(models.TransientModel):

    _name = "subscription.multi.wizard"
    _description = "Create delivery list/delivery lines"

    @api.multi
    def confirm(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        active_model = context.get('active_model', False) or False
        if active_model:
            if active_model == 'subscription.title.delivery':
                title = self.env['subscription.title.delivery'].browse(active_ids)
                title.generate_delivery_list()
            if active_model == 'subscription.delivery.list':
                lists = self.env['subscription.delivery.list'].browse(active_ids)
                lists.generate_delivery_lines()

        return {'type': 'ir.actions.act_window_close'}