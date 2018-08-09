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
    type = fields.Many2one('delivery.list.type', string='Type', readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    delivery_list = fields.One2many('subscription.delivery.list', 'delivery_id', string='Delivery List', copy=False)
    title_ids = fields.Many2many('sale.advertising.issue', 'delivery_list_adv_issue_title_rel', 'delivery_list_id','adv_issue_id', 'Titles', readonly=True, states={'draft': [('readonly', False)]})
    issue_ids = fields.Many2many('sale.advertising.issue','delivery_list_adv_issue_rel', 'delivery_list_id', 'adv_issue_id',  'Issues', readonly=True, states={'draft': [('readonly', False)]})
    weekday_ids = fields.Many2many('week.days', 'weekday_delivery_list_rel', 'delivery_list_id', 'weekday_id', 'Weekdays', readonly=True, states={'draft': [('readonly', False)]})
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

    @api.onchange('title_ids','issue_ids','weekday_ids')
    def onchange_title_issue(self):
        domain = {}
        domain['weekday_ids'] = []
        if not self.title_ids:
            self.issue_ids = [(6,0,[])]
            self.weekday_ids = [(6,0,[])]
        if self.issue_ids:
            days = set()
            weekdays = self.env['week.days']
            for issue in self.issue_ids.filtered('issue_date'):
                if len(days) == 7:
                    break
                dt = datetime.strptime(issue.issue_date, "%Y-%m-%d")
                days.add(dt.strftime('%A'))
            if days:
                days = list(days)
                weekdays = weekdays.search([('name', 'in', days)])
                self.weekday_ids = [(6, 0, weekdays.ids)]
                domain['weekday_ids'] = [('id', 'in', weekdays.ids)]
        else:
            self.weekday_ids = [(6, 0, [])]
        return {'domain': domain}

    @api.model
    def prepare_delivery_list(self, sols):
        self.ensure_one()
        advIssue = self.env['sale.advertising.issue']
        weekdays = self.env['week.days']
        deliveryLists, soLines = [], {}

        def _getIssue(self, line_obj):
            solDays, issue_ids, days = [wdys.name for wdys in line_obj.weekday_ids], [], []
            issueObj = advIssue.search([('parent_id', '=', line_obj.title.id), ('id', 'in', self.issue_ids.ids), ('issue_date','!=', False)])

            if not solDays:
                return issueObj, weekdays

            for issue in issueObj:
                dt = datetime.strptime(issue.issue_date, "%Y-%m-%d")
                if dt.strftime('%A') in solDays:
                    issue_ids.append(issue.id)
                    days.append(dt.strftime('%A'))
            issueObj = issueObj.search([('id','in',issue_ids)]) if issue_ids else advIssue
            wdysIds = weekdays.search([('name','in',days)]) if days else weekdays

            return issueObj, wdysIds

        for line_obj in sols:

            # copmare delivered issues if product issues is for magazine with non-zero values
            if line_obj.number_of_issues > 0 and line_obj.delivered_issues >= line_obj.number_of_issues:
                continue

            item={}
            issueObj, daysIds = _getIssue(self, line_obj)
            if issueObj:
                item['partner_id'] = line_obj.order_id.partner_shipping_id.id
                item['title'] = line_obj.title.id
                item['issue_ids'] = [(6,0,issueObj.ids)]
                item['sub_order_line'] = line_obj.id
                item['product_uom_qty'] = line_obj.product_uom_qty
                item['weekday_ids'] = [(6,0,daysIds.ids)]
                deliveryLists.append((0, 0, item))

                tot_issue = line_obj.delivered_issues + len(issueObj.ids)
                soLines[line_obj] = tot_issue
        res = {}

        if deliveryLists:
            res['delivery_list'] = deliveryLists
        if self.state != 'progress' and (self.delivery_list or 'delivery_list' in res):
            res['state'] = 'progress'

        if res:
            self.write(res)

        # update number of issues to subscription order line
        for sol, tot in soLines.iteritems():
            sol.write({'delivered_issues': tot})
        return True


    @api.multi
    def get_delivery_lists(self):
        orderline = self.env['sale.order.line']
        common_domain = [
            ('start_date', '<=', self.end_date),
            ('end_date', '>=', self.start_date),
            ('company_id', '=', self.company_id.id),
            ('weekday_ids', 'in', self.weekday_ids.ids)
        ]
        order_domain = common_domain + [
            ('delivery_type', '=', self.type.id),
            ('subscription', '=', True),
            ('state', '=', 'sale'),
            ('title', 'in', self.title_ids.ids),
            ('product_template_id.digital_subscription', '=', False)
        ]
        delivery_domain = common_domain+[
            ('id', '!=', self.id),
            ('state', '!=', 'cancel'),
            ('title_ids', 'in', self.title_ids.ids),
            ('issue_ids', 'in', self.issue_ids.ids),
            ('type', '=', self.type.id),
        ]

        self_sols = self.delivery_list.mapped('sub_order_line')
        sub_list_objs = self.search(delivery_domain)

        other_sols = []
        for found_obj in sub_list_objs:
            other_sols += found_obj.delivery_list.mapped('sub_order_line').ids
        if other_sols or self_sols:
            exists_sols = other_sols+self_sols.ids
            order_domain += [('id','not in',exists_sols)]

        sols = orderline.search(order_domain)
        self.prepare_delivery_list(sols)

        return True

    @api.multi
    def action_done(self):
        return self.write({'state': 'done'})

    @api.multi
    def action_cancel(self):
        return self.write({'state': 'cancel'})

    @api.multi
    def back2draft(self):
        return self.write({'state': 'draft'})

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
    weekday_ids = fields.Many2many('week.days', 'weekday_delivery_list_line_rel', 'delivery_list_id', 'weekday_id', 'Weekdays')



class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_list_ids = fields.One2many('subscription.delivery.list','subscription_number',string='Delivery List', copy=False)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    delivery_list_ids = fields.One2many('subscription.delivery.list','sub_order_line',string='Delivery List', copy=False)




