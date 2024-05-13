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
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from lxml import etree

import logging
_logger = logging.getLogger(__name__)


class Lead(models.Model):
    _inherit = ["crm.lead"]

    published_customer = fields.Many2one('res.partner', 'Advertiser', domain=[('is_customer', '=', True)], ondelete='set null',
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
    is_activity = fields.Boolean(string='Activity', default=False)
    activities_count = fields.Integer("Activities", compute='_compute_activities_count')
    quotations_count = fields.Integer("# of Quotations", compute='_compute_quotations_count')
    adv_quotations_count = fields.Integer("# of Advertising Quotations", compute='_compute_adv_quotations_count')
    name_salesperson = fields.Char('Name Salesperson')
    adv_sale_amount_total= fields.Monetary(compute='_compute_sale_amount_total', string="Sum of Adv. Orders", currency_field='company_currency')

    
    def _compute_quotations_count(self):
        for lead in self:
            lead.quotations_count = self.env['sale.order'].search_count([('opportunity_id', '=', lead.id), ('state','not in',['sale','done','cancel']), ('advertising', '=', False)])

    @api.depends('order_ids')
    def _compute_sale_amount_total(self):
        for lead in self:
            total = adv_total = 0.0
            nbr = 0
            company_currency = lead.company_currency or self.env.user.company_id.currency_id
            for order in lead.order_ids:
                if order.state not in ('sale', 'done', 'cancel'):
                    nbr += 1
                if order.state in ('sale', 'done'):
                    if not order.advertising:
                        total += order.currency_id.compute(order.amount_total, company_currency)
                    if order.advertising:
                        adv_total += order.currency_id.compute(order.amount_untaxed, company_currency)
            lead.sale_amount_total, lead.adv_sale_amount_total, lead.quotation_count = total, adv_total, nbr

    
    def _compute_adv_quotations_count(self):
        for lead in self:
            lead.adv_quotations_count = self.env['sale.order'].search_count([('opportunity_id', '=', lead.id), ('state','not in',('sale','done','cancel')), ('advertising', '=', True)])

    
    def _compute_activities_count(self):
        for lead in self:
            lead.activities_count = self.env['crm.activity.report'].search_count([('lead_id', '=', lead.id), ('subtype_id','not in', ('Lead Created','Stage Changed','Opportunity Won','Discussions','Note','Lead aangemaakt','Fase gewijzigd','Prospect gewonnen','Discussies','Notitie')), ('subtype_id','!=',False)])

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        ctx = self.env.context
        if 'params' in ctx and 'action' in ctx['params']:
            if ctx['params']['action'] == self.env.ref("crm.crm_case_tree_view_oppor").id:
                if groupby and groupby[0] == "stage_id":
                    stage_logged = self.env.ref("sale_advertising_order.stage_logged")
                    states_read = self.env['crm.stage'].search_read([('id', '!=', stage_logged.id)], ['name'])
                    states = [(state['id'], state['name']) for state in states_read]
                    read_group_res = super(Lead, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby)
                    result = []
                    for state_value, state_name in states:
                        res = filter(lambda x: x['stage_id'] == (state_value, state_name), read_group_res)
                        res[0]['stage_id'] = [state_value, state_name]
                        result.append(res[0])
                    return result
        return super(Lead, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby)

    @api.onchange('user_id')
    def _onchange_userid(self):
        self.name_salesperson = self.user_id.name

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
                # 'fax': advertiser.fax, --deprecated
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
                # 'fax': agency.fax, --deprecated
                'zip': agency.zip,
                'function': agency.function,
            }
        return {'value' : values}

    # Backported:
    def _onchange_partner_id_values(self, partner_id):
        """ returns the new values when partner_id has changed """
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)

            partner_name = partner.parent_id.name
            if not partner_name and partner.is_company:
                partner_name = partner.name

            return {
                'partner_name': partner_name,
                'contact_name': partner.name if not partner.is_company else False,
                'title': partner.title.id,
                'street': partner.street,
                'street2': partner.street2,
                'city': partner.city,
                'state_id': partner.state_id.id,
                'country_id': partner.country_id.id,
                'email_from': partner.email,
                'phone': partner.phone,
                'mobile': partner.mobile,
                # 'fax': partner.fax, -- deprecated
                'zip': partner.zip,
                'function': partner.function,
            }
        return {}

    @api.onchange('partner_id')
    def onchange_partner(self):
        if not self.partner_id:
            return {}

        part = self.partner_id
        addr = self.partner_id.address_get(['delivery', 'invoice', 'contact', 'default'])

        if part.type == 'contact':
            contact = self.env['res.partner'].search([('is_company','=', False),('type','=', 'contact'),('parent_id','=', part.id)])
            if len(contact) >=1:
                contact_id = contact[0]
            else:
                contact_id = False
        elif addr['contact'] == addr['default']:
            contact_id = False
        else: contact_id = addr['contact']

        values = self._onchange_partner_id_values(part.id)
        values.update({
            'industry_id': part.industry_id,
            'secondary_industry_ids': [(6, 0, part.secondary_industry_ids.ids)],
            # 'opt_out': part.opt_out, FIXME: Need?
            'partner_name': part.name,
            'partner_contact_id': contact_id,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        })
        return {'value' : values}


    @api.onchange('partner_contact_id')
    def onchange_contact(self):
        if self.partner_contact_id:
            partner = self.partner_contact_id
            values = {
                'contact_name': partner.name,
                'title': partner.title.id,
                'email_from' : partner.email,
                'phone' : partner.phone,
                'mobile' : partner.mobile,
                'function': partner.function,
            }
        else:
            values = {
                'contact_name': False,
                'title': False,
                'email_from': False,
                'phone': False,
                'mobile': False,
                'function': False,
            }
        return {'value' : values}


    
    def _convert_opportunity_data(self, customer, team_id=False):
        crm_stage = self.pool.get('crm.case.stage')

        if not team_id:
            team_id = self.team_id.id if self.team_id else False

            # 'planned_revenue': self.planned_revenue, FIXME: Check if needed.
        val = {
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
            # 'fax': self.fax, --deprecated
            'tag_ids': [(6, 0, [tag_id.id for tag_id in self.tag_ids])],
            'user_id': (self.user_id and self.user_id.id),
            'type': 'opportunity',
            # 'date_action': fields.datetime.now(),
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

        # print "partner_id", partner_id, self
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

    @api.model
    def retrieve_sales_dashboard(self):
        result = super(Lead, self).retrieve_sales_dashboard()
        tasks = self.env['project.task'].search([('user_id', '=', self._uid)])
        result['task'] = {
            'today' :0,
            'next_7_days' :0,
        }
        for task in tasks:
            if task.date_assign and task.date_assign:
                date_assign = fields.Date.from_string(task.date_assign)
                if date_assign == date.today():
                    result['task']['today'] += 1
                if task.date_deadline:
                    date_deadline = fields.Date.from_string(task.date_deadline)
                    if date.today() <= date_deadline <= date.today() + timedelta(days=7):
                        result['task']['next_7_days'] += 1

        current_datetime = datetime.now()
        result['sale_confirmed'] = {
            'this_month': 0,
            'last_month': 0,
        }
        sale_order_domain = [
            ('state', 'in', ['sale', 'done']),
            ('user_id', '=', self.env.uid),
        ]
        sale_data = self.env['sale.order'].search_read(sale_order_domain, ['confirmation_date', 'amount_untaxed'])

        for sale in sale_data:
            if sale['confirmation_date']:
                sale_date = fields.Datetime.from_string(sale['confirmation_date'])
                if sale_date <= current_datetime and sale_date >= current_datetime.replace(day=1):
                    result['sale_confirmed']['this_month'] += sale['amount_untaxed']
                elif sale_date < current_datetime.replace(day=1) and sale_date >= current_datetime.replace(day=1) - relativedelta(months=+1):
                    result['sale_confirmed']['last_month'] += sale['amount_untaxed']
        result['invoiced']['target'] = self.env.user.target_sales_invoiced
        result['reg_quotes'] = {'overdue': 0}
        result['adv_quotes'] = {'overdue': 0}
        quote_domain = [
            ('state', 'not in', ['sale', 'done']),
            ('user_id', '=', self.env.uid),
            ('validity_date', '<', fields.Date.to_string(date.today())),
        ]
        quote_data = self.env['sale.order'].search(quote_domain)
        for quote in quote_data:
            if quote.advertising == False:
                result['reg_quotes']['overdue'] += 1
            elif quote.advertising == True:
                result['adv_quotes']['overdue'] += 1
        return result

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(Lead, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if view_type == 'form':
            ctx = self.env.context
            if 'params' in ctx and 'action' in ctx['params']:
                doc = etree.XML(res['arch'])
                if ctx['params']['action'] == self.env.ref("crm.crm_case_tree_view_oppor").id and doc.xpath("//field[@name='stage_id']"):
                    stage = doc.xpath("//field[@name='stage_id']")[0]
                    stage_logged = self.env.ref("sale_advertising_order.stage_logged")
                    stage.set('domain', "['|', ('team_id', '=', team_id), ('team_id', '=', False), ('id', '!=', %d)]" %(stage_logged.id))

                res['arch'] = etree.tostring(doc)
        return res

    
    def action_set_lost(self):
        lead = super(Lead, self).action_set_lost()
        for rec in self:
            stage_lost = rec.env.ref("sale_advertising_order.stage_lost")
            rec.write({'stage_id': stage_lost.id, 'active': True})
        return lead

#    
#    def redirect_opportunity_view(self):
#        adv_opportunity_view = super(Lead, self).redirect_opportunity_view()
#        form_view = self.env.ref('sale_advertising_order.crm_case_form_view_oppor_advertising')
#        adv_opportunity_view['views'][0] = (form_view.id, 'form')
#        return adv_opportunity_view


class Team(models.Model):
    _inherit = ['crm.team']


    
    def _compute_invoiced(self):
        for team in self:
            confirmed_sales = self.env['sale.order'].search([
                ('state', 'in', ['sale', 'done']),
                ('team_id', '=', team.id),
                ('confirmation_date', '<=', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                ('confirmation_date', '>=', datetime.now().replace(day=1).strftime('%Y-%m-%d %H:%M:%S')),
            ])
            team.invoiced = sum(confirmed_sales.mapped('amount_untaxed'))

    @api.model
    def action_your_pipeline(self):
        action = self.env["ir.actions.actions"]._for_xml_id("crm.crm_lead_action_pipeline")
        user_team_id = self.env.user.sale_team_id.id
        if user_team_id:
            # To ensure that the team is readable in multi company
            user_team_id = self.search([('id', '=', user_team_id)], limit=1).id
        else:
            user_team_id = self.search([], limit=1).id
            action['help'] = _("""<p class='o_view_nocontent_smiling_face'>Add new opportunities</p><p>
    Looks like you are not a member of a Sales Team. You should add yourself
    as a member of one of the Sales Team.
</p>""")
            if user_team_id:
                action['help'] += _(
                    "<p>As you don't belong to any Sales Team, Odoo opens the first one by default.</p>")

        action_context = safe_eval(action['context'], {'uid': self.env.uid})
        if user_team_id:
            action_context['default_team_id'] = user_team_id

        # Load Views for Advertising:
        if self._context.get('advertising', False):
            form_view_id = self.env.ref('crm.crm_case_form_view_oppor_advertising').id
            action_context['default_advertising'] = True
            # action_domain.append(('is_activity', '=', False))

        if self._context.get('search_default_partner_id', False):
            action_context['search_default_partner_id'] = self._context['active_id']

        # action['views'] = [
        #     [kanb_view_id, 'kanban'],
        #     [tree_view_id, 'tree'],
        #     [form_view_id, 'form'],
        #     [False, 'graph'],
        #     [False, 'calendar'],
        #     [False, 'pivot']
        # ]
        print ('------action--------',action)
        action['context'] = action_context
        return action

#     @api.model
#     def action_your_pipeline(self):
#         action = self.env.ref('crm.crm_case_tree_view_oppor').read()[0]
#         user_team_id = self.env.user.sale_team_id.id
#         if not user_team_id:
#             user_team_id = self.search([], limit=1).id
#             action['help'] = """<p class='oe_view_nocontent_create'>Click here to add new opportunities</p><p>
#     Looks like you are not a member of a sales team. You should add yourself
#     as a member of one of the sales teams.
# </p>"""
#             if user_team_id:
#                 action['help'] += "<p>As you don't belong to any sales team, Odoo opens the first one by default.</p>"
#
#         action_context = safe_eval(action['context'], {'uid': self.env.uid})
#         if user_team_id:
#             action_context['default_team_id'] = user_team_id
#
#         action_domain = safe_eval(action['domain'])
#
#         tree_view_id = self.env.ref('crm.crm_case_tree_view_oppor').id
#         form_view_id = self.env.ref('crm.crm_case_form_view_oppor').id
#         kanb_view_id = self.env.ref('crm.crm_case_kanban_view_leads').id
#
#         # Load Views for Advertising:
#         if self._context.get('advertising', False):
#             form_view_id = self.env.ref('crm.crm_case_form_view_oppor_advertising').id
#             action_context['default_advertising'] = True
#             action_domain.append(('is_activity','=', False))
#
#         if self._context.get('search_default_partner_id', False):
#             action_context['search_default_partner_id'] = self._context['active_id']
#
#         action['views'] = [
#                 [kanb_view_id, 'kanban'],
#                 [tree_view_id, 'tree'],
#                 [form_view_id, 'form'],
#                 [False, 'graph'],
#                 [False, 'calendar'],
#                 [False, 'pivot']
#             ]
#         action['context'] = action_context
#         action['domain'] = action_domain
#
#         return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

