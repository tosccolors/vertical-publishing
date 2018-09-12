# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

class Lead2OpportunityPartner(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'

    @api.depends('partner_id')
    def _get_partner(self):
        self.partner_dummy = self.partner_id.id

    # action = fields.Selection([
    #         ('exist', 'Link to an existing customer'),
    #         ('nothing', 'Do not link to a customer')
    #     ], 'Related Customer', required=True, default='nothing')

    agent = fields.Many2one('res.partner', 'Agency')
    advertiser = fields.Many2one('res.partner', 'Advertiser')
    partner_id = fields.Many2one('res.partner', 'Payer')

    partner_dummy = fields.Many2one('res.partner', string='Payer', readonly=True)

    update1 = fields.Boolean('Update Advertiser/Agency', default=False,
                             help='Check this to be able to choose (other) Advertiser/Agency.')



    @api.onchange('action')
    def onchange_action(self):
        res = {}
        if self.action != 'exist':
            res = {
                'partner_id': False,
                'agent': False,
                'advertiser': False,
            }
        else:
            partner = self._find_matching_partner()

            lead = self.env['crm.lead'].browse(self._context['active_id'])
            res = lead._get_partnerDetails(lead.partner_id.id)

        return {'value': res}


    @api.onchange('advertiser', 'update1')
    def onchange_advertiser(self):
        if not self.update1:
            return {'value': {}}
        data = {'partner_id': self.advertiser, 'agent': False, 'partner_dummy': self.advertiser}
        return {'value': data}


    @api.onchange('agent', 'update1')
    def onchange_agent(self):
        if not self.update1:
            return {'value': {}}
        if self.agent:
            data = {'partner_id': self.agent, 'partner_dummy': self.agent}
            return {'value': data}
        return {'value': {}}


    @api.model
    def default_get(self, fields):
        """ Default get for name, opportunity_ids.
            If there is an exisitng partner link to the lead, find all existing
            opportunities links with this partner to merge all information together
        """
        result = super(Lead2OpportunityPartner, self).default_get(fields)

        if self._context.get('active_id'):
            tomerge = {int(self._context['active_id'])}

            partner_id = result.get('partner_id', {})
            lead = self.env['crm.lead'].browse(self._context['active_id'])
            email = lead.partner_id.email if lead.partner_id else lead.email_from

            partnerDict = lead._get_partnerDetails(partner_id)

            tomerge.update(self._get_duplicated_leads(partner_id, email, include_lost=True).ids)

            if 'action' in fields and not result.get('action'):
                result['action'] = 'exist' if partner_id else 'nothing'
            if 'partner_id' in fields:
                result['partner_id'] = partner_id
            if 'advertiser' in fields:
                result.update({'advertiser': partnerDict.get('advertiser', False)})
            if 'agent' in fields:
                result.update({'agent': partnerDict.get('advertiser', False)})
            if 'name' in fields:
                result['name'] = 'merge' if len(tomerge) >= 2 else 'convert'
            if 'opportunity_ids' in fields and len(tomerge) >= 2:
                result['opportunity_ids'] = list(tomerge)
            if lead.user_id:
                result['user_id'] = lead.user_id.id
            if lead.team_id:
                result['team_id'] = lead.team_id.id
            if not partner_id and not lead.contact_name:
                result['action'] = 'nothing'
        return result


    @api.model
    def _find_matching_partner(self):
        """ Try to find a matching partner regarding the active model data, like
            the customer's name, email, phone number, etc.
            :return int partner_id if any, False otherwise
        """
        # active model has to be a lead
        if self._context.get('active_model') != 'crm.lead' or not self._context.get('active_id'):
            return False

        lead = self.env['crm.lead'].browse(self._context.get('active_id'))

        # find the best matching partner for the active model
        Partner = self.env['res.partner']
        if lead.partner_id and lead.published_customer:  # a partner is set already
            return lead.partner_id.id

        if lead.email_from:  # search through the existing partners based on the lead's email
            partner = Partner.search([('email', '=', lead.email_from)], limit=1)
            return partner.id

        if lead.partner_name:  # search through the existing partners based on the lead's partner or contact name
            partner = Partner.search([('name', 'ilike', '%' + lead.partner_name + '%')], limit=1)
            return partner.id

        if lead.contact_name:
            partner = Partner.search([('name', 'ilike', '%' + lead.contact_name+'%')], limit=1)
            return partner.id

        return False

class Lead2OpportunityMassConvert(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner.mass'

    force_assignation = fields.Boolean('Force assignation', default=True, help='If unchecked, this will leave the salesman of duplicated opportunities')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
