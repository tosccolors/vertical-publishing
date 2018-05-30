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


from odoo import api, fields, models, _

class Lead(models.Model):
    _inherit = ["crm.lead"]

    subs_quotations_count = fields.Integer("# of Subscription Quotations", compute='_compute_subs_quotations_count')

    @api.multi
    def _compute_subs_quotations_count(self):
        for lead in self:
            lead.subs_quotations_count = self.env['sale.order'].search_count([('opportunity_id', '=', lead.id), ('state','not in',('sale','done')), ('subscription', '=', True)])

    # Adding ('subscription', '=', False) in filter criteria to filter subscription records in regular quotations smart button
    @api.multi
    def _compute_quotations_count(self):
        for lead in self:
            lead.quotations_count = self.env['sale.order'].search_count([('opportunity_id', '=', lead.id), ('state','not in',('sale','done')), ('advertising', '=', False), ('subscription', '=', False)])