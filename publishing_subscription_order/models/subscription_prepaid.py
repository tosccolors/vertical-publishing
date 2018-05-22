# -*- encoding: utf-8 -*-

from odoo import api, fields, exceptions, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil import relativedelta

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'out_refund': 'sale',
}

class SubscriptionPrepaid(models.Model):
    _name = 'subscription.prepaid'
    _rec_name = 'start_date'
    _order = 'start_date desc'
    _inherit = ['mail.thread']
    _description = 'Subscription Prepaid'


    @api.model
    def _get_default_source_journals(self):
        res = []
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
            ('company_id', '=', company_id),
        ]
        journal = self.env['account.journal'].search(domain)
        if journal:
            res = journal.ids
        return res

    @api.multi
    @api.depends('line_ids')
    def _compute_total_prepaid(self):
        for subscription in self:
            tamount = 0.0
            for line in subscription.line_ids:
                tamount += line.prepaid_amount
            subscription.total_prepaid_amount = tamount

    source_journal_ids = fields.Many2many('account.journal', column1='subscription_id', column2='journal_id', string='Source Journals', readonly=True,   default=_get_default_source_journals, states={'draft': [('readonly', False)]})
    subscription_journal_id = fields.Many2one('account.journal', string='Prepaid Account Journal',  readonly=True, states={'draft': [('readonly', False)]})

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    move_id = fields.Many2one('account.move', string='Prepaid Journal Entry', readonly=True, copy=False)

    delivery_obligation_account_ids = fields.Many2many('account.account', column1='subscription_id', column2='account_id', string='Delivery Obligation Account', domain=[('deprecated', '=', False)],readonly=True, states={'draft': [('readonly', False)]},)
    subscription_revenue_account_id = fields.Many2one('account.account', string='Prepaid Revenue Account', domain=[('deprecated', '=', False)],readonly=True, states={'draft': [('readonly', False)]},)

    total_prepaid_amount = fields.Monetary( compute='_compute_total_prepaid', string="Total Prepaid Amount", currency_field='company_currency_id', readonly=True, track_visibility='onchange', help="Total Excluding Taxes.")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,  states={'draft': [('readonly', False)]}, default=lambda self: self.env['res.company']._company_default_get('subscription.prepaid'))
    company_currency_id = fields.Many2one(related='company_id.currency_id', readonly=True, string='Company Currency')
    line_ids = fields.One2many('subscription.prepaid.line', 'parent_id', string='Prepaid Lines',readonly=True, states={'done': [('readonly', True)]})
    state = fields.Selection([('draft', 'Draft'),('process', 'In progress'),('done', 'Done'),], string='State', index=True, readonly=True, track_visibility='onchange', default='draft', copy=False, help="State of the prepaid. When the Journal Entry is created, "
        "the state is set to 'Done' and the fields become read-only.")

    @api.constrains('start_date', 'end_date')
    def _check_date(self):
        for prepaid in self:
            domain = [
                ('start_date', '<=', prepaid.end_date),
                ('end_date', '>=', prepaid.start_date),
                ('id', '!=', prepaid.id),
                ('state', '!=', 'done'),
                ('company_id', '=', prepaid.company_id.id),
            ]
            nprepaid = prepaid.search_count(domain)
            if nprepaid:
                raise ValidationError(_('You can not have 2 prepaid record that overlaps on same date range for same company!'))

    @api.multi
    @api.constrains('start_date', 'end_date')
    def _check_start_end_dates(self):
        for prepaid in self:
            if prepaid.start_date and prepaid.end_date and prepaid.start_date > prepaid.end_date:
                raise ValidationError(_('The start date is after the end date!'))

    @api.multi
    def back2draft(self):
        self.ensure_one()
        if self.move_id:
            self.move_id.unlink()
        self.state = 'draft'

    def _get_merge_keys(self):
        """ Return merge criteria for provision lines

        The returned list must contain valid field names
        for account.move.line. Provision lines with the
        same values for these fields will be merged.
        The list must at least contain account_id.
        """
        return ['account_id', 'analytic_account_id']

    @api.multi
    def _prepare_move(self, to_provision):
        self.ensure_one()
        movelines_to_create = []
        amount_total = 0
        move_label = 'Subscription Revenue Recognition'
        merge_keys = self._get_merge_keys()
        for merge_values, amount in to_provision.items():
            vals = {
                'name': move_label,
                'debit': amount < 0 and amount * -1 or 0,
                'credit': amount >= 0 and amount or 0,
            }
            for k, v in zip(merge_keys, merge_values):
                vals[k] = v
            movelines_to_create.append((0, 0, vals))
            amount_total += amount

        # add counter-part
        counterpart_amount = amount_total * -1
        movelines_to_create.append((0, 0, {
            'account_id': self.subscription_revenue_account_id.id,
            'name': move_label,
            'debit': counterpart_amount < 0 and counterpart_amount * -1 or 0,
            'credit': counterpart_amount >= 0 and counterpart_amount or 0,
            'analytic_account_id': False,
            'date':self.end_date,
        }))

        res = {
            'journal_id': self.subscription_journal_id.id,
            'ref': move_label,
            'line_ids': movelines_to_create,
            }
        return res


    @api.multi
    def _merge_provision_lines(self, provision_lines):
        """ merge provision line

        Returns a dictionary {key, amount} where key is
        a tuple containing the values of the properties in _get_merge_keys()
        """
        to_provision = {}
        merge_keys = self._get_merge_keys()
        for provision_line in provision_lines:
            key = tuple([provision_line.get(key) for key in merge_keys])
            if key in to_provision:
                to_provision[key] += provision_line['amount']
            else:
                to_provision[key] = provision_line['amount']
        return to_provision


    @api.multi
    def _prepare_provision_line(self, prepaid_line):
        """ Convert a prepaid line to elements of a move line

        The returned dictionary must at least contain 'account_id'
        and 'amount' (< 0 means debit).

        If you override this, the added fields must also be
        added in an override of _get_merge_keys.
        """
        return {
            'account_id': prepaid_line.account_id.id,
            'analytic_account_id': prepaid_line.analytic_account_id.id,
            'amount': prepaid_line.prepaid_amount,
        }

    @api.multi
    def create_move(self):
        self.ensure_one()
        move_obj = self.env['account.move']
        if self.move_id:
            raise UserError(_(
                "The Prepaid Journal Entry already exists. You should "
                "delete it before running this function."))
        if not self.line_ids:
            raise UserError(_(
                "There are no lines on this Prepaid, so we can't create "
                "a Journal Entry."))
        provision_lines = []
        for line in self.line_ids:
            provision_lines.append(self._prepare_provision_line(line))
        to_provision = self._merge_provision_lines(provision_lines)
        vals = self._prepare_move(to_provision)
        move = move_obj.create(vals)
        self.write({'move_id': move.id, 'state': 'done'})

        action = self.env['ir.actions.act_window'].for_xml_id(
            'account', 'action_move_journal_line')
        action.update({
            'view_mode': 'form,tree',
            'res_id': move.id,
            'view_id': False,
            'views': False,
            })
        return action

    @api.multi
    def search_prepaid_move(self, amls):
        self.ensure_one()
        found_amls = []
        self_domain = [
            ('start_date', '<=', self.end_date),
            ('end_date', '>=', self.start_date),
            ('id', '!=', self.id),
        ]
        subscription_ids = self.search(self_domain)
        if subscription_ids:
            domain = [
                ('parent_id', 'in', subscription_ids.ids),
                ('move_line_id', 'in', amls.ids),
            ]
            for data in self.env['subscription.prepaid.line'].search_read(domain, ['move_line_id']):
                found_amls.append(data['move_line_id'][0])
        if found_amls:
            amls = amls.filtered(lambda aml: aml.id not in found_amls)
        return amls

    @api.multi
    def get_prepaid_lines(self):
        self.ensure_one()
        aml_obj = self.env['account.move.line']
        line_obj = self.env['subscription.prepaid.line']
        if not self.source_journal_ids:
            raise UserError(
                _("You should set at least one Source Journal."))
        # Delete existing lines
        self.line_ids.unlink()

        domain = [
            ('product_id.subscription_product', '=', True),
            ('start_date', '<=', self.end_date),
            ('end_date', '>=', self.start_date),
            ('account_id', 'in', self.delivery_obligation_account_ids.ids),
            ('journal_id', 'in', self.source_journal_ids.ids)
        ]

        # Search for account move lines in the source journals
        amls = self.search_prepaid_move(aml_obj.search(domain))
        for aml in amls:
            line_obj.create(self._prepare_prepaid_lines(aml))
        self.state = 'process'
        return True

    @api.multi
    def _prepare_prepaid_lines(self, aml):
        self.ensure_one()
        start_date_dt = fields.Date.from_string(aml.start_date)
        end_date_dt = fields.Date.from_string(aml.end_date)
        # Here, we compute the amount of the prepaid
        # That's the important part !
        total_months = relativedelta.relativedelta(end_date_dt, start_date_dt).months+1
        out_months = 0
        forecast_start_date_dt = fields.Date.from_string(self.start_date)
        forecast_end_date_dt = fields.Date.from_string(self.end_date)
        if end_date_dt > forecast_end_date_dt:
            out_months += relativedelta.relativedelta(end_date_dt, forecast_end_date_dt).months
        if start_date_dt < forecast_start_date_dt:
            out_months += relativedelta.relativedelta(forecast_start_date_dt, start_date_dt).months
        prepaid_months = total_months - out_months

        assert total_months > 0, \
            'Should never happen. Total Months should always be > 0'
        monthly_editions = int(aml.product_id.number_of_issues/total_months)
        monthly_editions_cost = ((aml.debit - aml.credit)/aml.product_id.number_of_issues)*monthly_editions
        prepaid_amount = monthly_editions_cost * prepaid_months
        title = aml.name
        invoice_line_obj = aml.invoice_id.invoice_line_ids.filtered(lambda invline: invline.product_id == aml.product_id)
        for inv_line in invoice_line_obj:
            title = inv_line.sale_line_ids.title.name or aml.name
        res = {
            'parent_id': self.id,
            'move_line_id': aml.id,
            'partner_id': aml.partner_id.id or False,
            # 'name': aml.name,
            'name': title,
            'start_date': start_date_dt,
            'end_date': end_date_dt,
            'account_id': aml.account_id.id,
            'analytic_account_id': aml.analytic_account_id.id or False,
            'total_months': total_months,
            'prepaid_months': prepaid_months,
            'amount': aml.credit - aml.debit,
            'currency_id': self.company_currency_id.id,
            'prepaid_amount': prepaid_amount,
        }
        return res

