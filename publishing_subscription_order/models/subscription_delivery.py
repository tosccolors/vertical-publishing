# -*- encoding: utf-8 -*-

from odoo import api, fields, exceptions, models, _
import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta
from dateutil import relativedelta


class SubscriptionTitleDelivery(models.Model):
    _name = 'subscription.title.delivery'
    _description = 'Subscription Title Delivery'
    _rec_name = "title_id"

    title_id = fields.Many2one('sale.advertising.issue', required=True, readonly=True, string='Title')
    delivery_list_ids = fields.One2many('subscription.delivery.list', 'delivery_id', string='Delivery List', copy=False)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.order'))

    _sql_constraints = [('uniq_title', 'unique(title_id)', 'The Title must be unique')]

    @api.multi
    def generate_delivery_title(self):
        """
         Creates delivery title for all subscription title
        """

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
                            (company_id, create_uid, create_date, write_uid, write_date, title_id)
                        SELECT
                            {0} AS company_id,
                            {1} AS create_uid,
                            {2} AS create_date,
                            {1} AS write_uid,
                            {2} AS write_date,
                            {3}.id AS title_id
                          FROM
                            {3}
                          WHERE {4}                          
                     """.format(
                            "'%s'" % str(company_id.id),
                            self._uid,
                            "'%s'" % str(fields.Datetime.to_string(fields.datetime.now())),
                            title_tables,
                            title_where_clause
                    ))

        self.env.cr.execute(list_query, title_where_clause_params)

    @api.multi
    def generate_delivery_list(self):
        """
            Creates delivery List for current delivery title
        """

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
                               (delivery_id, delivery_date, title_id, state, create_uid, create_date, write_uid, write_date, company_id, issue_id, issue_date, type, weekday_id)
                            SELECT
                               {0} AS delivery_id,
                               {1}::DATE AS delivery_date,
                               {2} AS title_id,
                               {3} AS state,
                               {4} AS create_uid,
                               {5}::TIMESTAMP AS create_date,
                               {4} AS write_uid,
                               {5}::TIMESTAMP AS write_date,
                               {6} AS company_id,
                               {7}.id AS issue_id,
                               {7}.issue_date::DATE AS issue_date,
                               {8}.delivery_type AS type,
                               (select extract(dow from ({7}.issue_date)::DATE)) AS weekday_id
                            FROM
                               {7}, {8}
                            WHERE {9}
                            EXCEPT
                            SELECT
                               {0} AS delivery_id,
                               {1} AS delivery_date,
                               {2} AS title_id,
                               {3} AS state,
                               {4} AS create_uid,
                               {5} AS create_date,
                               {4} AS write_uid,
                               {5} AS write_date,
                               {6} AS company_id,
                               dl.issue_id AS issue_id,
                               dl.issue_date AS issue_date,
                               dl.type AS type,
                               dl.weekday_id AS weekday_id
                            FROM
                                subscription_delivery_list AS dl
                                """.format(
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
            self.env['subscription.delivery.list'].update_name()


class SubscriptionDeliveryList(models.Model):
    _name = 'subscription.delivery.list'
    _description = 'Subscription Delivery List'
    _rec_name = 'delivery_date'
    _order = 'issue_date, delivery_date'

    @api.multi
    @api.depends('issue_date')
    def _compute_weekday(self):
        weekdays = self.env['week.days']
        for sobj in self:
            dt = datetime.strptime(sobj.issue_date, "%Y-%m-%d")
            sobj.weekday_id = weekdays.search([('name', '=', dt.strftime('%A'))]).ids[0]

    name = fields.Char(string='Delivery List#', copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    delivery_id = fields.Many2one('subscription.title.delivery', 'Delivery Title', readonly=True, states={'draft': [('readonly', False)]}, ondelete='cascade')
    delivery_date = fields.Date('Prepared on', default=fields.Date.today,  readonly=True, states={'draft': [('readonly', False)]})
    weekday_id = fields.Many2one('week.days', compute=_compute_weekday, store=True, string='Weekday', readonly=True, copy=False)
    type = fields.Many2one('delivery.list.type', string='Delivery type', readonly=True, states={'draft': [('readonly', False)]}, copy=False)
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

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'subscription.delivery.list') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('subscription.delivery.list') or _('New')
        result = super(SubscriptionDeliveryList, self).create(vals)
        return result

    @api.multi
    def generate_all_delivery_list(self):
        """
            Creates delivery List for all delivery title
        """

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
                       (delivery_id, delivery_date, title_id, state, create_uid, create_date, write_uid, write_date, company_id, issue_id, issue_date, type, weekday_id)
                    SELECT 
                       dt.id AS delivery_id,
                       {0}::DATE AS delivery_date,
                       dt.title_id AS title_id,
                       {1} AS state,
                       {2} AS create_uid,
                       {3}::TIMESTAMP AS create_date,
                       {2} AS write_uid,
                       {3}::TIMESTAMP AS write_date,
                       dt.company_id AS company_id,
                       {4}.id AS issue_id,
                       {4}.issue_date::DATE AS issue_date,
                       {5}.delivery_type AS type,
                       (select extract(dow from ({4}.issue_date)::DATE)) AS weekday_id
                    FROM
                       {4}, {5}, subscription_title_delivery AS dt
                    WHERE {6} AND dt.title_id = {5}.title AND dt.company_id = {5}.company_id AND dt.title_id = {4}.parent_id
                    EXCEPT
                    SELECT
                       dt.id AS delivery_id,
                       {0} AS delivery_date,
                       dt.title_id AS title_id,
                       {1} AS state,
                       {2} AS create_uid,
                       {3} AS create_date,
                       {2} AS write_uid,
                       {3} AS write_date,
                       dt.company_id AS company_id,
                       dl.issue_id AS issue_id,
                       dl.issue_date AS issue_date,
                       dl.type AS type,
                       dl.weekday_id AS weekday_id
                    FROM
                        subscription_delivery_list AS dl, subscription_title_delivery AS dt
                        """.format(
            "'%s'" % str(fields.Date.to_string(datetime.now())),
            "'draft'",
            self._uid,
            "'%s'" % str(fields.Datetime.to_string(fields.datetime.now())),
            issue_tables,
            sol_tables,
            all_where_clause,
        ))
        self.env.cr.execute(list_query, all_where_clause_params)
        self.update_name()

    def update_name(self):
        list_ids = self.search([('name','=',False)])
        list_ids.write({'name':'New'})


    @api.multi
    def update_sequence_number(self):
        self.ensure_one()
        if self.name == 'New':
            if self.company_id:
                name = self.env['ir.sequence'].with_context(force_company=self.company_id).next_by_code(
                    'subscription.delivery.list') or _('New')
            else:
                name = self.env['ir.sequence'].next_by_code('subscription.delivery.list') or _('New')
            self.name = name
        return self.name

    @api.multi
    def generate_delivery_lines(self):
        """
         Crates delivery line for all delivery order
        """

        SOL = self.env['sale.order.line']

        for dlist in self:
            dlist.update_sequence_number()
            weekday_id = dlist.weekday_id.id
            common_domain = [('title', '=', dlist.title_id.id), ('weekday_ids','=', weekday_id), ('state', '=', 'sale'), ('subscription', '=', True), ('delivery_type', '=', dlist.type.id), ('company_id', '=', dlist.company_id.id)]
            sol_domain = common_domain + [('product_id.digital_subscription', '=', False), ('start_date', '<=', dlist.issue_date), ('end_date', '>=', dlist.issue_date)]

            temp_stop_domain = common_domain + [('temporary_stop','=',True), ('tmp_start_date', '<=', dlist.issue_date), ('tmp_end_date', '>=', dlist.issue_date)]
            temp_sol = SOL.search(temp_stop_domain)
            stopSolIds = []
            if temp_sol:
                stopSolIds += temp_sol.ids                

            self.env.cr.execute("SELECT array_agg(sub_order_line) FROM subscription_delivery_line WHERE delivery_list_id = %s"%(dlist.id))
            currSOL = self.env.cr.fetchall()[0][0]
            if currSOL:
                stopSolIds += list(currSOL)
                
            if stopSolIds:
                stopSolIds = list(set(stopSolIds))
                sol_domain += [('id', 'not in', stopSolIds)]

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
                            dlist.id,
                            dlist.company_id.id,
                            self._uid,
                            "'%s'" % str(fields.Datetime.to_string(fields.datetime.now())),
                            sol_tables,
                            sol_where_clause
                        ))

            self.env.cr.execute(list_query, sol_where_clause_params)


    def generate_all_delivery_lines(self):
        """
            Creates delivery Lines for all delivery list
        """

        SOL = self.env['sale.order.line']

        sol_domain = [('state', '=', 'sale'), ('subscription', '=', True),('product_id.digital_subscription','=',False)]
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
                            {2}, subscription_delivery_list as dl, weekday_sale_line_rel as wk
                          WHERE {3} AND dl.title_id = {2}.title AND dl.type = {2}.delivery_type AND dl.company_id = {2}.company_id AND
                            {2}.start_date <= dl.issue_date AND {2}.end_date >= dl.issue_date AND wk.order_line_id = {2}.id AND wk.weekday_id = dl.weekday_id AND 
                            ((({2}.temporary_stop IS Null) OR {2}.temporary_stop ='t' AND dl.issue_date NOT BETWEEN {2}.tmp_start_date and {2}.tmp_end_date) )
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
    def action_done(self):
        return self.write({'state': 'done'})

    @api.multi
    def action_progress(self):
        self.update_sequence_number()
        return self.write({'state': 'progress'})

    @api.multi
    def action_cancel(self):
        result = self.write({'state': 'cancel'})
        lines = self.env['subscription.delivery.line'].search([('delivery_list_id', 'in', tuple(self.ids))])
        lines.update_delivered_issues()
        return result

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
    product_uom_qty = fields.Float(string='Delivered per subscription', digits=(16,0), required=True)
    company_id = fields.Many2one(related='delivery_list_id.company_id', string='Company', store=True, readonly=True)
    title_id = fields.Many2one(related='delivery_list_id.title_id', string='Title', readonly=True)
    issue_id = fields.Many2one(related='delivery_list_id.issue_id', string='Issue', readonly=True)
    state = fields.Selection(related='delivery_list_id.state', string='State', readonly=True)


    def update_delivered_issues(self):
        """
            Update Sale order line delivered Issues from all delivery lines
        """
        if len(self) == 0:
            return
        elif len(self) == 1:
            cond = '='
            rec = self.sub_order_line.id
        else :
            cond = 'IN'
            rec = tuple(self.mapped('sub_order_line').ids)
        self.env.invalidate_all() #next steps need up-to-date database
        list_query = (""" 
            WITH  delivered AS
                ( SELECT sub_order_line, 
                         sum(CASE WHEN subscription_delivery_list.state ='cancel' 
                               THEN 0 
                               ELSE subscription_delivery_line.product_uom_qty 
                             END
                          ) as total_per_sub_order_line
                  FROM subscription_delivery_line
                  JOIN subscription_delivery_list ON subscription_delivery_list.id = subscription_delivery_line.delivery_list_id
                  WHERE subscription_delivery_line.sub_order_line %s %s
                  GROUP BY sub_order_line )
            UPDATE sale_order_line 
            SET delivered_issues = delivered.total_per_sub_order_line
            FROM  delivered
            WHERE sale_order_line.id = delivered.sub_order_line
                  AND sale_order_line.subscription = 't'                  
        """)
        self.env.cr.execute(list_query % (cond, rec))
        self.env.cr.commit()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    delivery_line_ids = fields.One2many('subscription.delivery.line','sub_order_line',string='Delivery Lines', copy=False, compute="_compute_line_ids",)

    @api.one
    def _compute_line_ids(self):
        self.delivery_line_ids = self.env["subscription.delivery.line"].search([('sub_order_line', '=', self.id),('state','=','done')])




