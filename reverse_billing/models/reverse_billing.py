# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2016 Magnus www.magnus.nl
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
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class SowBatch(models.Model):

    _name = "sow.batch"
    _order = "id desc"

    @api.one
    @api.depends('invoiced', 'invoice_ids.state')
    def _invoiced_rate(self, cursor, user, ids, name, arg, context=None):
        rate = tot = 0.0

        if self.invoiced:
            rate = 100.0

        else:
            for invoice in self.invoice_ids:
                if invoice.state not in ('draft', 'cancel'):
                    tot += invoice.amount_untaxed
            if tot:
                rate = min(100.0, tot * 100.0 / (self.amount_untaxed or 1.00))

        self.invoiced_rate = rate

    @api.one
    @api.depends('invoice_ids')
    def _invoice_exists(self):
        flag = False
        if self.invoice_ids:
            flag = True

        self.invoice_exists = flag

    @api.one
    @api.depends('sow_batch_line.invoice_line_id', 'sow_batch_line.employee', 'sow_batch_line.gratis')
    def _invoiced(self):
        flag = True
        for line in self.sow_batch_line:
            if not line.invoice_line_id and not line.employee and not line.gratis:
                flag = False
                break

        self.invoiced = flag

    def _invoiced_search(self, operator, value):
        cursor = self._cr

        clause = ''
        batch_clause = ''
        no_invoiced = False

        if (operator == '=' and value) or (operator == '!=' and not value):
            clause += 'AND inv.state = \'paid\''
        else:
            clause += 'AND inv.state != \'cancel\' AND batch.state != \'cancel\'  AND inv.state <> \'paid\'  AND rel.batch_id = batch.id '
            batch_clause = ',  sow_batch AS batch '
            no_invoiced = True

        cursor.execute('SELECT rel.batch_id ' \
                       'FROM sow_batch_invoice_rel AS rel, account_invoice AS inv '+ batch_clause + \
                       'WHERE rel.invoice_id = inv.id ' + clause)
        res = cursor.fetchall()
        if no_invoiced:
            cursor.execute('SELECT batch.id ' \
                           'FROM sow_batch AS batch ' \
                           'WHERE batch.id NOT IN ' \
                           '(SELECT rel.batch_id ' \
                           'FROM sow_batch_invoice_rel AS rel) and batch.state != \'cancel\'')
            res.extend(cursor.fetchall())
        if not res:
            return [('id', '=', 0)]
        return [('id', 'in', [x[0] for x in res])]



    date_batch = fields.Date(string='Batch Date')
    name = fields.Char(string='Name')
    company_id = fields.Many2one('res.company', 'Company', required=True, change_default=True,
                                 readonly=True, states={'draft':[('readonly',False)]},
                                 default=lambda self: self.env['res.company']._company_default_get('account.invoice'))
    sow_batch_line = fields.One2many('revbil.statement.of.work', 'batch_id', 'Batch Lines', readonly=False,
                                     states={'draft':[('readonly',False)]})
    state = fields.Selection([
        ('cancel', 'Cancelled'),
        ('draft','Draft'),
        ('open','Open'),
        ('done', 'Done'),
        ],'Status', index=True, readonly=True, default='draft',
        help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed Batch. \
        \n* The \'Open\' status is used when user create invoice.\
        \n* The \'Cancelled\' status is used when user cancel Batch.')
    comment = fields.Text('Additional Information')
    invoice_ids = fields.Many2many('account.invoice', 'sow_batch_invoice_rel', 'batch_id', 'invoice_id',
                                    'Invoices', readonly=True,
                                    help="This is the list of invoices that have been generated for this batch. "
                                         "The same batch may have been invoiced several times (by line for example).")
    invoiced_rate = fields.Float(compute='_invoiced_rate', string='Invoiced Ratio')
    invoiced = fields.Boolean(compute='_invoiced', string='Invoiced',
                                search='_invoiced_search',
                                help="It indicates that all batch lines have been invoiced.")
    invoice_exists = fields.Boolean(compute='_invoice_exists', string='Invoiced',
                                      search='_invoiced_search',
                                      help="It indicates that batch has at least one invoice.")



    @api.multi
    def action_invoice_create(self):
        '''
        create invoices for the given batches of sow (ids), and open the form
        view of one of the newly created invoices
        '''

        ctx = self._context.copy()
        ctx.update({'active_ids': self.sow_batch_line.ids})
        return self.env['revbil.statement.of.work.make.invoice'].with_context(ctx).make_invoices_from_lines()


    @api.multi
    def action_view_invoice(self):
        '''
        This function returns an action that display existing invoices of given sow batch ids.
        It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_invoice_tree2').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.invoice_supplier_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action


    @api.multi
    def action_batch_confirm(self):
        if not self.sow_batch_line:
            raise UserError(_('You cannot confirm a sow batch which has no line.'))
        self.write({'state': 'open', })
        self.sow_batch_line.button_confirm()


    @api.multi
    def action_back_draft(self):
        '''Method: action unconfirm'''

        self.write({'state': 'draft', })
        self.sow_batch_line.button_unconfirm()

    @api.multi
    def action_cancel(self):

        for inv in self.invoice_ids:
            if inv.state not in ('draft', 'cancel'):
                raise UserError(_('Cannot cancel this batch!, First cancel all invoices attached to this batch.'))

        self.invoice_ids.action_invoice_cancel()
        if self.invoice_ids:
            self._cr.execute('delete from sow_batch_invoice_rel where batch_id=%s and invoice_id in %s',
                           (self.id, tuple(self.invoice_ids.ids),))

        self.sow_batch_line.write({'state': 'cancel','invoice_line_id': False})
        self.write({'state': 'cancel'})

    @api.multi
    def action_cancel_draft(self):
        self.write({'state':'draft'})

    @api.multi
    def action_done(self):
        if not self.invoiced:
            UserError(_('Cannot finalise this batch!, First invoice all sow_lines attached to this batch.'))

        self.write({'state': 'done'})

    @api.multi
    def unlink(self):
        for case in self:
            if case.state not in ('draft', 'cancel'):
                raise UserError(_('In order to delete a confirmed batch, you must cancel it before!'))
        return super(SowBatch, self).unlink()

class RevBilStatementOfWork(models.Model):

    _name = "revbil.statement.of.work"

    @api.one
    @api.depends('invoice_line_id', 'employee', 'gratis')
    def _invoiced(self):
        for line in self:
            flag = True
            if not line.invoice_line_id and not line.employee and not line.gratis:
                flag = False
            line.invoiced = flag

    def _invoiced_search(self, operator, value):
        cursor = self._cr

        clause = ''
        batch_clause = ''
        no_invoiced = False

        if (operator == '=' and value) or (operator == '!=' and not value):
            clause += 'AND inv.state = \'paid\''
        else:
            clause += 'AND inv.state != \'cancel\' AND batch.state != \'cancel\'  AND inv.state <> \'paid\'  AND rel.batch_id = batch.id '
            batch_clause = ',  sow_batch AS batch '
            no_invoiced = True

        cursor.execute('SELECT rel.batch_id ' \
                       'FROM sow_batch_invoice_rel AS rel, account_invoice AS inv ' + batch_clause + \
                       'WHERE rel.invoice_id = inv.id ' + clause)
        res = cursor.fetchall()
        if no_invoiced:
            cursor.execute('SELECT batch.id ' \
                           'FROM sow_batch AS batch ' \
                           'WHERE batch.id NOT IN ' \
                           '(SELECT rel.batch_id ' \
                           'FROM sow_batch_invoice_rel AS rel) and batch.state != \'cancel\'')
            res.extend(cursor.fetchall())
        if not res:
            return [('id', '=', 0)]
        return [('id', 'in', [x[0] for x in res])]

    @api.one
    @api.depends('price_unit', 'quantity')
    def _amount_line(self):
        self.price_subtotal = self.price_unit * self.quantity

    sequence = fields.Integer('Sequence', default=10,
                              help="Gives the sequence of this line when displaying the statement of work.")
    name = fields.Char('Description', required=True, size=64)
    page_number = fields.Char('Pgnr', size=32)
    nr_of_columns = fields.Float('#Cols', digits=dp.get_precision('Number of Columns'), required=True)
    batch_id = fields.Many2one('sow.batch', 'Batch Reference', index=True)
    issue_id = fields.Many2one('sale.advertising.issue', 'Issue Reference', index=True, required=True)
    partner_id = fields.Many2one('res.partner', 'Freelancer', required=True)
    employee = fields.Boolean('Employee',  help="It indicates that the partner is an employee.",
                              default=False)
    product_category_id = fields.Many2one('product.category', 'Category', required=True,
                                          domain=[('parent_id.revbil', '=', True)])
    product_id = fields.Many2one('product.product', 'Product', required=True,)
    account_id = fields.Many2one('account.account', 'Account', required=True,
                                 domain=[('internal_type','<>','view')],
                                 help="The income or expense account related to the selected product.")
    # uos_id = fields.Many2one('product.uom', 'Unit of Measure', ondelete='set null', index=True)
    price_unit = fields.Float('Unit Price', required=True, digits= dp.get_precision('Product Price'), default=0.0)
    quantity = fields.Float('Quantity', digits= dp.get_precision('Product Unit of Measure'),
                            required=True, default=1)
    analytic_account_id = fields.Many2one(related='issue_id.analytic_account_id', relation='account.analytic.account',
                                          string='Analytic Account', store=True, readonly=True )
    date_publish = fields.Date(related='issue_id.issue_date', readonly=True, string='Publishing Date', store=True,)
    company_id = fields.Many2one(related='batch_id.company_id', relation='res.company',string='Company', store=True,
                                 readonly=True)
    price_subtotal = fields.Float(compute='_amount_line', string='Amount',digits = dp.get_precision('Account'),
                                  store=True)
    estimated_price = fields.Float('Estimate',)
    invoice_line_id = fields.Many2one('account.invoice.line', 'Invoice Line', readonly=True)
    invoice_id = fields.Many2one(related='invoice_line_id.invoice_id', relation='account.invoice', string='Invoice',
                                 readonly=True)
    invoiced = fields.Boolean(compute='_invoiced', string='Invoiced', store=True,
#                              search='_invoiced_search',
                              help="It indicates that the line has been invoiced.")
    state = fields.Selection(
        [('cancel', 'Cancelled'),
         ('draft', 'Draft'),
         ('confirmed', 'Confirmed'),
         ('exception', 'Exception'),
         ('done', 'Done')],
        'Status', required=True, readonly=True, default='draft',
        help='* The \'Draft\' status is set when the statement of work is in draft status. \
                    \n* The \'Confirmed\' status is set when the statement of work is confirmed. \
                    \n* The \'Exception\' status is set when the statement of work is set as exception. \
                    \n* The \'Done\' status is set when the statement of work has been picked. \
                    \n* The \'Cancelled\' status is set when a user cancels the statement of work.')
    gratis = fields.Boolean('Gratis',  help="It indicates that no letter/invoice is generated.")


    @api.model
    def _prepare_revbil_statement_of_work_invoice_line(self, account_id=False):
        """Prepare the dict of values to create the new invoice line for a
           revbil_statement_of_work. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record line: revbil.statement.of.work record to invoice
           :param int account_id: optional ID of a G/L account to force
               (this is used for returning products including service)
           :return: dict of values to create() the invoice line
        """
        res = {}
        if not self.invoice_line_id:
            if not account_id:
                if self.product_id:
                    account_id = self.product_id.property_account_expense_id.id
                    if not account_id:
                        account_id = self.product_id.categ_id.property_account_expense_categ_id.id
                    if not account_id:
                        raise UserError(_('Please define expense account for this product: "%s" (id:%d).') % \
                                    (self.product_id.name, self.product_id.id,))
                else:
                    prop = self.env['ir.property'].get('property_account_expense_categ_id', 'product.category')
                    account_id = prop and prop.id or False

            qty = self.quantity
            fpos = self.partner_id.property_account_position_id
            account_id = fpos.map_account(account_id)

            if not account_id:
                raise UserError(_('There is no Fiscal Position defined or Expense category account defined for default properties of Product categories.'))

            res = {
                'revbil_statement_of_work_id': self.id,
                'analytic_account_id': self.analytic_account_id.id,
                'name': self.name,
                'sequence': self.sequence,
                'origin': self.issue_id.name,
                'account_id': account_id,
                'price_unit': self.price_unit,
                'quantity': qty,
                # 'uos_id': self.uos_id,
                'product_id': self.product_id.id,
            }

        return res

    @api.multi
    def invoice_line_create(self):
        create_ids = []

        for line in self:
            vals = line._prepare_revbil_statement_of_work_invoice_line(account_id=False)
            if vals:
                invln = self.env['account.invoice.line'].create(vals)
                line.write({'invoice_line_id': invln.id})
                create_ids.append(invln.id)
        return create_ids

    # TODO: This method is not in use
    @api.multi
    def button_cancel(self):
        if self.invoice_line_id:
            raise UserError(_('You cannot cancel a Statement of Work that has already been invoiced.'))
        self.write({'state': 'cancel'})

    @api.multi
    def button_confirm(self):
        self.write({'state': 'confirmed'})

    @api.multi
    def button_unconfirm(self):
        self.write({'state': 'draft'})

    # TODO: This method is not in use
    @api.multi
    def button_done(self):
        self.write({'state': 'done'})
        self.batch_id.action_done()


    @api.multi
    def unlink(self):
        """Allows to delete Statement of Work lines in draft,cancel states"""
        for rec in self:
            if rec.state not in ['draft', 'cancel']:
                raise UserError(_('Cannot delete a Statement of Work line which is in state \'%s\'.') %(rec.state,))
        return super(RevBilStatementOfWork, self).unlink()


    @api.onchange('product_category_id')
    def product_category_change(self):
        if not self.product_category_id or not self.product_id:
            return {}

        if self.product_category_id is not self.product_id.categ_id:
            self.product_id = False


    @api.onchange('partner_id', 'product_id')
    def _onchange_calculatePrice(self):
        if not (self.partner_id and self.product_id):
            return {}
        user = self.env.user
        context = dict(self._context)
        company_id = context.get('company_id', user.company_id.id)
        context.update({'company_id': company_id, 'force_company': company_id})
        part = self.partner_id
        if part.lang:
            context.update({'lang': part.lang})
        self.employee = True if part.employee else False
        if 'nsm_supplier_portal' in self.env['ir.module.module']._installed():
            if part.product_category_ids:
                self.product_category_id = part.product_category_ids[0].id
        res = self.product_id
        a = res.property_account_expense_id.id
        if not a:
            a = res.categ_id.property_account_expense_categ_id.id
        if a:
            self.account_id = a
        self.price_unit = self.partner_id.property_product_pricelist.get_product_price(self.product_id, self.quantity or 1.0, self.partner_id)




