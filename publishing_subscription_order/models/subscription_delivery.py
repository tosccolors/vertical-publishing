# -*- encoding: utf-8 -*-

from odoo import api, fields, exceptions, models, _
import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta
from dateutil import relativedelta

class SubscriptionDelivery(models.Model):
    _name='subscription.delivery'
    _inherit = ['mail.thread']
    _description = 'Subscription Delivery'
    
    name = fields.Char(string='Delivery Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    delivery_date = fields.Date('Delivery Date', default=fields.Date.today)
    delivery_list = fields.One2many('subscription.delivery.list','delivery_id',string='Delivery List', states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.order'))

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'subscription.delivery') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('subscription.delivery') or _('New')
        result = super(SubscriptionDelivery, self).create(vals)
        return result

    @api.multi
    def prepare_delivery_list(self, sols):
        advIssue = self.env['sale.advertising.issue']
        deliveryList = self.env['subscription.delivery.list']

        for line_obj in sols:

            if line_obj.delivered_issues >= line_obj.number_of_issues:
                continue

            item={}
            issueObj = advIssue.search([('parent_id','in', line_obj.title_ids.ids),('issue_date','=',self.delivery_date)])
            if issueObj:
                item['delivery_id'] = self.id
                item['partner_id'] = line_obj.order_id.partner_shipping_id.id
                item['title_ids'] = [(6,0,line_obj.title_ids.ids)]
                item['issue_ids'] = [(6,0,issueObj.ids)]
                item['sub_order_line'] = line_obj.id
                item['product_uom_qty'] = line_obj.product_uom_qty
                deliveryList.create(item)

                #update number of issues to subscription order line
                tot_issue = line_obj.delivered_issues + len(issueObj.ids)
                line_obj.write({'delivered_issues':tot_issue})

        return True


    @api.multi
    def get_delivery_lists(self):
        orderline = self.env['sale.order.line']
        domain = [
            ('start_date', '<=', self.delivery_date),
            ('end_date', '>=', self.delivery_date),
            ('company_id', '=', self.company_id.id),
            ('subscription', '=', True),
            ('state', '=', 'sale'),
        ]
        self_sols = self.delivery_list.mapped('sub_order_line')
        sub_list_objs = self.search([('delivery_date','=',self.delivery_date),('id','!=',self.id),('company_id','=',self.company_id.id),('state','!=','cancel')])
        other_sols = sub_list_objs.delivery_list.mapped('sub_order_line')
        if other_sols or self_sols:
            exists_sols = other_sols.ids+self_sols.ids
            domain += [('id','not in',exists_sols)]

        sols = orderline.search(domain)
        self.prepare_delivery_list(sols)
        if self.state != 'progress':
            return self.write({'state': 'progress'})
        return True

    @api.multi
    def action_done(self):
        return self.write({'state': 'done'})

    @api.multi
    def action_cancel(self):
        return self.write({'state': 'cancel'})


class SubscriptionDeliveryList(models.Model):
    _name = 'subscription.delivery.list'
    _description = 'Subscription Delivery List'
    _rec_name = 'delivery_date'

    delivery_id = fields.Many2one('subscription.delivery', string='Delivery Reference', required=True, ondelete='cascade', index=True, copy=False)
    delivery_date = fields.Date(related='delivery_id.delivery_date',string='Delivery Date',store=True, readonly=True)
    company_id = fields.Many2one(related='delivery_id.company_id', string='Company', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Delivery Address')
    title_ids = fields.Many2many('sale.advertising.issue', 'delivery_list_title_adv_issue_rel', 'delivery_list_id', 'adv_issue_id',string='Title')
    issue_ids = fields.Many2many('sale.advertising.issue', 'delivery_list_issue_adv_issue_rel', 'delivery_list_id', 'adv_issue_id', string='Issues')
    sub_order_line = fields.Many2one('sale.order.line', string='Subscription order line')
    subscription_number = fields.Many2one(related='sub_order_line.order_id',string='Subscription Number', store=True, readonly=True)
    product_uom_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)





