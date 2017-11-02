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
from odoo.tools.safe_eval import safe_eval
from odoo.tools import email_re, email_split


class Lead(models.Model):
    _inherit = ["crm.lead"]

    published_customer = fields.Many2one('res.partner', 'Advertiser', domain=[('customer', '=', True)], ondelete='set null',
                                        track_visibility='onchange', index=True,
                                        help="Linked Advertiser (optional). ")
    partner_id = fields.Many2one('res.partner', 'Payer', ondelete='set null', track_visibility='onchange',
                                        index=True, help="Linked Payer (optional).")
    partner_invoice_id = fields.Many2one('res.partner', 'Payer Invoice Address', ondelete='set null',
                                      index=True, help="Linked partner (optional). Usually created when converting the lead.")
    partner_shipping_id = fields.Many2one('res.partner', 'Payer Delivery Address', ondelete='set null',
                                          index=True, help="Linked partner (optional). Usually created when converting the lead.")
    partner_contact_id = fields.Many2one('res.partner', 'Contact Person', ondelete='set null', track_visibility='onchange',
                                    index=True, help="Linked Contact Person (optional). Usually created when converting the lead.")
    ad_agency_id = fields.Many2one('res.partner', 'Agency', ondelete='set null', track_visibility='onchange',
                                  index=True, help="Linked Advertising Agency (optional). Usually created when converting the lead.")
    partner_acc_mgr = fields.Many2one(related='partner_id.user_id', relation='res.users',
                                      string='Account Manager', store=True)
    advertising = fields.Boolean('Advertising', default=False)



    @api.onchange('published_customer')
    def onchange_published_customer(self):
        values = {}
        if self.published_customer:
            advertiser = self.published_customer #self.pool.get('res.partner').browse(cr, uid, published_customer, context=context)
            values = {
                'partner_name': advertiser.name,
                'partner_id': self.published_customer.id,
                'title': advertiser.title.id,
                'email_from': advertiser.email,
                'phone': advertiser.phone,
                'mobile': advertiser.mobile,
                'fax': advertiser.fax,
                'zip': advertiser.zip,
                'function': advertiser.function,
                'ad_agency_id': False,
            }
        return {'value' : values }

    @api.onchange('ad_agency_id')
    def onchange_agency(self):
        values = {}
        if self.ad_agency_id:
            agency = self.ad_agency_id #self.pool.get('res.partner').browse(cr, uid, ad_agency, context=context)
            values = {
                'partner_id': agency.id,
                'title': agency.title and agency.title.id or False,
                'email_from': agency.email,
                'phone': agency.phone,
                'mobile': agency.mobile,
                'fax': agency.fax,
                'zip': agency.zip,
                'function': agency.function,
            }
        return {'value' : values}

    @api.onchange('partner_id')
    def onchange_partner(self):
        if not self.partner_id:
            return {}

        part = self.partner_id
        addr = self.partner_id.address_get(['delivery', 'invoice', 'contact'])
        values = {}

        if part.type == 'contact':
            contact = self.env['res.partner'].search([('is_company','=', False),('type','=', 'contact'),('parent_id','=', part.id)])
            if len(contact) >=1:
                contact_id = contact[0]
            else:
                contact_id = False
        elif addr['contact'] == addr['default']:
            contact_id = False
        else: contact_id = addr['contact']
        invoice = self.env['res.partner'].browse(addr['invoice'])

        values = {
            'street': invoice.street,
            'street2': invoice.street2,
            'city': invoice.city,
            'state_id': invoice.state_id.id,
            'country_id': invoice.country_id.id,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'partner_contact_id': contact_id,
        }
        return {'value' : values}


    @api.onchange('partner_contact_id')
    def onchange_contact(self):
        values = {}
        if self.partner_contact_id:
            partner = self.partner_contact_id
            values = {
                'contact_name': partner.name,
                'title': partner.title.id,
                'email_from' : partner.email,
                'phone' : partner.phone,
                'mobile' : partner.mobile,
                'fax' : partner.fax,
                'function': partner.function,
            }
        else:
            values['contact_name'] = False
        return {'value' : values}


    @api.multi
    def _convert_opportunity_data(self, customer, team_id=False):
        crm_stage = self.pool.get('crm.case.stage')

        if not team_id:
            team_id = self.team_id.id if self.team_id else False

        val = {
            'planned_revenue': self.planned_revenue,
            'probability': self.probability,
            'name': self.name,
            'partner_name': self.partner_name,
            'contact_name': self.contact_name,
            'street': self.street,
            'street2': self.street2,
            'zip': self.zip,
            'city': self.city,
            'state_id': self.state_id.id,
            'country_id': self.country_id.id,
            'title': self.title.id,
            'email_from': self.email_from,
            'function': self.function,
            'phone': self.phone,
            'mobile': self.mobile,
            'fax': self.fax,
            'tag_ids': [(6, 0, [tag_id.id for tag_id in self.tag_ids])],
            'user_id': (self.user_id and self.user_id.id),
            'type': 'opportunity',
            'date_action': fields.datetime.now(),
            'date_open': fields.datetime.now(),

        }
        if customer:
            val['published_customer'] = customer.id,
        if self.partner_id:
            val['partner_id'] = self.partner_id.id,
        if self.ad_agency_id:
            val['ad_agency_id'] = self.ad_agency_id.id,
        if self.partner_invoice_id:
            val['partner_invoice_id'] = self.partner_invoice_id.id,
        if self.partner_shipping_id:
            val['partner_shipping_id'] = self.partner_shipping_id.id,
        if self.partner_contact_id:
            val['partner_contact_id'] = self.partner_contact_id.id,

        if not self.stage_id:
            stage = self._stage_find(team_id=team_id)
            val['stage_id'] = stage.id
            if stage:
                val['probability'] = stage.probability
        return val

    @api.multi
    def handle_partner_assignation(self,  action='create', partner_id=False):
        """ Handle partner assignation during a lead conversion.
            if action is 'create', create new partner with contact and assign lead to new partner_id.
            otherwise assign lead to the specified partner_id

            :param list ids: leads/opportunities ids to process
            :param string action: what has to be done regarding partners (create it, assign an existing one, or nothing)
            :param int partner_id: partner to assign if any
            :return dict: dictionary organized as followed: {lead_id: partner_assigned_id}
        """
        partner_ids = {}
        for lead in self:
            if lead.partner_id:
                partner_ids[lead.id] = lead.partner_id.id
                continue
            if action in ('create', 'nothing'):
                partner = lead._create_lead_partner()
                partner_id = partner.id
                partner.team_id = lead.team_id
            if partner_id:
                lead.partner_id = partner_id
            partner_ids[lead.id] = partner_id
        return partner_ids

    @api.multi
    def handle_partner_assignation(self,  action='create', partner_id=False):
        """ Handle partner assignation during a lead conversion.
            if action is 'create', create new partner with contact and assign lead to new partner_id.
            otherwise assign lead to the specified partner_id

            :param list ids: leads/opportunities ids to process
            :param string action: what has to be done regarding partners (create it, assign an existing one, or nothing)
            :param int partner_id: partner to assign if any
            :return dict: dictionary organized as followed: {lead_id: partner_assigned_id}
        """
        partner_ids = {}
        for lead in self:
            if lead.partner_id:
                partner_ids[lead.id] = lead.partner_id.id
                continue
            if action == 'create':
                partner = lead._create_lead_partner()
                partner_id = partner.id
                partner.team_id = lead.team_id
            if partner_id:
                lead.partner_id = partner_id
                lead.published_customer = partner_id
            partner_ids[lead.id] = partner_id
        return partner_ids



    # -- deep added
    @api.model
    def _get_duplicated_leads_by_emails(self, partner_id, email, include_lost=False):
        """
        Search for opportunities that have   the same partner and that arent done or cancelled
        """

        print "partner_id", partner_id, self
        partnerDict = self._get_partnerDetails(partner_id)


        final_stage_domain = [('stage_id.probability', '<', 100), '|', ('stage_id.probability', '>', 0), ('stage_id.sequence', '<=', 1)]
        partner_match_domain = []
        for email in set(email_split(email) + [email]):
            partner_match_domain.append(('email_from', '=ilike', email))
        if partnerDict:
            partner_match_domain.append(('partner_id', '=', partnerDict['partner_id']))
            partner_match_domain.append(('published_customer', '=', partnerDict['advertiser']))
        partner_match_domain = ['|'] * (len(partner_match_domain) - 1) + partner_match_domain
        if not partner_match_domain:
            return []
        domain = partner_match_domain
        if not include_lost:
            domain += final_stage_domain

        return self.search(domain)


    @api.model
    def _get_partnerDetails(self, partnerID=False):

        if not partnerID: return {}

        Partner = self.env['res.partner'].browse(partnerID)
        lead = self

         # a partner is set already in Lead
        if lead.partner_id and lead.published_customer:
            res = {'partner_id':lead.partner_id.id,
                   'agent': lead.ad_agency_id.id if lead.partner_id.is_ad_agency else False,
                   'advertiser': lead.published_customer.id
                   }

        elif Partner.is_ad_agency:
            res = {'partner_id' : Partner.id,
                   'agent' : Partner.id,
                   'advertiser' : False
                   }
        elif not Partner.is_ad_agency:
            res = {'partner_id' : Partner.id,
                   'agent' : False,
                   'advertiser' : Partner.id
                   }

        return res




