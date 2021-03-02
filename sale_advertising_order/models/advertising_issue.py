# -*- coding: utf-8 -*-
# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
import datetime

class AdvertisingIssue(models.Model):
    _name = "sale.advertising.issue"
    _inherits = {
        'account.analytic.account': 'analytic_account_id',
    }
    _description="Sale Advertising Issue"

    @api.model
    def _get_attribute_domain(self):
        id = self.env.ref('sale_advertising_order.attribute_title').id
        return [('attribute_id', '=', id)]

    @api.depends('parent_id')
    @api.multi
    def _compute_medium_domain(self):
        """
        Compute the domain for the Medium domain.
        """
        for rec in self:
            if rec.parent_id:
                np = self.env.ref('sale_advertising_order.newspaper_advertising_category').id
                mag = self.env.ref('sale_advertising_order.magazine_advertising_category').id
                if rec.parent_id.medium.id in [np, mag]:
                    ads = self.env.ref('sale_advertising_order.title_pricelist_category').id
                    rec.medium_domain = json.dumps(
                                        [('parent_id', '=', ads)]
                    )
                else:
                    ads = [self.env.ref('sale_advertising_order.online_advertising_category').id]
                    rec.medium_domain = json.dumps(
                                        [('id', 'in', ads)]
                    )
            else:
                ads = self.env.ref('sale_advertising_order.advertising_category').id
                rec.medium_domain = json.dumps(
                                    [('parent_id', '=', ads)]
                )

    @api.one
    @api.depends('issue_date')
    def _week_number(self):
        """
        Compute the week number of the issue.
        """
        for issue in self:
            if self.issue_date:
                wk = fields.Date.from_string(self.issue_date).isocalendar()[1]
                issue.update({
                    'issue_week_number': wk,
                    'week_number_even': wk % 2 == 0
                })

    @api.depends('available_ids.available_qty')
    @api.multi
    def _availability(self):
        self.ensure_one()
        qty = 0
        for line in self.available_ids:
            qty += line.available_qty
        self.amount_total = qty

    @api.multi
    def calc_page_space(self, page_id):
        self.ensure_one()
        av_space = 0
        for line in self.available_ids.filtered(lambda record: record.page_id.id == page_id):
            av_space += line.available_qty or 0
        return av_space

    name = fields.Char('Name', size=64, required=True)
    code = fields.Char('Code', size=16, required=True)
    child_ids = fields.One2many('sale.advertising.issue', 'parent_id', 'Issues',)
    available_ids = fields.One2many('sale.advertising.available', 'adv_issue_id', 'Available', )
    parent_id = fields.Many2one('sale.advertising.issue', 'Title', index=True)
    product_attribute_value_id = fields.Many2one('product.attribute.value', string='Variant Title',
                                                 domain=_get_attribute_domain)
    analytic_account_id = fields.Many2one('account.analytic.account', required=True,
                                      string='Related Analytic Account', ondelete='restrict',
                                      help='Analytic-related data of the issue')
    issue_date = fields.Date('Issue Date')
    issue_week_number = fields.Integer(string='Week Number', store=True, readonly=True, compute='_week_number' )
    week_number_even = fields.Boolean(string='Even Week Number', store=True, readonly=True, compute='_week_number' )
    deadline = fields.Datetime('Deadline', help='Closing Time for Sales')
    medium_domain = fields.Char(compute='_compute_medium_domain', readonly=True, store=False,)
    medium = fields.Many2one('product.category','Medium', required=True)
    state = fields.Selection([('open','Open'),('close','Close')], 'State', default='open')
    default_note = fields.Text('Default Note')
    amount_total = fields.Integer(computed=_availability, string='Available Space', store=True, readonly=True,)
    price_edit = fields.Boolean('Price Editable')
    active = fields.Boolean('Active', default=True)


    @api.onchange('parent_id')
    def onchange_parent_id(self):
        domain = {}
        self.medium = False
        if self.parent_id:
            if self.parent_id.medium.id == self.env.ref('sale_advertising_order.newspaper_advertising_category').id:
                ads = self.env.ref('sale_advertising_order.title_pricelist_category').id
                domain['medium'] = [('parent_id', '=', ads)]
            else:
                ads = [self.env.ref('sale_advertising_order.magazine_advertising_category').id]
                ads.append(self.env.ref('sale_advertising_order.online_advertising_category').id)
                domain['medium'] = [('id', 'in', ads)]

        else:
            ads = self.env.ref('sale_advertising_order.advertising_category').id
            domain['medium'] = [('parent_id', '=', ads)]
        return {'domain': domain }

class AdvertisingIssueAvailability(models.Model):
    _name = "sale.advertising.available"
    _description="Sale Advertising Issue Availability"

    adv_issue_id = fields.Many2one('sale.advertising.issue', string='Advertising Issue Reference', ondelete='cascade', index=True)
    issue_date = fields.Date(related='adv_issue_id.issue_date', string='Issue Date')
    name = fields.Selection([('Opboeking','Opboeking'),('Afboeking','Afboeking')], default='Afboeking', string='Description', required=True)
    available_qty = fields.Integer('Available', required=True, default=0)
    page_id = fields.Many2one('sale.advertising.page', required=True, string='Advertising Page')
    order_line_id = fields.Many2one('sale.order.line', string='Ad Placement', readonly=False)

    @api.multi
    @api.constrains('order_line_id')
    def _check_unique_orderline(self):
        for rec in self:
            if rec.order_line_id:
                if len(self.search([('order_line_id', '=', rec.order_line_id.id),
                        ('id', '!=', rec.id)])) > 0:
                    raise UserError(_('There can only be one Availability posting per order_line'))

class AdvertisingPage(models.Model):
    _name = "sale.advertising.page"
    _description="Sale Advertising Pages"

    name = fields.Char('Description', size=64, required=True)
