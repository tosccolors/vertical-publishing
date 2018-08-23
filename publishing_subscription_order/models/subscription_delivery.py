# -*- encoding: utf-8 -*-

from odoo import api, fields, exceptions, models, _
import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta
from dateutil import relativedelta


class SubscriptionTitleDelivery(models.Model):
    _name = 'subscription.title.delivery'
    _description = 'Subscription Title Delivery'

    name = fields.Char(string='Title Delivery Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    title_id = fields.Many2one('sale.advertising.issue', required=True, readonly=True, string='Title', states={'draft': [('readonly', False)]})
    delivery_list_ids = fields.One2many('subscription.delivery.list', 'delivery_id', string='Delivery List', copy=False)
    state = fields.Selection([
        ('draft', 'New'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.order'))

    _sql_constraints = [('uniq_title', 'unique(title_id)', 'The Title must be unique')]

    @api.multi
    def generate_sequence(self):
        for slf in self:
            if slf.name == _('New'):
                if self.company_id :
                    slf.name = self.env['ir.sequence'].with_context(force_company=self.company_id.id).next_by_code(
                        'subscription.title.delivery') or _('New')
                else:
                    slf.name = self.env['ir.sequence'].next_by_code('subscription.title.delivery') or _('New')
        return True

    @api.multi
    def action_done(self):
        return self.write({'state': 'done'})

    @api.multi
    def action_progress(self):
        self.generate_sequence()
        return self.write({'state': 'progress'})

    @api.multi
    def action_cancel(self):
        return self.write({'state': 'cancel'})

    @api.multi
    def generate_delivery_title(self):
        advIssue = self.env['sale.advertising.issue']

        title_domain = [('parent_id', '=', False), ('subscription_title', '=', True)]
        self.env.cr.execute("SELECT array_agg(title_id) FROM subscription_title_delivery")
        currTitles = self.env.cr.fetchall()[0][0]
        title_domain = title_domain + [('id', 'not in', currTitles)] if currTitles else title_domain
        title_query_line = advIssue._where_calc(title_domain)
        title_tables, title_where_clause, title_where_clause_params = title_query_line.get_sql()
        company_id = self.env['res.company']._company_default_get('sale.order')

        list_query = ("""
                        INSERT INTO
                            subscription_title_delivery
                            (name, company_id, state, create_uid, create_date, write_uid, write_date, title_id)
                        SELECT
                            {0} AS name,
                            {1} AS company_id,
                            {2} AS state,
                            {3} AS create_uid,
                            {4} AS create_date,
                            {3} AS write_uid,
                            {4} AS write_date,
                            {5}.id AS title_id
                          FROM
                            {5}
                          WHERE {6}                          
                     """.format(
                            "'New'",
                            "'%s'" % str(company_id.id),
                            "'draft'",
                            self._uid,
                            "'%s'" % str(fields.Datetime.to_string(fields.datetime.now())),
                            title_tables,
                            title_where_clause
                    ))

        self.env.cr.execute(list_query, title_where_clause_params)

    @api.multi
    def generate_delivery_list(self):
        SOL = self.env['sale.order.line']
        advIssue = self.env['sale.advertising.issue']

        for delvTitle in self:
            title = delvTitle.title_id

            sol_domain = [('title', '=', title.id), ('subscription', '=', True),('company_id','=',delvTitle.company_id.id),('state', '=', 'sale')]
            sol_query_line = SOL._where_calc(sol_domain)
            sol_tables, sol_where_clause, sol_where_clause_params = sol_query_line.get_sql()

            issue_domain = [('parent_id', '=', title.id), ('subscription_title', '=', True), ('issue_date', '!=', False)]
            issues_query_line = advIssue._where_calc(issue_domain)
            issue_tables, issue_where_clause, issue_where_clause_params = issues_query_line.get_sql()

            all_where_clause = issue_where_clause + ' AND ' + sol_where_clause
            all_where_clause_params = issue_where_clause_params + sol_where_clause_params


            list_query = ("""
                          INSERT INTO
                               subscription_delivery_list
                               (name, delivery_id, delivery_date, title_id, state, create_uid, create_date, write_uid, write_date, company_id, issue_id, issue_date, type)
                            SELECT
                               {0} AS name,
                               {1} AS delivery_id,
                               {2}::DATE AS delivery_date,
                               {3} AS title_id,
                               {4} AS state,
                               {5} AS create_uid,
                               {6}::TIMESTAMP AS create_date,
                               {5} AS write_uid,
                               {6}::TIMESTAMP AS write_date,
                               {7} AS company_id,
                               {8}.id AS issue_id,
                               {8}.issue_date::DATE AS issue_date,
                               {9}.delivery_type AS type
                            FROM
                               {8}, {9}
                            WHERE {10}
                            EXCEPT
                            SELECT
                               {0} AS name,
                               {1} AS delivery_id,
                               {2} AS delivery_date,
                               {3} AS title_id,
                               {4} AS state,
                               {5} AS create_uid,
                               {6} AS create_date,
                               {5} AS write_uid,
                               {6} AS write_date,
                               {7} AS company_id,
                               dl.issue_id AS issue_id,
                               dl.issue_date AS issue_date,
                               dl.type AS type
                            FROM
                                subscription_delivery_list AS dl
                                """.format(
                "'New'",
                delvTitle.id,
                "'%s'" % str(fields.Date.to_string(datetime.now())),
                title.id,
                "'draft'",
                self._uid,
                "'%s'" % str(fields.Datetime.to_string(fields.datetime.now())),
                delvTitle.company_id.id,
                issue_tables,
                sol_tables,
                all_where_clause,
            ))

            self.env.cr.execute(list_query, all_where_clause_params)
            delvTitle.generate_sequence()

    def generate_all_delivery_list(self):
        SOL = self.env['sale.order.line']
        advIssue = self.env['sale.advertising.issue']

        sol_domain = [('subscription', '=', True), ('state', '=', 'sale')]
        sol_query_line = SOL._where_calc(sol_domain)
        sol_tables, sol_where_clause, sol_where_clause_params = sol_query_line.get_sql()

        issue_domain = [('subscription_title', '=', True), ('issue_date', '!=', False)]
        issues_query_line = advIssue._where_calc(issue_domain)
        issue_tables, issue_where_clause, issue_where_clause_params = issues_query_line.get_sql()

        all_where_clause = issue_where_clause + ' AND ' + sol_where_clause
        all_where_clause_params = issue_where_clause_params + sol_where_clause_params

        list_query = ("""
              INSERT INTO
                   subscription_delivery_list
                   (name, delivery_id, delivery_date, title_id, state, create_uid, create_date, write_uid, write_date, company_id, issue_id, issue_date, type)
                SELECT 
                   {0} AS name,
                   dt.id AS delivery_id,
                   {1}::DATE AS delivery_date,
                   dt.title_id AS title_id,
                   {2} AS state,
                   {3} AS create_uid,
                   {4}::TIMESTAMP AS create_date,
                   {3} AS write_uid,
                   {4}::TIMESTAMP AS write_date,
                   dt.company_id AS company_id,
                   {5}.id AS issue_id,
                   {5}.issue_date::DATE AS issue_date,
                   {6}.delivery_type AS type
                FROM
                   {5}, {6}, subscription_title_delivery AS dt
                WHERE {7} AND dt.title_id = {6}.title AND dt.company_id = {6}.company_id AND dt.title_id = {5}.parent_id
                EXCEPT
                SELECT
                   {0} AS name,
                   dt.id AS delivery_id,
                   {1} AS delivery_date,
                   dt.title_id AS title_id,
                   {2} AS state,
                   {3} AS create_uid,
                   {4} AS create_date,
                   {3} AS write_uid,
                   {4} AS write_date,
                   dt.company_id AS company_id,
                   dl.issue_id AS issue_id,
                   dl.issue_date AS issue_date,
                   dl.type AS type
                FROM
                    subscription_delivery_list AS dl, subscription_title_delivery AS dt
                    """.format(
                "'New'",
                "'%s'" % str(fields.Date.to_string(datetime.now())),
                "'draft'",
                self._uid,
                "'%s'" % str(fields.Datetime.to_string(fields.datetime.now())),
                issue_tables,
                sol_tables,
                all_where_clause,
            ))

        self.env.cr.execute(list_query, all_where_clause_params)


class SubscriptionDeliveryList(models.Model):
    _name = 'subscription.delivery.list'
    _description = 'Subscription Delivery List'
    _rec_name = 'delivery_date'

    @api.multi
    @api.depends('issue_date')
    def _compute_weekday(self):
        weekdays = self.env['week.days']
        for sobj in self:
            dt = datetime.strptime(sobj.issue_date, "%Y-%m-%d")
            sobj.weekday_id = weekdays.search([('name', '=', dt.strftime('%A'))]).ids[0]

    name = fields.Char(string='Delivery Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    delivery_id = fields.Many2one('subscription.title.delivery', 'Title', readonly=True, states={'draft': [('readonly', False)]}, ondelete='cascade')
    delivery_date = fields.Date('Delivery Date', default=fields.Date.today,  readonly=True, states={'draft': [('readonly', False)]})
    weekday_id = fields.Many2one('week.days', compute=_compute_weekday, string='Weekday', readonly=True, copy=False)
    type = fields.Many2one('delivery.list.type', string='Type', readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    title_id = fields.Many2one(related='delivery_id.title_id', string='Title', store=True, readonly=True)
    issue_id = fields.Many2one('sale.advertising.issue', 'Issue', readonly=True, states={'draft': [('readonly', False)]})
    issue_date = fields.Date(related='issue_id.issue_date', string='Issue Date', store=True, readonly=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.order'))
    delivery_line_ids = fields.One2many('subscription.delivery.line', 'delivery_list_id', string='Delivery Lines', copy=False)
    state = fields.Selection([
        ('draft', 'New'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')


    @api.multi
    def generate_delivery_lines(self):

        ######update delivered issues to Sale order lines can be done to make boolean field true once it's completed need to check with Willem######

        SOL = self.env['sale.order.line']
        advIssue = self.env['sale.advertising.issue']

        for list in self:
            sol_domain = [('title', '=', list.title_id.id), ('state', '=', 'sale'), ('subscription', '=', True), ('delivery_type', '=', list.type.id), ('start_date', '<=', list.issue_date), ('end_date', '>=', list.issue_date), ('company_id', '=', list.company_id.id)]
            self.env.cr.execute("SELECT array_agg(sub_order_line) FROM subscription_delivery_line WHERE delivery_list_id = %s"%(list.id))
            currSOL = self.env.cr.fetchall()[0][0]
            sol_domain = sol_domain + [('id', 'not in', currSOL)] if currSOL else sol_domain
            sol_query_line = SOL._where_calc(sol_domain)
            sol_tables, sol_where_clause, sol_where_clause_params = sol_query_line.get_sql()

            list_query = ("""
                            INSERT INTO
                                subscription_delivery_line
                                (delivery_list_id,sub_order_line, subscription_number, product_uom_qty, company_id, create_uid, create_date, write_uid, write_date, partner_id)
                            SELECT
                                {0} AS delivery_list_id,
                                {4}.id AS sub_order_line,
                                {4}.order_id AS subscription_number,
                                {4}.product_uom_qty AS product_uom_qty,
                                {1} AS company_id,
                                {2} AS create_uid,
                                {3} AS create_date,
                                {2} AS write_uid,
                                {3} AS write_date,
                                (SELECT partner_shipping_id AS partner_id FROM sale_order WHERE id = {4}.order_id)
                              FROM
                                {4}
                              WHERE {5}
                         """.format(
                            list.id,
                            list.company_id.id,
                            self._uid,
                            "'%s'" % str(fields.Datetime.to_string(fields.datetime.now())),
                            sol_tables,
                            sol_where_clause
                        ))

            self.env.cr.execute(list_query, sol_where_clause_params)
            list.generate_sequence()


    def generate_all_delivery_lines(self):
        SOL = self.env['sale.order.line']

        sol_domain = [('state', '=', 'sale'), ('subscription', '=', True)]
        sol_query_line = SOL._where_calc(sol_domain)
        sol_tables, sol_where_clause, sol_where_clause_params = sol_query_line.get_sql()

        list_query = ("""
                        INSERT INTO
                            subscription_delivery_line
                            (delivery_list_id, sub_order_line, subscription_number, product_uom_qty, company_id, create_uid, create_date, write_uid, write_date, partner_id)
                        SELECT
                            dl.id AS delivery_list_id,
                            {2}.id AS sub_order_line,
                            {2}.order_id AS subscription_number,
                            {2}.product_uom_qty AS product_uom_qty,
                            dl.company_id AS company_id,
                            {0} AS create_uid,
                            {1}::TIMESTAMP AS create_date,
                            {0} AS write_uid,
                            {1}::TIMESTAMP AS write_date,
                            (SELECT partner_shipping_id AS partner_id FROM sale_order WHERE id = {2}.order_id)
                          FROM
                            {2}, subscription_delivery_list as dl
                          WHERE {3} AND dl.title_id = {2}.title AND dl.type = {2}.delivery_type AND dl.company_id = {2}.company_id AND
                            {2}.start_date <= dl.issue_date AND {2}.end_date >= dl.issue_date
                        EXCEPT 
                        SELECT 
                            sl.delivery_list_id AS delivery_list_id,
                            sl.sub_order_line AS sub_order_line,
                            sl.subscription_number AS subscription_number,
                            sl.product_uom_qty AS product_uom_qty,
                            sl.company_id AS company_id,
                            {0} AS create_uid,
                            {1}::TIMESTAMP AS create_date,
                            {0} AS write_uid,
                            {1}::TIMESTAMP AS write_date,
                            sl.partner_id AS partner_id
                        FROM 
                            subscription_delivery_list as dl, subscription_delivery_line AS sl
                        WHERE dl.id = sl.delivery_list_id
                     """.format(
                        self._uid,
                        "'%s'" % str(fields.Datetime.to_string(fields.datetime.now())),
                        sol_tables,
                        sol_where_clause
        ))

        self.env.cr.execute(list_query, sol_where_clause_params)
        self.env['subscription.delivery.line'].update_delivered_issues()

    @api.multi
    def generate_sequence(self):
        for slf in self:
            if slf.name == _('New'):
                if self.company_id:
                    slf.name = self.env['ir.sequence'].with_context(force_company=self.company_id.id).next_by_code(
                        'subscription.delivery.list') or _('New')
                else:
                    slf.name = self.env['ir.sequence'].next_by_code('subscription.delivery.list') or _('New')
        return True

    @api.multi
    def action_done(self):
        return self.write({'state': 'done'})

    @api.multi
    def action_progress(self):
        self.generate_sequence()
        return self.write({'state': 'progress'})

    @api.multi
    def action_cancel(self):
        return self.write({'state': 'cancel'})

    @api.multi
    def print_xls_report(self):
        return self.env['report'].get_action(self, 'report_subscription_delivery.xlsx')

class SubscriptionDeliveryLine(models.Model):
    _name = 'subscription.delivery.line'
    _description = 'Subscription Delivery Line'
    _rec_name= 'subscription_number'


    delivery_list_id = fields.Many2one('subscription.delivery.list', string='Delivery List Reference', required=True, ondelete='cascade', index=True, copy=False)
    sub_order_line = fields.Many2one('sale.order.line', string='Subscription order line')
    subscription_number = fields.Many2one(related='sub_order_line.order_id', string='Subscription Number', store=True, readonly=True)
    partner_id = fields.Many2one(related='subscription_number.partner_shipping_id', string='Delivery Address',copy=False, readonly=True, store=True)
    product_uom_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)
    company_id = fields.Many2one(related='delivery_list_id.company_id', string='Company', store=True, readonly=True)
    title_id = fields.Many2one(related='delivery_list_id.title_id', string='Title', store=True, readonly=True)
    issue_id = fields.Many2one(related='delivery_list_id.issue_id', string='Issue', store=True, readonly=True)
    state = fields.Selection(related='delivery_list_id.state', string='State', store=True, readonly=True)

    @api.model
    def create(self, values):
        res = super(SubscriptionDeliveryLine, self).create(values)
        self.update_delivered_issues()
        return res

    @api.multi
    def write(self, values):
        res = super(SubscriptionDeliveryLine, self).write(values)
        self.update_delivered_issues()
        return res


    def update_delivered_issues(self):
        list_query = (""" 
                   UPDATE sale_order_line SET (delivered_issues) =
                   (SELECT count(sub_order_line) FROM subscription_delivery_line
                   WHERE subscription_delivery_line.sub_order_line = sale_order_line.id AND sale_order_line.subscription = 't' group by subscription_delivery_line.sub_order_line)                   
        """)
        self.env.cr.execute(list_query)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    delivery_line_ids = fields.One2many('subscription.delivery.line','sub_order_line',string='Delivery Lines', copy=False, compute="_compute_line_ids",)

    @api.one
    def _compute_line_ids(self):
        self.delivery_line_ids = self.env["subscription.delivery.line"].search([('sub_order_line', '=', self.id),('state','=','done')])