class Team(models.Model):
    _inherit = ['crm.team']


    @api.model
    def action_your_pipeline(self):
        action = self.env.ref('crm.crm_lead_opportunities_tree_view').read()[0]
        user_team_id = self.env.user.sale_team_id.id
        if not user_team_id:
            user_team_id = self.search([], limit=1).id
            action['help'] = """<p class='oe_view_nocontent_create'>Click here to add new opportunities</p><p>
    Looks like you are not a member of a sales team. You should add yourself
    as a member of one of the sales team.
</p>"""
            if user_team_id:
                action['help'] += "<p>As you don't belong to any sales team, Odoo opens the first one by default.</p>"

        action_context = safe_eval(action['context'], {'uid': self.env.uid})
        if user_team_id:
            action_context['default_team_id'] = user_team_id

        action_domain = safe_eval(action['domain'])

        tree_view_id = self.env.ref('crm.crm_case_tree_view_oppor').id
        form_view_id = self.env.ref('crm.crm_case_form_view_oppor').id
        kanb_view_id = self.env.ref('crm.crm_case_kanban_view_leads').id

        # Load Views for Advertising:
        if self._context.get('advertising', False):
            form_view_id = self.env.ref('sale_advertising_order.crm_case_form_view_oppor_advertising').id
            action_context['default_advertising'] = True
            action_domain.append(('advertising','=', True))
        else:
            action_domain.append(('advertising','=', False))

        action['views'] = [
                [kanb_view_id, 'kanban'],
                [tree_view_id, 'tree'],
                [form_view_id, 'form'],
                [False, 'graph'],
                [False, 'calendar'],
                [False, 'pivot']
            ]
        action['context'] = action_context
        action['domain'] = action_domain

        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

