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

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = ["sale.order"]

    @api.depends('order_line.price_total', 'company_id')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = max_cdiscount = 0.0
            cdiscount = []

            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                cdiscount.append(line.computed_discount)

                # FORWARDPORT UP TO 10.0
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=order.partner_shipping_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax

            if cdiscount:
                max_cdiscount = max(cdiscount)

            if order.company_id.verify_order_setting < amount_untaxed or order.company_id.verify_discount_setting < max_cdiscount:
                ver_tr_exc = True
            else: ver_tr_exc = False

            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
                'ver_tr_exc': ver_tr_exc,
            })


    state = fields.Selection([
        ('draft', 'Quotation'),
        ('submitted', 'Submitted for Approval'),
        ('approved1', 'Approved by Sales Mgr'),
        ('approved2', 'Approved by Traffic'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sale Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    published_customer = fields.Many2one('res.partner', 'Advertiser', domain=[('customer','=',True)])
    advertising_agency = fields.Many2one('res.partner', 'Advertising Agency', domain=[('customer','=',True)])
    nett_nett = fields.Boolean('Netto Netto Deal', default=False)
    customer_contact = fields.Many2one('res.partner', 'Payer Contact Person', domain=[('customer','=',True)])
    traffic_employee = fields.Many2one('res.users', 'Traffic Employee',)
    traffic_comments = fields.Text('Traffic Comments')
    traffic_appr_date = fields.Date('Traffic Confirmation Date', index=True, help="Date on which sales order is confirmed bij Traffic.")
    opportunity_subject = fields.Char('Opportunity Subject', size=64,
                          help="Subject of Opportunity from which this Sales Order is derived.")

    partner_acc_mgr = fields.Many2one(related='published_customer.user_id', relation='res.users', string='Account Manager', store=True , readonly=True)

    date_from = fields.Date(compute=lambda *a, **k: {}, string="Date from")
    date_to = fields.Date(compute=lambda *a, **k: {}, string="Date to")

    ver_tr_exc = fields.Boolean(string='Verification Treshold', store=True, readonly=True, compute='_amount_all', track_visibility='always')

    advertising = fields.Boolean('Advertising', default=False)


    # overridden:
    @api.multi
    @api.onchange('partner_id', 'published_customer', 'advertising_agency')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment term
        - Invoice address
        - Delivery address
        """

        # Advertiser:
        if self.advertising:
            if self.published_customer:
                self.partner_id = self.published_customer.id

            if self.advertising_agency:
                self.partner_id = self.advertising_agency

        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'payment_term_id': False,
                'fiscal_position_id': False,
                'customer_contact': False
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        if self.env.user.company_id.sale_note:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.user.company_id.sale_note

        if self.partner_id.user_id:
            values['user_id'] = self.partner_id.user_id.id
        if self.partner_id.team_id:
            values['team_id'] = self.partner_id.team_id.id
        self.update(values)

        if self.partner_id.type == 'contact':
            contact = self.env['res.partner'].search([('is_company','=', False),('type','=', 'contact'),('parent_id','=', self.partner_id.id)])
            if len(contact) >=1:
                contact_id = contact[0]
            else:
                contact_id = False
        elif addr['contact'] == addr['default']:
            contact_id = False
        else: contact_id = addr['contact']

        if self.order_line:
            warning = {'title':_('Warning'),
                                 'message':_('Changing the Customer can have a change in Agency Discount as a result.'
                                             'This change will only show after saving the order!'
                                             'Before saving the order the order lines and the total amounts may therefor'
                                             'show wrong values.')}
            return {'warning': warning}
        values['user_id'] = self._uid
        values['customer_contact'] = contact_id
        self.update(values)


    @api.multi
    def action_submit(self):
        for o in self:
            if not o.order_line:
                raise UserError(_('You cannot submit a quotation/sales order which has no line.'))
        return self.write({'state':'submitted'})

    @api.multi
    def action_approve2(self):
        return self.write({'state': 'approved2',
                           'traffic_appr_date': fields.Date.context_today(self)})

    @api.one
    def update_line_discount(self):
        self.ensure_one()
        order = self
        discount = order.partner_id.agency_discount or 0.0
        if order.nett_nett:
            discount = 0.0
        fiscal_position = order.partner_id.property_account_position_id

        for line in order.order_line:
            tax = []
            if fiscal_position:
                tax = fiscal_position.map_tax(line.product_id.taxes_id, line.product_id, order.partner_id).ids
            vals = {}
            vals['discount'] = discount
            vals['tax_id'] = [(6,0,tax)]

            line.write(vals)

        return True

    # --added deep
    @api.multi
    def action_approve1(self):
        self.action_submit()
        return self.write({'state':'approved1'})

    # --added deep
    @api.multi
    def action_refuse(self):
        self.action_submit()
        return self.write({'state':'draft'})

    # overridden: -- added deep
    @api.multi
    def print_quotation(self):
        self.filtered(lambda s: s.state == 'approved2').write({'state': 'sent'})
        return self.env['report'].get_action(self, 'sale.report_saleorder')


    @api.multi
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if 'partner_id' in vals or 'nett_nett' in vals:
            self.update_line_discount()
        return res

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        res.update_line_discount()
        return res



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

    @api.model
    def _domain_medium(self):
        ads = self.env.ref('sale_advertising_order.advertising_category').id
        return [('parent_id', '=', ads)]

    name = fields.Char('Name', size=64, required=True)
    child_ids = fields.One2many('sale.advertising.issue', 'parent_id', 'Issues',)
    parent_id = fields.Many2one('sale.advertising.issue', 'Title', index=True)
    product_attribute_value_id = fields.Many2one('product.attribute.value', string='Variant Title',
                                                 domain=_get_attribute_domain)
    analytic_account_id = fields.Many2one('account.analytic.account', required=True,
                                      string='Related Analytic Account', ondelete='restrict',
                                      help='Analytic-related data of the issue')
    issue_date = fields.Date('Issue Date')
    medium = fields.Many2one('product.category','Medium', domain=_domain_medium, required=True)
    state = fields.Selection([('open','Open'),('close','Close')], 'State', default='open')
    default_note = fields.Text('Default Note')


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:

            if not line.order_id.date_order:
                date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            else: date_order = line.order_id.date_order

            pricelist = line.order_id.pricelist_id and line.order_id.pricelist_id.id or False
            product_id = line.product_id and line.product_id.id or False
            order_partner_id = line.order_id.partner_id and line.order_id.partner_id.id or False
            discount = line.discount or 0.0
            comp_discount = 0.00

            if line.order_id.nett_nett:
                discount = 0.0
            product_uom = line.product_uom and line.product_uom.id or False

            price_unit = line.price_unit

            if line.advertising:
                price_unit = line.actual_unit_price
                if product_id:
                    unit_price = self.env['account.tax']._fix_tax_included_price(line._get_display_price(line.product_id), line.product_id.taxes_id, line.tax_id)

                else: unit_price = 0.0
                if unit_price > 0.0:
                    comp_discount = (unit_price - line.actual_unit_price)/unit_price * 100.0

            price = price_unit * (1 - discount / 100.0)
            subtotal_bad = price_unit * line.product_uom_qty
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_id)

            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
                'computed_discount': comp_discount,
                'subtotal_before_agency_disc': subtotal_bad,
                'discount_dummy': line.discount,

            })

    @api.model
    def _domain_medium(self):
        ads = self.env.ref('sale_advertising_order.advertising_category').id
        return [('parent_id', '=', ads)]


    layout_remark = fields.Text('Layout Remark')
    title = fields.Many2one('sale.advertising.issue', 'Title', domain=[('child_ids','<>', False)])
    title_product_attr_value_id = fields.Many2one(related='title.product_attribute_value_id',
                                                 relation='sale.advertising.issue',
                                                 string='Title', readonly=True)
    title_ids = fields.Many2many('sale.advertising.issue', 'sale_order_line_adv_issue_title_rel', 'order_line_id',
                                     'adv_issue_id', 'Titles')
    adv_issue_ids = fields.Many2many('sale.advertising.issue','sale_order_line_adv_issue_rel', 'order_line_id',
                                      'adv_issue_id',  'Advertising Issues')
    issue_product_ids = fields.One2many('sale.order.line.issues.products', 'order_line_id', 'Adv. Issues with Product Prices')
    dates = fields.One2many('sale.order.line.date', 'order_line_id', 'Advertising Dates')
    dateperiods = fields.One2many('sale.order.line.dateperiod', 'order_line_id', 'Advertising Date Periods')
    date_type = fields.Selection(related='ad_class.date_type', type='selection',
                   selection=[
                        ('validity', 'Validity Date Range'),
                        ('date', 'Date of Publication'),
                        ('newsletter', 'Newsletter'),
                        ('online', 'Online'),
                        ('issue_date', 'Issue Date'),
                   ], relation='product.category', string='Date Type', readonly=True)
    adv_issue = fields.Many2one('sale.advertising.issue','Advertising Issue')
#    medium = fields.Many2one(related='title.medium', relation='product.category',string='Medium', readonly=True )
    medium = fields.Many2one('product.category', string='Medium', domain=_domain_medium, readonly=False)
    ad_class = fields.Many2one('product.category', 'Advertising Class')
    product_template_id = fields.Many2one('product.template', string='Generic Product', domain=[('sale_ok', '=', True)],
                                 change_default=True, ondelete='restrict')
    page_reference = fields.Char('Reference of the Page', size=32)
    ad_number = fields.Char('Advertising Reference', size=32)
    url_to_material = fields.Char('Advertising Material', size=64)
    from_date = fields.Date('Start of Validity')
    to_date = fields.Date('End of Validity')
    partner_acc_mgr = fields.Many2one(related='order_id.partner_acc_mgr', store=True, string='Account Manager', readonly=True)
    order_partner_id = fields.Many2one(related='order_id.partner_id', relation='res.partner', string='Customer')
    discount_dummy = fields.Float(compute='_compute_amount', string='Agency Commission (%)',readonly=True )
    actual_unit_price = fields.Float('Actual Unit Price', required=True, default='0.0',
                                     digits=dp.get_precision('Actual Unit Price'), readonly=True, states={'draft': [('readonly', False)]})
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    computed_discount = fields.Monetary(compute='_compute_amount', string='Discount (%)', digits=dp.get_precision('Account'), store=True)
    subtotal_before_agency_disc = fields.Monetary(compute='_compute_amount', string='Subtotal before Commission', digits=dp.get_precision('Account'), store=True)
    advertising = fields.Boolean(related='order_id.advertising', string='Advertising', default=False, store=True)


    @api.onchange('title')
    def onchange_title(self):
        data, vals = {}, {}

        if self.title:
            ad_issue = self.title
            child_id = [x.id for x in ad_issue.child_ids]

            if len(child_id) == 1:
                vals['adv_issue'] = child_id[0]
                vals['adv_issue_ids'] = [(6,0,[])]
                vals['ad_class'] = False
                vals['product_id'] = False
                vals['actual_unit_price'] = 0.0
                ac = ad_issue.medium and ad_issue.medium.id or False
                vals['medium'] = ac
                data = {'ad_class': [('id', 'child_of', ac), ('type', '!=', 'view')]}
                ac_child = self.env['product.category'].search([('id', 'child_of', ac), ('type', '!=', 'view')])
                if len(ac_child) == 1:
                    vals['ad_class'] = ac_child[0]

            else:
                vals['adv_issue'] = False
                vals['ad_class'] = False
                vals['product_id'] = False
                vals['actual_unit_price'] = 0.0
                ac = ad_issue.medium and ad_issue.medium.id or False
                vals['medium'] = ac
                data = {'ad_class': [('id', 'child_of', ac), ('type', '!=', 'view')]}
                ac_child = self.env['product.category'].search([('id', 'child_of', ac), ('type', '!=', 'view')])
                if len(ac_child) == 1:
                    vals['ad_class'] = ac_child[0]

            # - deep
            data.update({'adv_issue': [('id','in', child_id)]})

        return {'value': vals, 'domain': data}


    @api.onchange('ad_class')
    def onchange_ad_class(self):
        vals, data, result = {}, {}, {}

        if self.ad_class:
            product_ids = self.env['product.template'].search([('categ_id', '=', self.ad_class.id)])
            if product_ids:
                data['product_template_id'] = [('categ_id', '=', self.ad_class.id)]
                if len(product_ids) == 1:
                    vals['product_template_id'] = product_ids[0]
                else:
                    vals['product_template_id'] = False

            date_type = self.ad_class.date_type
            if date_type:
                vals['date_type'] = date_type
            else: result = {'title':_('Warning'),
                                 'message':_('The Ad Class has no Date Type. You have to define one')}
        else:
            vals['product_template_id'] = False
            vals['date_type'] = False
        return {'value': vals, 'domain' : data, 'warning': result}


    @api.onchange('date_type')
    def onchange_date_type(self):
        vals = {}
        date_type = self.date_type

        if date_type:
            if date_type == 'date':
                if self.dateperiods:
                    vals['dateperiods'] = [(6,0,[])] #[(2,x[1]) for x in dateperiods]
                if self.adv_issue_ids:
                    vals['adv_issue_ids'] = [(6,0,[])]

            elif date_type == 'validity':
                if self.dates:
                    vals['dates'] = [(6,0,[])] #[(2, x[1]) for x in dates]
                if self.adv_issue_ids:
                    vals['adv_issue_ids'] = [(6,0,[])]

            elif date_type == 'issue_date':
                if self.dates:
                    vals['dates'] = [(6,0,[])] #[(2, x[1]) for x in dates]
                if self.dateperiods:
                    vals['dateperiods'] = [(6,0,[])] #[(2, x[1]) for x in dateperiods]
        return {'value': vals}



    @api.onchange('actual_unit_price', 'discount')
    def onchange_actualup(self):
        result = {}
        if not self.advertising:
            return {'value': result}

        qty = self.product_uom_qty
        actual_unit_price = self.actual_unit_price
        price_unit = self.price_unit
        discount = self.discount

        if actual_unit_price and actual_unit_price > 0.0:
            if price_unit and price_unit > 0.0:
                cdisc = (float(price_unit) - float(actual_unit_price)) / float(price_unit) * 100.0
                result['computed_discount'] = cdisc
                result['subtotal_before_agency_disc'] = round((float(actual_unit_price) * float(qty)), 2)
                result['price_subtotal'] = round((float(actual_unit_price) * float(qty) * (1.0 - float(discount)/100.0)), 2)
            else:
                result['computed_discount'] = 0.0
                result['subtotal_before_agency_disc'] = round((float(actual_unit_price) * float(qty)), 2)
                result['price_subtotal'] = round((float(actual_unit_price) * float(qty) * (1.0 - float(discount)/100.0)), 2)
        else:
            if price_unit and price_unit > 0.0:
                result['actual_unit_price'] = 0.0
            result['computed_discount'] = 100.0
            result['subtotal_before_agency_disc'] = round((float(actual_unit_price) * float(qty)), 2)
            result['price_subtotal'] = round((float(actual_unit_price) * float(qty) * (1.0 - float(discount)/100.0)), 2)
        return {'value': result}


    @api.onchange('subtotal_before_agency_disc')
    def onchange_price_subtotal(self):
        result = {}
        if not self.advertising:
            return {'value': result}

        subtotal_before_agency_disc = self.subtotal_before_agency_disc
        qty = self.product_uom_qty

        if subtotal_before_agency_disc and subtotal_before_agency_disc > 0.0:
                if qty > 0.0:
                    actual_unit_price = float(subtotal_before_agency_disc) / float(qty)
                    result['actual_unit_price'] = actual_unit_price
                    result['price_subtotal'] = round((float(subtotal_before_agency_disc) * (1.0 - float(self.discount) / 100.0)), 2)
        else:
            result['actual_unit_price'] = 0.0
            result['price_subtotal'] = 0.0
        return {'value': result}


    @api.onchange('price_unit')
    def onchange_price_unit(self):
        vals = {}
        if not self.advertising:
            return {'value': vals}

        if self.price_unit > 0.0:
            vals['actual_unit_price'] = self.price_unit
        return {'value': vals}


    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        res['account_analytic_id'] = self.adv_issue.analytic_account_id.id
        return res

    @api.onchange('adv_issue', 'adv_issue_ids','dates','issue_product_ids')
    def onchange_getQty(self):
#        import pdb;
#        pdb.set_trace()
        qty = 0.00
        if self.adv_issue and self.adv_issue_ids:
            if len(self.adv_issue_ids) > 1:
                qty = len(self.adv_issue_ids)
                self.adv_issue = False
            else:
                self.adv_issue = self.adv_issue_ids.id
                self.adv_issue_ids = [(6,0,[])]
                qty = 1

        elif self.adv_issue_ids:
            if len(self.adv_issue_ids) > 1:
                qty = len(self.adv_issue_ids)
            else:
                self.adv_issue = self.adv_issue_ids.id
                self.adv_issue_ids = [(6,0,[])]
                qty = 1

        elif self.adv_issue:
            qty = 1

        elif self.dates:
            if len(self.dates) >= 1:
                qty = len(self.dates)

        elif self.issue_product_ids:
            if len(self.issue_product_ids) > 1:
                qty = len(self.issue_product_ids)

        self.product_uom_qty = qty


    @api.onchange('product_uom_qty')
    def qty_change(self):
        res = self.product_id_change()

        mqty = False
        if self.date_type == 'issue_date' and self.adv_issue_ids:
            if len(self.adv_issue_ids) >= 1:
                mqty = len(self.adv_issue_ids)
            else:
                mqty = 0
        elif self.date_type == 'issue_date' and self.issue_product_ids:
            if len(self.issue_product_ids) > 1:
                mqty = len(self.adv_issue_ids)
            else:
                mqty = 0

        if self.date_type == 'date' and self.dates:
            if len(self.dates) >= 1:
                mqty = len(self.dates)
            else:
                mqty = 0
        if mqty:
            qty = mqty
            self.product_uom_qty = qty

        partner = self.order_id.partner_id
        if partner.is_ad_agency and not self.order_id.nett_nett:
            discount = partner.agency_discount
        else:
            discount = 0.0
        self.update({'discount': discount, 'discount_dummy': discount})

        # TODO: FIXME
        # if self.price_unit:
        #     pu = self.price_unit
        #     if pu != self.price_unit:
        #         actual_unit_price = pu
        # else:
        #     pu = 0.0
        res2 = self.onchange_actualup()
        self.update(res2['value'])
        return res

    @api.onchange('product_template_id',  'title_ids')
    def issues_products_price(self):
#        import pdb;
#        pdb.set_trace()
        if self.product_template_id and self.adv_issue_ids and self.title_ids:
            self.product_uom = self.product_template_id.uom_id
            if len(self.title_ids) == 1:
                if self.title_product_attr_value_id:
                    product_id = self.env['product.product'].search(
                        [('product_tmpl_id', '=', self.product_template_id.id), ('attribute_value_ids', '=', self.title_product_attr_value_id.id)])
                else:
                    product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.product_template_id.id)])
                if len(product_id) != 1:
                    raise UserError(_('There are product variants without attribute set.'))

                self.title = self.title_ids.id
                self.product_id = product_id.id

            else:
                titles = self.title_ids.ids
                issue_ids = self.adv_issue_ids.ids
                adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', issue_ids)])
                issue_parent_ids = [x.parent_id.id for x in adv_issues]
                values = []
                product_id = False
                price = 0
                issues_count = 0
                for title in titles:
                    if not (title in issue_parent_ids):
                        raise UserError(_('Not for every selected Title an Issue is selected.'))
                for adv_issue in adv_issues:
                    if adv_issue.parent_id.id in titles:
                        value = {}
                        pav = adv_issue.parent_id.product_attribute_value_id.id
                        product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.product_template_id.id),('attribute_value_ids','=', pav)])
                        if product_id:
                            if self.order_id.pricelist_id and self.order_id.partner_id:
                                value['product_id'] = product_id.id
                                value['adv_issue_id'] = adv_issue.id
                                value['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                                    self._get_display_price(product_id), product_id.taxes_id, self.tax_id, self.company_id)
                                price += value['price_unit']
                            values.append(value)
                            issues_count += 1

                avg_price = price / issues_count
                if product_id:
                    self.update({
                        'adv_issue_ids': [(6,0,[])],
                        'issue_product_ids': values,
                        'price_unit': avg_price,
                        'product_id': product_id.id,
                        'product_uom_qty': issues_count,
                    })

        elif self.title_ids:
            if len(self.title_ids) == 1:
                self.update({ 'title' : self.title_ids.id })
            elif len(self.title_ids) > 1:
                self.update({'title': False})

        return



class OrderLineAdvIssuesProducts(models.Model):

    _name = "sale.order.line.issues.products"
    _description= "Advertising Order Line Advertising Issues"
    _order = "order_line_id,sequence,id"

    sequence = fields.Integer('Sequence', help="Gives the sequence of this line .", default=10)
    order_line_id = fields.Many2one('sale.order.line', 'Line', ondelete='cascade', index=True, required=True)
    adv_issue_id = fields.Many2one('sale.advertising.issue', 'Issue', ondelete='cascade', index=True, required=True)
    product_attribute_value_id = fields.Many2one(related='adv_issue_id.parent_id.product_attribute_value_id', relation='sale.advertising.issue',
                                      string='Title', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', ondelete='cascade', index=True, )
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'), default=0.0)


class OrderLineDate(models.Model):

    _name = "sale.order.line.date"
    _description= "Advertising Order Line Dates"
    _order = "order_line_id,sequence,id"

    sequence = fields.Integer('Sequence', help="Gives the sequence of this line .", default=10)
    order_line_id = fields.Many2one('sale.order.line', 'Line', ondelete='cascade', index=True, required=True)
    issue_date = fields.Date('Date of Issue')
    name = fields.Char('Name', size=64)
    page_reference = fields.Char('Reference of the Page', size=32)
    ad_number = fields.Char('Advertising Reference', size=32)


class OrderLineDateperiod(models.Model):

    _name = "sale.order.line.dateperiod"
    _description= "Advertising Order Line Date Periods"
    _order = "order_line_id,sequence,id"

    sequence = fields.Integer('Sequence', help="Gives the sequence of this line .", default=10)
    order_line_id = fields.Many2one('sale.order.line', 'Line', ondelete='cascade', index=True, required=True)
    from_date = fields.Date('Start of Validity')
    to_date = fields.Date('End of Validity')
    name = fields.Char('Name', size=64)
    page_reference = fields.Char('Reference of the Page', size=32)
    ad_number = fields.Char('Advertising Reference', size=32)



class AdvertisingProof(models.Model):
    _name = "sale.advertising.proof"
    _description="Sale Advertising Proof"

    name = fields.Char('Name', size=32, required=True)
    address_id = fields.Many2one('res.partner','Delivery Address', required=True)
    number = fields.Integer('Number of Copies', required=True, default=1)
    target_id = fields.Many2one('sale.order','Target', required=True)




class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        if self._context.get('default_model') == 'sale.order' and self._context.get('default_res_id') and self._context.get('mark_so_as_sent'):
            order = self.env['sale.order'].browse([self._context['default_res_id']])
            if order.state == 'approved2':
                order.state = 'sent'
        return super(MailComposeMessage, self.with_context(mail_post_autofollow=True)).send_mail(auto_commit=auto_commit)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