class SubscriptionPrepaidLine(models.Model):
    _name = 'subscription.prepaid.line'
    _description = 'Subscription Prepaid Lines'

    parent_id = fields.Many2one('subscription.prepaid', string='Subscription Prepaid', ondelete='cascade')
    name = fields.Char('Title')
    company_currency_id = fields.Many2one(related='parent_id.company_currency_id', string="Company Currency", readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    account_id = fields.Many2one('account.account', 'Account',  domain=[('deprecated', '=', False)], required=True, readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account',  domain=[('account_type', '!=', 'closed')], readonly=True)
    analytic_account_code = fields.Char(related='analytic_account_id.code', string='Analytic Account Code', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Amount Currency', readonly=True,  help="Currency of the 'Amount' field.")
    amount = fields.Monetary(string='Amount', currency_field='currency_id', readonly=True, help="Amount that is used as base to compute the Prepaid Amount. "
             "This Amount is in the 'Amount Currency', which may be different "
             "from the 'Company Currency'.")
    prepaid_amount = fields.Monetary(string='Prepaid Amount', currency_field='company_currency_id', readonly=True, help="Prepaid Amount without taxes in the Company Currency.")
    move_line_id = fields.Many2one('account.move.line', string='Account Move Line', readonly=True)
    move_date = fields.Date(related='move_line_id.date', string='Account Move Date', readonly=True)
    invoice_id = fields.Many2one(related='move_line_id.invoice_id', string='Invoice', readonly=True)
    start_date = fields.Date(string='Start Date', readonly=True)
    end_date = fields.Date(string='End Date', readonly=True)
    total_months = fields.Integer('Total Number of Months', readonly=True)
    prepaid_months = fields.Integer(string='Prepaid Months', readonly=True,help="This is the number of months between the start date and the end date.")


