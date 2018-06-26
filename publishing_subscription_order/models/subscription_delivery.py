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
    start_date = fields.Date('Start Date', default=fields.Date.today,  readonly=True, states={'draft': [('readonly', False)]})
    end_date = fields.Date('End Date', default=fields.Date.today,  readonly=True, states={'draft': [('readonly', False)]})
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
            issueObj = advIssue.search([('parent_id','in', line_obj.title.ids),('issue_date','<=',self.end_date),('issue_date','>=',self.start_date)])
            if issueObj:
                item['delivery_id'] = self.id
                item['partner_id'] = line_obj.order_id.partner_shipping_id.id
                item['title'] = line_obj.title.id
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
            ('start_date', '<=', self.end_date),
            ('end_date', '>=', self.start_date),
            ('company_id', '=', self.company_id.id),
            ('subscription', '=', True),
            ('state', '=', 'sale'),
            ('title', '!=', False),
        ]
        self_sols = self.delivery_list.mapped('sub_order_line')
        sub_list_objs = self.search([('start_date', '<=', self.end_date), ('end_date', '>=', self.start_date),('id','!=',self.id),('company_id','=',self.company_id.id),('state','!=','cancel')])
        other_sols = []
        for found_obj in sub_list_objs:
            other_sols += found_obj.delivery_list.mapped('sub_order_line').ids
        if other_sols or self_sols:
            exists_sols = other_sols+self_sols.ids
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

    @api.multi
    def print_xls_report(self):
        return self.env['report'].get_action(self, 'report_subscription_delivery.xlsx')

class SubscriptionDeliveryList(models.Model):
    _name = 'subscription.delivery.list'
    _description = 'Subscription Delivery List'
    _rec_name = 'subscription_number'

    delivery_id = fields.Many2one('subscription.delivery', string='Delivery Reference', required=True, ondelete='cascade', index=True, copy=False)
    start_date = fields.Date(related='delivery_id.start_date',string='Start Date',store=True, readonly=True)
    end_date = fields.Date(related='delivery_id.end_date',string='End Date',store=True, readonly=True)
    company_id = fields.Many2one(related='delivery_id.company_id', string='Company', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Delivery Address')
    title = fields.Many2one('sale.advertising.issue', string='Title')
    issue_ids = fields.Many2many('sale.advertising.issue', 'delivery_list_issue_adv_issue_rel', 'delivery_list_id', 'adv_issue_id', string='Issues')
    sub_order_line = fields.Many2one('sale.order.line', string='Subscription order line')
    subscription_number = fields.Many2one(related='sub_order_line.order_id',string='Subscription Number', store=True, readonly=True)
    product_uom_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_list_ids = fields.One2many('subscription.delivery.list','subscription_number',string='Delivery List', copy=False)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    delivery_list_ids = fields.One2many('subscription.delivery.list','sub_order_line',string='Delivery List', copy=False)





