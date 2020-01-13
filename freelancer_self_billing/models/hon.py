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

class HonIssue(models.Model):

    _name = "hon.issue"
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
    @api.depends(
        'hon_issue_line.invoice_line_id',
        'hon_issue_line.employee',
        'hon_issue_line.gratis'
    )
    def _invoiced(self):
        flag = True
        for line in self.hon_issue_line:
            if not line.invoice_line_id \
            and not line.employee \
            and not line.gratis:
                flag = False
                break
        self.invoiced = flag

    def _invoiced_search(self, operator, value):
        cursor = self._cr
        clause = ''
        issue_clause = ''
        no_invoiced = False
        if (operator == '=' and value) or (operator == '!=' and not value):
            clause += 'AND inv.state = \'paid\''
        else:
            clause += 'AND inv.state != \'cancel\' ' \
                      'AND issue.state != \'cancel\'  ' \
                      'AND inv.state <> \'paid\'  ' \
                      'AND rel.issue_id = issue.id '
            issue_clause = ',  hon_issue AS issue '
            no_invoiced = True
        cursor.execute('SELECT rel.issue_id ' \
                       'FROM hon_issue_invoice_rel AS rel, '
                       'account_invoice AS inv '+ issue_clause + \
                       'WHERE rel.invoice_id = inv.id ' + clause)
        res = cursor.fetchall()
        if no_invoiced:
            cursor.execute('SELECT issue.id ' \
                           'FROM hon_issue AS issue ' \
                           'WHERE issue.id NOT IN ' \
                           '(SELECT rel.issue_id ' \
                           'FROM hon_issue_invoice_rel AS rel) and issue.state != \'cancel\'')
            res.extend(cursor.fetchall())
        if not res:
            return [('id', '=', 0)]
        return [('id', 'in', [x[0] for x in res])]

    @api.model
    def _get_account_domain(self):
        domain = []
        if 'nsm_supplier_portal' in self.env['ir.module.module']._installed():
            domain = [('portal_sub', '=', True)]
        return domain

    account_analytic_id = fields.Many2one(
        'account.analytic.account',
        'Title/Issue',
        required=True,
        readonly=True,
        states = {'draft': [('readonly', False)]},
        domain=_get_account_domain
    )
    date_publish = fields.Date(
        related='account_analytic_id.date_publish',
        relation='account.analytic.account',
        string='Publishing Date',
        store=True,
        readonly=True
    )
    name = fields.Char(
        related='account_analytic_id.name',
        relation='account.analytic.account',
        string='Name',
        store=True,
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        change_default=True,
        readonly=True, states={'draft':[('readonly',False)]},
        default=lambda self: self.env['res.company'].
            _company_default_get('account.invoice'))

    hon_issue_line = fields.One2many(
        'hon.issue.line',
        'issue_id',
        'Hon Lines',
        readonly=False,
        states={'draft':[('readonly',False)]}
    )

    state = fields.Selection(
        [
        ('cancel', 'Cancelled'),
        ('draft','Draft'),
        ('open','Open'),
        ('done', 'Done'),
        ],
        'Status',
        index=True,
        readonly=True,
        default='draft',
        help=' * The \'Draft\' status is used when a user is encoding a new and'
             ' unconfirmed Honorarium Issue. \
        \n* The \'Open\' status is used when user create invoice.\
        \n* The \'Cancelled\' status is used when user cancel Honorarium Issue.'
    )

    comment = fields.Text(
        'Additional Information'
    )
    invoice_ids = fields.Many2many(
        'account.invoice',
        'hon_issue_invoice_rel',
        'issue_id',
        'invoice_id',
        'Invoices',
        readonly=True,
        help="This is the list of invoices that have been generated for this "
             "issue. "
             "The same issue may have been invoiced several times "
             "(by line for example).")

    invoiced_rate = fields.Float(
        compute='_invoiced_rate',
        string='Invoiced Ratio'
    )
    invoiced = fields.Boolean(
        compute='_invoiced',
        string='Invoiced',
        search='_invoiced_search',
        help="It indicates that all issue lines have been invoiced."
    )
    invoice_exists = fields.Boolean(
        compute='_invoice_exists',
        string='Invoiced',
        search='_invoiced_search',
        help="It indicates that hon issue has at least one invoice."
    )


    _sql_constraints = [
        ('account_analytic_company_uniq',
         'unique (account_analytic_id, company_id)',
         'The Issue must be unique per company !'),
    ]


    @api.onchange('account_analytic_id')
    def onchange_analytic_ac(self):
        res, war = {}, {}
        if not self.account_analytic_id:
            return res

        analytic_account = self.account_analytic_id

        res['name'] = analytic_account.name
        res['date_publish'] = analytic_account.date_publish
        llist = []
        for line in self.hon_issue_line:
            if line.tag_id:
                llist.append((1, line.id, {'tag_id': [],}))
                res['hon_issue_line'] = llist
                war['title'] = 'Let op!'
                war['message'] = 'U heeft de Titel/Nummer aangepast. ' \
                                 'Nu moet u opnieuw Redacties selecteren in ' \
                                 'de HONregel(s)'
        return {'value': res, 'warning': war}

    @api.multi
    def action_invoice_create(self):
        '''
        create invoices for the given hon issues (ids), and open the form
        view of one of the newly created invoices
        '''

        ctx = self._context.copy()
        ctx.update({'active_ids': self.hon_issue_line.ids})
        return self.env['hon.issue.line.make.invoice'].\
            with_context(ctx).make_invoices_from_lines()


    @api.multi
    def action_view_invoice(self):
        '''
        This function returns an action that display existing invoices of given hon issue ids.
        It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_invoice_tree2').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action


    @api.multi
    def action_issue_confirm(self):
        if not self.hon_issue_line:
            raise UserError(_('You cannot confirm a hon issue which has no line.'))
        self.write({'state': 'open', })
        self.hon_issue_line.action_line_confirm()


    @api.multi
    def action_back_draft(self):
        '''Method: action unwait'''

        if not self.hon_issue_line:
            raise UserError(_('You cannot unconfirm a hon issue which has no line.'))
        self.write({'state': 'draft', })
        self.hon_issue_line.action_line_unconfirm()

    @api.multi
    def action_cancel(self):
        for inv in self.invoice_ids:
            if inv.state not in ('draft', 'cancel'):
                raise UserError(_('Cannot cancel this issue!, First cancel all invoices attached to this issue.'))
        self.invoice_ids.action_invoice_cancel()
        if self.invoice_ids:
            self._cr.execute('delete from hon_issue_invoice_rel where issue_id=%s and invoice_id in %s',
                           (self.id, tuple(self.invoice_ids.ids),))
        self.hon_issue_line.write({'state': 'cancel','invoice_line_id': False})
        self.write({'state': 'cancel'})

    @api.multi
    def action_cancel_draft(self):
        self.write({'state':'draft'})

    @api.multi
    def action_done(self):
        if not self.invoiced:
            UserError(_('Cannot finalise this issue!, First invoice all hon_lines attached to this issue.'))
        self.write({'state': 'done'})

    @api.multi
    def unlink(self):
        for case in self:
            if case.state not in ('draft', 'cancel'):
                raise UserError(_('In order to delete a confirmed issue, you must cancel it before!'))
        return super(HonIssue, self).unlink()

class HonIssueLine(models.Model):

    _name = "hon.issue.line"

    @api.one
    @api.depends('price_unit', 'quantity')
    def _amount_line(self):
        self.price_subtotal = self.price_unit * self.quantity

    sequence = fields.Integer('Sequence', default=10, help="Gives the sequence of this line when displaying the honorarium issue.")
    name = fields.Char('Description', required=True, size=64)
    page_number = fields.Char('Pgnr', size=32)
    nr_of_columns = fields.Float('#Cols', digits=dp.get_precision('Number of Columns'), required=True)
    issue_id = fields.Many2one('hon.issue', 'Issue Reference', ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    employee = fields.Boolean('Employee',  help="It indicates that the partner is an employee.",
                              default=False)
    product_category_id = fields.Many2one('product.category', 'T/B', required=True, domain=[('parent_id.supportal',
                                                                                             '=', True)])
    product_id = fields.Many2one('product.product', 'Product', required=True,)
    account_id = fields.Many2one('account.account', 'Account', required=True,
                                 domain=[('internal_type','<>','view')],
                                 help="The income or expense account related to the selected product.")
    # uos_id = fields.Many2one('product.uom', 'Unit of Measure', ondelete='set null', index=True)
    price_unit = fields.Float('Unit Price', required=True, digits= dp.get_precision('Product Price'), default=0.0)
    quantity = fields.Float('Quantity', digits= dp.get_precision('Product Unit of Measure'),
                            required=True, default=1)
    account_analytic_id = fields.Many2one(related='issue_id.account_analytic_id', relation='account.analytic.account',
                                          string='Issue',store=True, readonly=True )

    date_publish = fields.Date(related='account_analytic_id.date_publish', readonly=True, string='Publishing Date', store=True,)

    tag_id = fields.Many2one('account.analytic.tag', 'Page Type', ondelete='set null', index=True)
    company_id = fields.Many2one(related='issue_id.company_id', relation='res.company',string='Company', store=True, readonly=True)
    price_subtotal = fields.Float(compute='_amount_line', string='Amount',
       digits = dp.get_precision('Account'), store=True)
    estimated_price = fields.Float('Estimate',)
    invoice_line_id = fields.Many2one('account.invoice.line', 'Invoice Line', readonly=True)
    invoice_id = fields.Many2one(related='invoice_line_id.invoice_id', relation='account.invoice', string='Invoice', readonly=True)
    state = fields.Selection(
        [('cancel', 'Cancelled'),
         ('draft', 'Draft'),
         ('confirmed', 'Confirmed'),
         ('exception', 'Exception'),
         ('done', 'Done')],
        'Status', required=True, readonly=True, default='draft',
        help='* The \'Draft\' status is set when the related hon issue in draft status. \
                    \n* The \'Confirmed\' status is set when the related hon issue is confirmed. \
                    \n* The \'Exception\' status is set when the related hon issue is set as exception. \
                    \n* The \'Done\' status is set when the hon line has been picked. \
                    \n* The \'Cancelled\' status is set when a user cancel the hon issue related.')
    gratis = fields.Boolean('Gratis',  help="It indicates that no letter/invoice is generated.")

    ## TODO: This method is not in use
    @api.multi
    def button_cancel(self):
        if self.invoice_line_id:
            raise UserError(_('You cannot cancel a Hon line that has already been invoiced.'))
        self.write({'state': 'cancel'})

    @api.multi
    def action_line_confirm(self):
        self.write({'state': 'confirmed'})

    @api.multi
    def action_line_unconfirm(self):
        self.write({'state': 'draft'})

    # TODO: This method is not in use
    @api.multi
    def action_line_done(self):
        self.write({'state': 'done'})
        self.issue_id.action_done()

    @api.multi
    def unlink(self):
        """Allows to delete hon lines in draft,cancel states"""
        for rec in self:
            if rec.state not in ['draft', 'cancel']:
                raise UserError(_('Cannot delete a hon line which is in state \'%s\'.') %(rec.state,))
        return super(HonIssueLine, self).unlink()


    @api.onchange('product_category_id')
    def product_category_change(self):
        if not self.product_category_id or not self.product_id:
            return {}

        if self.product_category_id is not self.product_id.categ_id:
            self.product_id = False


    @api.onchange('partner_id', 'product_id')
    def _onchange_calculatePrice(self):
        user = self.env.user
        context = dict(self._context)
        company_id = context.get('company_id', user.company_id.id)
        context.update({'company_id': company_id, 'force_company': company_id})
        part = self.partner_id
        if part.lang:
            context.update({'lang': part.lang})
        self.employee = True if part.employee else False

        # if 'nsm_supplier_portal' in self.env['ir.module.module']._installed():
        #     if part.product_category_ids:
        #         self.product_category_id = part.product_category_ids[0].id

        res = self.product_id
        a = res.property_account_expense_id.id
        if not a:
            a = res.categ_id.property_account_expense_categ_id.id
        if a:
            self.account_id = a
        pricelist = self.env['partner.product.price'].search([('product_id','=',self.product_id.id),
                             ('partner_id','=', self.partner_id.id),
                             ('company_id','=', company_id)])
        if len(pricelist) >= 1 :
            price = pricelist
            if price :
                self.price_unit = price[0].price_unit

    @api.model
    def _prepare_hon_issue_line_invoice_line(self, account_id=False):
        """Prepare the dict of values to create the new invoice line for a
           honorarium line. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record line: hon.issue.line record to invoice
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
                raise UserError(_(
                    'There is no Fiscal Position defined or Expense category account defined for default properties of Product categories.'))
            res = {
                'hon_issue_line_id': self.id,
                'account_analytic_id': self.account_analytic_id.id,
                'name': self.name,
                'sequence': self.sequence,
                'origin': self.issue_id.name,
                'account_id': account_id,
                'price_unit': self.price_unit,
                'quantity': qty,
                'product_id': self.product_id.id,
                'analytic_tag_ids': [(6, 0, [self.tag_id.id])],
            }
        return res

    @api.multi
    def invoice_line_create(self):
        create_ids = []
        # hon = set()

        for line in self:
            vals = line._prepare_hon_issue_line_invoice_line(account_id=False)
            if vals:
                invln = self.env['account.invoice.line'].create(vals)
                line.write({'invoice_line_id': invln.id})
                # hon.add(line.issue_id.id)
                create_ids.append(invln.id)

        return create_ids




