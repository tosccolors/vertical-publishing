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

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, exceptions, models, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import ValidationError, UserError
import odoo.addons.decimal_precision as dp

VALUES = [(1,'Anbos lid'), (2, 'Andere nieuwsbronnen/internet'), (3, 'Actie/proefabonnement'), (4,'Bedrijf is opgeheven/failliet/fusie'), (5, 'Betalingsachterstand'), (6, 'Klachten over de slechte bezorging'), (7, 'Blad retour/factuur retour'), (8, 'Is onder curatele gezet/schuldsanering'), (9, 'Dubbel abonnement'), (10, 'Einde proef/kado abonnement'), (11, 'Bezuinigen/ financieel'), (12, 'Gaat samenlezen, ivm financien'), (13, 'Geen BDU-medewerker meer'), (14, 'Geen interesse'), (15, 'Geen opgave'), (16, 'Gezondheidsredenen (ouderd./ziek/dement)'), (17, 'Geen student meer'), (18, 'In overleg met ACM'), (19, 'Leest via werkgever / leest samen'), (20, 'Met pensioen'), (21, 'Verhuizen/emigreren'), (22, 'Nabellen opzeggers'), (23, 'Naar incassobureau'), (24, 'Nogmaals toegestuurd'), (25, 'Niet meer werkzaam'), (26, 'Omgezet naar digitaal/ander soort abo'), (27, 'Overstap naar concurrent / Andere keuze'), (28, 'Oneens met verlenging'), (29, 'Ontevreden over digitale versie'), (30, 'Overleden'), (31, 'Op verzoek betalende instantie'), (32, 'Persoonlijke omstandigheden'), (33, 'Redactioneel / inhoud'), (34, 'Retour'), (35, 'Te duur'), (36, 'Telefonische opzegging'), (37, 'Tijdelijke stopzetting'), (38, 'Telemarketing actie Tijdschriften'), (39, 'Verlengingsaanbieding'), (40, 'Via de mail benaderd')]

