# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2015 Magnus 
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
import odoo.addons.decimal_precision as dp
from bs4 import BeautifulSoup


class Partner(models.Model):
    _inherit = 'res.partner'

    agency_discount = fields.Float('Agency Discount (%)', digits=(16, 2), default=0.0)
    is_ad_agency = fields.Boolean('Agency', default=False)

    @api.model
    def default_get(self, fields):
        """Function gets default values."""
        res = super().default_get(fields)
        res.update({"type": "contact"})
        return res


    def name_get_custom(self, partner_ids):
        if not partner_ids:
            return []
        res = []
        domain = False
        if 'searchFor' in self.env.context:
            domain = self.env.context['searchFor']
        for record in partner_ids:
            str_name = record.name
            if domain:
                if record.zip and domain == 'zip':
                    name = '['+record.zip+']'+str_name
                    res.append((record.id, name))
                elif record.email and domain == 'email':
                    name = '['+record.email+']'+str_name
                    res.append((record.id, name))
                elif record.ref and domain == 'ref':
                    name = '[' + record.ref + ']' + str_name
                    res.append((record.id, name))
                else:
                    res.append((record.id, str_name))
            else:
                res.append((record.id, str_name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        args = args[:]
        ctx = self.env.context.copy()
        ctx.update({'searchFor': 'name'}) #default search for name
        if name:
            partner_ids = self.search([('zip', '=like', name + "%")] + args, limit=limit)
            ctx.update({'searchFor': 'zip'}) if partner_ids else ctx
            if not partner_ids:
                partner_ids = self.search([('email', '=like', name + "%")] + args, limit=limit)
                ctx.update({'searchFor': 'email'}) if partner_ids else ctx
            partner_ids += self.search([('name', operator, name)] + args, limit=limit)
            if not partner_ids and len(name.split()) >= 2:
                # Separating zip, email and name of partner for searching
                operand1, operand2 = name.split(' ', 1)  # name can contain spaces e.g. OpenERP S.A.
                partner_ids = self.search([('zip', operator, operand1), ('name', operator, operand2)] + args,
                                  limit=limit)
                ctx.update({'searchFor': 'zip'}) if partner_ids else ctx
                if not partner_ids:
                    partner_ids = self.search([('email', operator, operand1), ('name', operator, operand2)] + args,
                                      limit=limit)
                    ctx.update({'searchFor': 'email'}) if partner_ids else ctx
            if not partner_ids:
                partner_ids = self.search([('ref', '=like', name + "%")] + args, limit=limit)
                ctx.update({'searchFor': 'ref'}) if partner_ids else ctx
            if partner_ids:
                return self.with_context(ctx).name_get_custom(list(set(partner_ids)))
            else:
                return[]
        return super(Partner, self).name_search(name, args, operator=operator, limit=limit)

    @api.onchange('zip')
    def onchange_zip(self):
        zip = self.zip
        if zip:
            self.zip = zip.replace(" ", "")

