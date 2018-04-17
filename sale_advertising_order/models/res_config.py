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


class Partner(models.Model):
    _inherit = 'res.partner'

    agency_discount = fields.Float('Agency Discount (%)', digits=(16, 2), default=0.0)
    is_ad_agency = fields.Boolean('Agency', default=False)
    adv_sale_order_count = fields.Integer(compute='_compute_adv_sale_order_count', string='# of Sales Order')

    def _compute_adv_sale_order_count(self):
        for partner in self:
            partner.adv_sale_order_count = self.env['sale.order'].search_count(['|', ('published_customer', 'child_of', partner.ids), ('advertising_agency', 'child_of', partner.ids),
                 ('advertising', '=', True), ('state', 'in', ('sale', 'done'))])

    def _compute_sale_order_count(self):
        sale_data = self.env['sale.order'].read_group(domain=[('partner_id', 'child_of', self.ids),('state','not in',('draft','sent','cancel')), ('advertising','=',False)],
                                                      fields=['partner_id'], groupby=['partner_id'])
        # read to keep the child/parent relation while aggregating the read_group result in the loop
        partner_child_ids = self.read(['child_ids'])
        mapped_data = dict([(m['partner_id'][0], m['partner_id_count']) for m in sale_data])
        for partner in self:
            # let's obtain the partner id and all its child ids from the read up there
            partner_ids = filter(lambda r: r['id'] == partner.id, partner_child_ids)[0]
            partner_ids = [partner_ids.get('id')] + partner_ids.get('child_ids')
            # then we can sum for all the partner's child
            partner.sale_order_count = sum(mapped_data.get(child, 0) for child in partner_ids)

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
            if partner_ids:
                return self.with_context(ctx).name_get_custom(list(set(partner_ids)))
            else:
                return[]
        return super(Partner, self).name_search(name, args, operator=operator, limit=limit)


class Company(models.Model):
    _inherit = 'res.company'

    verify_order_setting = fields.Float('Order Amount bigger than', digits=dp.get_precision('Account'))
    verify_discount_setting = fields.Float('Discount (%) bigger than', digits=(16, 2))


    @api.multi
    def write(self, vals):
        res = super(Company, self).write(vals)


        if 'verify_order_setting' in vals or 'verify_discount_setting' in vals:
            for case in self:
                treshold = case.verify_order_setting
                maxdiscount = case.verify_discount_setting
                if treshold == -1.00:
                    self._cr.execute("""
                                 UPDATE sale_order
                                 SET ver_tr_exc=True
                                 WHERE max_discount > %s
                                 AND company_id= %s
                                 AND advertising=True
                                 AND state!='done';

                                 UPDATE sale_order
                                 SET ver_tr_exc=False
                                 WHERE company_id= %s
                                 AND advertising=True
                                 AND max_discount <= %s
                                 AND state!='done'
                                 """, (maxdiscount, case.id, case.id, maxdiscount)
                    )
                else:
                    self._cr.execute("""
                                 UPDATE sale_order
                                 SET ver_tr_exc=True
                                 WHERE (amount_untaxed > %s
                                 OR max_discount > %s)
                                 AND company_id= %s
                                 AND advertising=True
                                 AND state!='done';
                    
                                 UPDATE sale_order
                                 SET ver_tr_exc=False
                                 WHERE amount_untaxed <= %s
                                 AND company_id= %s
                                 AND advertising=True
                                 AND max_discount <= %s
                                 AND state!='done'
                                 """, (treshold, maxdiscount, case.id,  treshold, case.id, maxdiscount )
                    )


        return res

class ActivityLog(models.TransientModel):
    _inherit = "crm.activity.log"

    @api.multi
    def action_log(self):
        result = super(ActivityLog, self).action_log()
        stage_logged = self.env.ref("sale_advertising_order.stage_logged")
        for log in self:
            log.lead_id.write({'stage_id': stage_logged.id, 'next_activity_id': log.next_activity_id.id})
        return result




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
