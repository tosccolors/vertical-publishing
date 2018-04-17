# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2016 Magnus (<http://www.magnus.nl>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, exceptions, models, _
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import ValidationError, UserError


class SaleOrder(models.Model):
    _inherit = ["sale.order"]

    subscription = fields.Boolean('Subscription', default=False)

    @api.multi
    def check_limit(self):
        """Check if credit limit for partner was exceeded."""
        self.ensure_one()
        partner = self.partner_id
        moveline_obj = self.env['account.move.line']
        movelines = moveline_obj.\
            search([('partner_id', '=', partner.id),
                    ('account_id.user_type_id.type', 'in',
                    ['receivable', 'payable']),
                    ('full_reconcile_id', '=', False)])

        debit, credit = 0.0, 0.0
        today_dt = datetime.strftime(datetime.now().date(), DF)
        for line in movelines:
            if line.date_maturity < today_dt:
                credit += line.debit
                debit += line.credit

        if (credit - debit + self.amount_total) > partner.credit_limit:
            # Consider partners who are under a company.
            msg = 'Can not confirm Sale Order,Total mature due Amount ' \
                  '%s as on %s !\nCheck Partner Accounts or Credit ' \
                  'Limits !' % (credit - debit, today_dt)
            raise UserError(_('Credit Over Limits !\n' + msg))
        else:
            return True

    @api.multi
    def action_confirm(self):
        """Extend to check credit limit before confirming sale order."""
        for order in self:
            if order.subscription:
                order.check_limit()
        return super(SaleOrder, self).action_confirm()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    subscription = fields.Boolean(related='order_id.subscription', string='Subscription', store=True)
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    must_have_dates = fields.Boolean(related='product_id.subscription_product', readonly=True)

    @api.multi
    @api.onchange('product_id')
    def set_start_date(self):
        for order_line in self:
            if order_line.product_id.subscription_product:
                order_line.start_date = datetime.today()


    @api.multi
    @api.constrains('start_date', 'end_date')
    def _check_start_end_dates(self):
        for orderline in self:
            if orderline.start_date and not orderline.end_date:
                raise ValidationError(
                    _("Missing End Date for order line with "
                      "Description '%s'.")
                    % (orderline.name))
            if orderline.end_date and not orderline.start_date:
                raise ValidationError(
                    _("Missing Start Date for order line with "
                      "Description '%s'.")
                    % (orderline.name))
            if orderline.end_date and orderline.start_date and \
                    orderline.start_date > orderline.end_date:
                raise ValidationError(
                    _("Start Date should be before or be the same as "
                      "End Date for order line with Description '%s'.")
                    % (orderline.name))

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        if self.product_id.subscription_product:
            res['start_date'] = self.start_date
            res['end_date'] = self.end_date
            account = self.product_id.delivery_obligation_account
            fpos = self.order_id.fiscal_position_id or self.order_id.partner_id.property_account_position_id
            if fpos:
                account = fpos.map_account(account)
            res['account_id'] = account.id
        return res