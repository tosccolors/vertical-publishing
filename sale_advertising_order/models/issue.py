# -*- coding: utf-8 -*-
# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class AdvertisingIssue(models.Model):
    _name = "sale.advertising.issue"
    _inherits = {
        'account.analytic.account': 'analytic_account_id',
    }
    _description = "Sale Advertising Issue"

    @api.model
    def _get_attribute_domain(self):
        id = self.env.ref('sale_advertising_order.attribute_title').id
        return [('attribute_id', '=', id)]

    @api.depends('parent_id')
    def _compute_medium_domain(self):
        """
        Compute the domain for the Medium domain.
        """
        for rec in self:
            domain = ''
            if rec.parent_id:
                i2p = self.env.ref('sale_advertising_order.interface_portal_category').id
                domain = json.dumps(
                    [('parent_id', 'child_of', i2p)]
                )
            rec.medium_domain = domain

    @api.depends('issue_date')
    def _week_number(self):
        """
        Compute the week number of the issue.
        """
        for issue in self:
            wk, evenwk = 0, False
            if issue.issue_date:
                wk = fields.Date.from_string(issue.issue_date).isocalendar()[1]
                evenwk = wk % 2 == 0

            issue.issue_week_number = wk
            issue.week_number_even = evenwk


    @api.depends('child_ids')
    def _compute_issue_count(self):
        for rec in self:
            rec.issue_count = len(rec.child_ids)


    name = fields.Char('Name', size=64, required=True)
    code = fields.Char('Code', size=16, required=True)
    child_ids = fields.One2many('sale.advertising.issue', 'parent_id', 'Issues'
                                , index=True)
    parent_id = fields.Many2one('sale.advertising.issue', 'Title', index=True, ondelete='cascade')
    product_attribute_value_id = fields.Many2one('product.attribute.value', string='Variant Title',
                                                 domain=_get_attribute_domain)
    analytic_account_id = fields.Many2one('account.analytic.account', required=True,
                                          string='Related Analytic Account', ondelete='restrict',
                                          help='Analytic-related data of the issue')
    issue_date = fields.Date('Issue Date')
    issue_week_number = fields.Integer(string='Week Number', store=True, readonly=True, compute='_week_number')
    week_number_even = fields.Boolean(string='Even Week Number', store=True, readonly=True, compute='_week_number')
    deadline = fields.Datetime('Deadline', help='Closing Time for Sales')
    medium_domain = fields.Char(compute='_compute_medium_domain', readonly=True, store=False, )
    state = fields.Selection([('open', 'Open'), ('close', 'Close')], 'Status', default='open')
    default_note = fields.Text('Default Note')

    price_edit = fields.Boolean('Price Editable') # TODO: Check usage!
    active = fields.Boolean('Active', default=True)
    issue_count = fields.Integer("Issue count", compute='_compute_issue_count')
    to_update_issdt = fields.Boolean("To Update Issue Date", default=False, copy=False)

    medium = fields.Many2many('product.category', 'adv_issue_categ_rel', 'adv_issue_id', 'category_id', 'Medium',
                              required=True)


    @api.onchange('parent_id')
    def onchange_parent_id(self):
        domain = {}
        self.medium = False
        if self.parent_id:
            i2p = self.env.ref('sale_advertising_order.interface_portal_category').id
            domain['medium'] = [('parent_id', 'child_of', i2p)]
        return {'domain': domain}


    def action_open_issue(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale_advertising_order.action_sale_advertising_issue_title")

        # display all issue(s) of current title
        action['domain'] = [('id', 'child_of', self.id), ('id', '!=', self.id)]
        return action

    def validate_medium(self):
        if self.parent_id:
            if len(self.medium.ids) > 1:
                raise ValidationError(_("You can't select more than one medium."))

    @api.onchange('medium')
    def _onchange_medium(self):
        self.validate_medium()

    @api.constrains('medium')
    def _check_medium(self):
        self.validate_medium()

    @api.onchange('issue_date')
    def _onchange_issue_date(self):
        if self.ids:
            self.to_update_issdt = True


class DiscountReason(models.Model):
    _name = "discount.reason"
    _description = "Discount Reason"

    name = fields.Char('Name', size=64, required=True)