class SaleOrder(models.Model):
    _inherit = ["sale.order"]

    subscription = fields.Boolean('Subscription', default=False)
    subscription_payment_mode_id = fields.Many2one(related='partner_id.subscription_customer_payment_mode_id', relation='account.payment.mode', string='Payment method', company_dependent=True,domain=[('payment_type', '=', 'inbound')],help="Select the default subscription payment mode for this customer.",readonly=True, copy=False, store=True)
    delivery_type = fields.Many2one('delivery.list.type', 'Delivery Type', default=lambda self: self.env.ref('publishing_subscription_order.delivery_list_type_regular', False) if 'params' in self._context and 'action' in self._context['params'] and self._context['params']['action'] ==  self.env.ref('publishing_subscription_order.action_orders_subscription').id else False)

    @api.depends('order_line.price_total', 'order_line.computed_discount', 'partner_id')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        super(SaleOrder, self.filtered(lambda record: record.subscription != True))._amount_all()
        for order in self.filtered('subscription'):
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    price = line.actual_unit_price * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                    product=line.product_id, partner=order.partner_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })


    @api.multi
    def check_limit(self):
        """Check if credit limit for partner was exceeded."""
        self.ensure_one()
        partner = self.partner_id
        partner.is_subscription_customer = True
        if not partner.is_subscription_customer:
            partner.is_subscription_customer = True
        # if not partner.subscription_customer_payment_mode_id or not partner.property_subscription_payment_term_id:
        #     raise UserError(_("Can not confirm Sale Order Partner subscription's details are not completed"))

        if not partner.is_subscription_customer:
            raise UserError(_("Can not confirm Sale Order Partner is not subscription partner"
                              ))
        #set payment term and payment mode from customer
        if not self.payment_term_id:
            self.payment_term_id = partner.property_subscription_payment_term_id and partner.property_subscription_payment_term_id.id or False
        if not self.payment_mode_id:
            self.payment_mode_id = partner.subscription_customer_payment_mode_id
        return True

    @api.multi
    def action_confirm(self):
        """Extend to check credit limit before confirming sale order."""
        for order in self.filtered('subscription'):
            if order.partner_id:
                order.check_limit()
        return super(SaleOrder, self).action_confirm()

    def update_acc_mgr_sp(self):
        if not self.advertising and not self.subscription:
            self.user_id = self.partner_id.user_id.id if self.partner_id.user_id else False
            self.partner_acc_mgr = False
            if self.partner_id:
                if self.company_id and self.company_id.name == 'BDUmedia BV':
                    self.user_id = self._uid
                    self.partner_acc_mgr = self.partner_id.user_id.id if self.partner_id.user_id else False

    @api.multi
    @api.onchange('partner_id', 'published_customer', 'advertising_agency', 'agency_is_publish')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Subscription Payment term
        """
        super(SaleOrder, self).onchange_partner_id()
        if self.subscription:
            address = self.published_customer.address_get(['delivery'])
            self.partner_shipping_id = address['delivery']
            if self.partner_id:
                # Subscription:
                self.payment_term_id = self.partner_id.property_subscription_payment_term_id and self.partner_id.property_subscription_payment_term_id.id or False
                self.payment_mode_id = self.partner_id.subscription_customer_payment_mode_id

    @api.model
    def _prepare_invoice(self,):
        res = super(SaleOrder, self)._prepare_invoice()
        if self.filtered('subscription'):
            res['payment_term_id'] = self.partner_id.property_subscription_payment_term_id.id or False
        return res

    @api.multi
    def action_draft(self):
        res = super(SaleOrder, self).action_draft()
        orders = self.filtered('subscription')
        for line in orders.order_line:
            if line.can_cancel and line.subscription_cancel:
                line.can_cancel  = False
                line.subscription_cancel = False
                line.date_cancel = False
        return res

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    @api.depends('product_uom_qty', 'order_id.partner_id', 'order_id.nett_nett', 'nett_nett',
                 'subtotal_before_agency_disc',
                 'price_unit', 'tax_id', 'discount')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        super(SaleOrderLine, self.filtered(lambda record: record.subscription != True))._compute_amount()
        for line in self.filtered('subscription'):
            unit_price = line.price_unit or 0.0
            unit_price = round(unit_price * (1 - (line.discount or 0.0) / 100.0), 5)
            taxes = line.tax_id.compute_all(unit_price, line.order_id.currency_id, line.product_uom_qty,
                                            product=line.product_id,
                                            partner=line.order_id.partner_id)
            line.update({
                'actual_unit_price': round(unit_price, 3),
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

        return True

    @api.multi
    @api.depends('product_template_id')
    def _compute_price_edit(self):
        """
        Compute if price_unit should be editable.
        """
        super(SaleOrderLine, self.filtered(lambda record: record.subscription != True))._compute_price_edit()
        for line in self.filtered('subscription'):
            line.number_of_issues = line.product_template_id.number_of_issues
            if line.product_template_id.price_edit:
                line.price_edit = True

    subscription = fields.Boolean(related='order_id.subscription', string='Subscription', readonly=True, store=True)
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    must_have_dates = fields.Boolean(related='product_id.product_tmpl_id.subscription_product', readonly=True, copy=False, store=True)
    number_of_issues = fields.Integer(string='No. Of Issues', digits=dp.get_precision('Product Unit of Measure'))
    delivered_issues = fields.Integer(string='Issues delivered', digits=dp.get_precision('Product Unit of Measure'), copy=False)
    can_cancel = fields.Boolean('Can cancelled?')
    can_renew = fields.Boolean('Can Renewed?', default=False)
    date_cancel = fields.Date('Cancelled date', help="Cron will cancel this line on selected date.")
    reason_cancel = fields.Selection(VALUES, string='Reason Cancellation')
    renew_product_id = fields.Many2one('product.product','Renewal Product')
    subscription_cancel = fields.Boolean('Subscription cancelled',copy=False)
    line_renewed = fields.Boolean('Subscription Renewed', copy=False)
    delivery_type = fields.Many2one(related='order_id.delivery_type', readonly=True, copy=False, store=True)
    weekday_ids = fields.Many2many('week.days', 'weekday_sale_line_rel', 'order_line_id', 'weekday_id', 'Weekdays')
    temporary_stop = fields.Boolean('Temporary Delivery Stop', copy=False)
    tmp_start_date = fields.Date('Start Of Delivery Stop')
    tmp_end_date = fields.Date('End Of Delivery Stop')
    renew_disc = fields.Boolean('Renew With Discount', copy=False)

    @api.multi
    @api.constrains('start_date', 'end_date', 'temporary_stop', 'tmp_start_date', 'tmp_end_date')
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
            if self.temporary_stop:
                if orderline.tmp_start_date and not orderline.tmp_end_date:
                    raise ValidationError(
                        _("Missing End Of Delivery Stop Date for order line with "
                          "Description '%s'.")
                        % (orderline.name))
                if orderline.tmp_end_date and not orderline.tmp_start_date:
                    raise ValidationError(
                        _("Missing Start Of Delivery Stop date for order line with "
                          "Description '%s'.")
                        % (orderline.name))
                if orderline.tmp_end_date and orderline.tmp_start_date and \
                        orderline.tmp_start_date > orderline.tmp_end_date:
                    raise ValidationError(
                        _("Start Of Delivery Stop Date should be before "
                          "End Of Delivery Stop Date for order line with Description '%s'.")
                        % (orderline.name))

    @api.onchange('tmp_start_date')
    def onchange_temporary_delivery_stop(self):
        vals = {}
        vals['temporary_stop'] = True if self.tmp_start_date else False
        return {'value': vals}

    @api.onchange('medium')
    def onchange_medium(self):
        vals, data, result = {}, {}, {}
        if self.advertising:
            result = super(SaleOrderLine, self).onchange_medium()
            if 'domain' in result:
                if 'ad_class' in result['domain'] and result['domain']['ad_class']:
                    result['domain']['ad_class'] = result['domain']['ad_class']+[('subscription_categ','=', False)]
            return result
        elif not self.subscription:
            return {'value':vals}
        if self.medium:
            child_id = [x.id for x in self.medium.child_id.filtered('subscription_categ')]
            if not self.ad_class or self.ad_class.id not in child_id:
                if len(child_id) == 1:
                    vals['ad_class'] = child_id[0]
                else:
                    vals['ad_class'] = False
            data['ad_class'] = [('id', 'child_of', self.medium.id), ('type', '!=', 'view'),
                                ('subscription_categ', '=', True)]
            titles = self.env['sale.advertising.issue'].search(
                [('parent_id', '=', False), ('medium', '=', self.medium.id), ('subscription_title', '=', True)]).ids
            if not self.title or self.title.id not in titles:
                if titles and len(titles) == 1:
                    vals['title'] = titles[0]
                else:
                    vals['title'] = False
                    vals['product_id'] = False
        else:
            vals['ad_class'] = False
            data = {'ad_class': []}
            vals['title'] = False
            vals['product_id'] = False

        return {'value': vals, 'domain': data}

    @api.onchange('ad_class','title')
    def onchange_ad_class(self):
        vals, data, result = {}, {}, {}

        def _get_products(self):
            ids = []
            product_ids = self.env['product.product'].search(
                [('categ_id', '=', self.ad_class.id), ('subscription_product', '=', True)])
            if product_ids:
                for product in product_ids:
                    if self.title.product_attribute_value_id:
                        if self.title.product_attribute_value_id.id in product.attribute_value_ids.ids:
                            ids.append(product.id)
                    else:
                        if not product.attribute_value_ids: ids.append(product.id)
            return ids

        def _no_template(self, vals):
            vals['product_template_id'] = False
            vals['product_id'] = False
            return vals

        if self.advertising:
            result = super(SaleOrderLine, self).onchange_ad_class()
            if 'domain' in result:
                if 'product_template_id' in result['domain'] and result['domain']['product_template_id']:
                    result['domain']['product_template_id'] = result['domain']['product_template_id']+[('subscription_product','=', False)]
            return result
        elif not self.subscription:
            return {'value': vals}

        data['product_id'] = [('subscription_product', '=', True)]

        if self.ad_class: data['product_id'] += [('categ_id', '=', self.ad_class.id)]

        if self.ad_class and self.title :
            prod_ids = _get_products(self)
            if prod_ids:
                data['product_id'] += [('id', 'in', prod_ids)]
                product_ids = self.env['product.product'].search([('subscription_product', '=', True), ('categ_id', '=', self.ad_class.id), ('id', 'in', prod_ids)])

                if len(product_ids) == 1:
                    pro_tmpl = product_ids.product_tmpl_id
                    vals['product_template_id'] = pro_tmpl.id
                    vals['product_id'] = product_ids[0]
                    vals['product_uom'] = pro_tmpl.uom_id
                    vals['number_of_issues'] = pro_tmpl.number_of_issues
                    vals['can_renew'] = pro_tmpl.can_renew
                    vals['renew_product_id'] = pro_tmpl.renew_product_id
            else:
                vals.update(_no_template(self, vals))
        else:
            if not self.product_id:
                vals.update(_no_template(self, vals))

        if self.title:
            adv_issue = self.env['sale.advertising.issue'].search([('subscription_title', '=', True),('parent_id', '=', self.title.id),('issue_date', '!=', False),('issue_date', '>', datetime.today().date())], order='issue_date', limit=1)
            if adv_issue:
                self.start_date = adv_issue.issue_date
            else:
                self.start_date = self.end_date = datetime.today().date() + timedelta(days=1)

            if not self.medium:
                ads = self.env.ref('sale_advertising_order.advertising_category').id
                if self.title.parent_id:
                    medium = self.title.medium.parent_id.id if ads != self.title.medium.parent_id.id else self.title.medium.id
                else:
                    medium = self.title.medium.id
                data['medium'] = [('parent_id', '=', ads)]
                vals['medium'] = medium
        else:
            self.start_date = self.end_date = False

        return {'value': vals, 'domain': data, 'warning': result}

    @api.onchange('renew_product_id')
    def onchange_renewal(self):
        vals = {}
        if self.renew_product_id:
            vals['can_renew'] = True
            vals['date_cancel'] = False
        else:
            vals['can_renew'] = False
            vals['renew_disc'] = False
        return {'value': vals}

    @api.onchange('date_cancel')
    def onchange_date_cancel(self):
        vals = {}
        if self.date_cancel:
            vals['can_cancel'] = True
            vals['renew_product_id'] = False
        else:
            vals['can_cancel'] = False
        return {'value': vals}

    @api.onchange('start_date', 'end_date')
    def onchange_start_end_date_subs(self):
        vals = {}
        if not self.subscription:
            return {'value': vals}
        if self.product_id and self.product_template_id:
            if not self.start_date:
                vals['start_date'] = datetime.today().date()
            elif self.start_date:
                vals['end_date'] = datetime.strptime(str(self.start_date), "%Y-%m-%d").date() + timedelta(
                days=self.product_template_id.subscr_number_of_days)
        else:
            vals = {'end_date': False}
            if not self.title:
                vals = {'start_date': False}
        return {'value': vals}

    @api.onchange('product_id')
    def onchange_product_subs(self):
        vals = {}
        if not self.subscription:
            return {'value': vals}

        def _line_update(line):
            dic = {}
            product_template_id = product_id.product_tmpl_id
            dic['number_of_issues'] = product_template_id.number_of_issues
            dic['can_renew'] = product_template_id.can_renew
            dic['renew_product_id'] = product_template_id.renew_product_id
            dic['weekday_ids'] = [(6, 0, product_template_id.weekday_ids.ids)]
            start_date = line.start_date
            if not start_date:
                start_date = datetime.today().date()
                dic['start_date'] = start_date
            if start_date:
                dic['end_date'] = datetime.strptime(str(start_date), "%Y-%m-%d").date() + timedelta(
                    days=product_template_id.subscr_number_of_days)
            return dic

        def _reset_line():
            return {'product_template_id': False,
                    'name': '',
                    'number_of_issues': 0,
                    'can_renew': False,
                    'renew_product_id': False,
                    'weekday_ids': [(6, 0, [])]
                    }

        product_id = self.product_id
        if 'cronRenewal' in self.env.context:
            product_id = self.renew_product_id
        if product_id:
            vals['ad_class'] = product_id.categ_id.id
            attr = product_id.attribute_value_ids[0]
            vals['title'] = self.env['sale.advertising.issue'].search(
                [('product_attribute_value_id', '=', attr.id)], limit=1).id

            if product_id:
                name = product_id.name_get()[0][1]
                if product_id.description_sale:
                    name += '\n' + product_id.description_sale
                vals.update({
                    'product_template_id': product_id.product_tmpl_id.id,
                    'name': name,
                })
                vals.update(_line_update(self))
            else:
                vals.update(_reset_line())

        else:
            vals.update(_reset_line())
        return {'value': vals}

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        if self.product_id.subscription_product:
            res['start_date'] = self.start_date
            res['end_date'] = self.end_date
#            account = self.product_id.delivery_obligation_account_id
#            fpos = self.order_id.fiscal_position_id or self.order_id.partner_id.property_account_position_id
#            if fpos:
#                account = fpos.map_account(account)
#            res['account_id'] = account.id
        return res


    @api.multi
    def create_renewal_line(self, order_lines=[]):
        sol_obj = self.env['sale.order.line']

        #new period start on end date of expired subscription, has end_date with more robust delta period, regardless of rundate
        for line in order_lines:

            #some better handling of leap day, months and quarters
            if line.renew_product_id.subscr_number_of_days==730 :
                delta = relativedelta(months=24)
            elif line.renew_product_id.subscr_number_of_days==365 :
                delta = relativedelta(months=12)
            elif line.renew_product_id.subscr_number_of_days==183 :
                delta = relativedelta(months=6)
            elif line.renew_product_id.subscr_number_of_days==92 :
                delta = relativedelta(months=3)
            elif line.renew_product_id.subscr_number_of_days==61 :
                delta = relativedelta(months=2)
            elif line.renew_product_id.subscr_number_of_days==31 :
                delta = relativedelta(months=1)
            else :
                #as it was
                delta = timedelta(days=line.renew_product_id.subscr_number_of_days)
            new_end_date = datetime.strptime(line.end_date,DF).date() + delta

            res = {
                'start_date'      : line.end_date,
                'end_date'        : new_end_date,
                'order_id'        : line.order_id.id,
                'price_unit'      : line.renew_product_id.lst_price or False,
                'number_of_issues': line.renew_product_id.product_tmpl_id.number_of_issues or 0,
                'can_renew'       : True,
                'renew_product_id': line.renew_product_id.id,
                'discount'        : 0
            }
            if line.product_id != line.renew_product_id:
                res.update({
                    'product_template_id' : line.renew_product_id.product_tmpl_id.id or False,
                    'product_id'          : line.renew_product_id.id or False,
                    'number_of_issues'    : line.renew_product_id.product_tmpl_id.number_of_issues or 0,
                })

        ctx = self.env.context.copy()
        ctx.update({'cronRenewal':True})
        for line in order_lines:
            res = line.with_context(ctx).onchange_product_subs()['value']
            tmpl_prod = line.renew_product_id.product_tmpl_id
            res.update({
                'start_date': datetime.today().date(),
                'end_date': datetime.today().date() + timedelta(days=line.renew_product_id.subscr_number_of_days),
                'order_id': line.order_id.id,
                'product_template_id': tmpl_prod and tmpl_prod.id,
                'product_id': line.renew_product_id.id,
                'number_of_issues': tmpl_prod.number_of_issues,
                'can_renew': tmpl_prod.can_renew,
                'renew_product_id': tmpl_prod.renew_product_id and tmpl_prod.renew_product_id.id,
                'price_unit':self.env['account.tax']._fix_tax_included_price_company(line._get_display_price(line.renew_product_id), line.renew_product_id.taxes_id, line.tax_id, line.company_id),
                'discount':0.0,
            })
            if line.renew_disc:
                res.update({
                    'discount': line.discount,
                    'discount_reason_id': line.discount_reason_id.id,
                })

            vals = line.copy_data(default=res)[0]
            sol_obj.create(vals)

            line.line_renewed = True

    @api.onchange('number_of_issues')
    def onchange_edition(self):
        if self.product_id and self.number_of_issues != self._origin.number_of_issues:
            self.number_of_issues = self.product_id.product_tmpl_id.number_of_issues

    @api.model
    def run_order_line_cancel(self):
        order_lines = self.search([('subscription','=',True),('state','in',('sale','done')),('subscription_cancel','=',False),('can_cancel','=',True),('date_cancel','<=',datetime.today().date())])
        return order_lines.write({'subscription_cancel': True})

    @api.model
    def run_order_line_renew(self):
        offset = int(self.env['ir.config_parameter'].search([('key','=','subscription_renewal_offset_in_days')]).value) or 10
        expiration_date = (datetime.today().date() + timedelta(days=offset)).strftime('%Y-%m-%d')
        order_lines = self.search(
            [('subscription','=',True),('state', 'in', ('sale', 'done')), ('can_renew', '=', True),('line_renewed', '=' ,False), ('end_date', '<', expiration_date )])
        self.create_renewal_line(order_lines)
        return True

class AdvertisingIssue(models.Model):
    _inherit = "sale.advertising.issue"

    subscription_title = fields.Boolean('Subscription Title')