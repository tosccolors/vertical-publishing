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

import json
from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta


class SaleOrder(models.Model):
    _inherit = ["sale.order"]

    @api.depends('order_line.price_total', 'order_line.computed_discount', 'partner_id')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        super(SaleOrder, self.filtered(lambda record: record.advertising != True))._amount_all()
        for order in self.filtered('advertising'):
            amount_untaxed = amount_tax = max_cdiscount = 0.0
            cdiscount = []
            ver_tr_exc = False
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                cdiscount.append(line.computed_discount)
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    if not line.multi_line:
                        price = line.actual_unit_price * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                        product=line.product_id, partner=order.partner_id)
                        amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                    else:
                        price = line.subtotal_before_agency_disc * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id, quantity=1,
                                                        product=line.product_id, partner=order.partner_id)
                        amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
            if cdiscount:
                max_cdiscount = max(cdiscount)
            if order.company_id.verify_order_setting != -1.00 and order.company_id.verify_order_setting < amount_untaxed \
                                                                  or order.company_id.verify_discount_setting < max_cdiscount:
                ver_tr_exc = True

            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
                'ver_tr_exc': ver_tr_exc,
                'max_discount': max_cdiscount,
            })

    @api.depends('state', 'order_line.invoice_status')
    def _get_invoiced(self):
        """
        Compute the invoice status of a SO. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also hte default value if the conditions of no other status is met.
        - to invoice: if any SO line is 'to invoice', the whole SO is 'to invoice'
        - invoiced: if all SO lines are invoiced, the SO is invoiced.
        - not invoiced: if no SO lines are invoiced, the SO is not invoiced (This override)
        - upselling: if all SO lines are invoiced or upselling, the status is upselling.

        The invoice_ids are obtained thanks to the invoice lines of the SO lines, and we also search
        for possible refunds created directly from existing invoices. This is necessary since such a
        refund is not directly linked to the SO.
        """
        super(SaleOrder, self)._get_invoiced()
        for order in self.filtered('advertising'):
            line_invoice_status = [line.invoice_status for line in order.order_line]

            if all(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                invoice_status = 'not invoiced'
                order['invoice_status'] = invoice_status

    @api.depends('agency_is_publish')
    @api.multi
    def _compute_pub_cust_domain(self):
        """
        Compute the domain for the published_customer domain.
        """
        for rec in self:
            if rec.agency_is_publish:
                rec.pub_cust_domain = json.dumps(
                    [('is_ad_agency', '=', True), ('parent_id', '=', False), ('customer', '=', True)]
                )
            else:
                rec.pub_cust_domain = json.dumps(
                    [('is_ad_agency', '!=', True),('parent_id', '=', False), ('customer', '=', True)]
                )

    state = fields.Selection(selection=[
        ('draft', 'Draft Quotation'),
        ('submitted', 'Submitted for Approval'),
        ('approved1', 'Approved by Sales Mgr'),
        ('approved2', 'Approved by Traffic'),
        ('sent', 'Quotation Sent'),
        ('cancel', 'Cancelled'),
        ('sale', 'Sales Order'),
        ('done', 'Done'),
        ])
    invoice_status = fields.Selection(selection_add=[
        ('not invoiced', 'Nothing Invoiced Yet')
        ])
    published_customer = fields.Many2one('res.partner', 'Advertiser', domain=[('customer','=',True)])
    advertising_agency = fields.Many2one('res.partner', 'Advertising Agency', domain=[('customer','=',True)])
    nett_nett = fields.Boolean('Netto Netto Deal', default=False)
    pub_cust_domain = fields.Char(compute=_compute_pub_cust_domain, readonly=True, store=False, )
    agency_is_publish = fields.Boolean('Agency is Publishing Customer', default=False)
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
    max_discount = fields.Integer(compute='_amount_all', track_visibility='always', store=True, string="Maximum Discount")
    display_discount_to_customer = fields.Boolean("Display Discount", default=False)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env[
                                     'res.company']._company_default_get(
                                     'sale.order'), index=True)

    @api.model
    def default_get(self, fields):
        result = super(SaleOrder, self).default_get(fields)
        if self._context.get('active_model') and self._context.get('active_ids') and self._context.get('active_model') == 'crm.lead':
            lead = self.env[self._context.get('active_model')].browse(self._context.get('active_ids'))
            result.update({'campaign_id': lead.campaign_id.id, 'source_id': lead.source_id.id, 'medium_id': lead.medium_id.id, 'tag_ids': [[6, False, lead.tag_ids.ids]]})
        return result



    # overridden:
    @api.multi
    @api.onchange('partner_id', 'published_customer', 'advertising_agency', 'agency_is_publish')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment term
        - Invoice address
        - Delivery address
        """
        if not self.advertising:
            result = super(SaleOrder, self).onchange_partner_id()
            return result
        # Advertiser:
        if self.published_customer:
            self.partner_id = self.published_customer.id
        else:
            self.partner_id = self.advertising_agency = False
        if self.advertising_agency:
            self.partner_id = self.advertising_agency
        if not self.partner_id:
            self.update({
                'customer_contact': False
            })
        super(SaleOrder, self).onchange_partner_id()
        if self.partner_id.type == 'contact':
            contact = self.env['res.partner'].search([('is_company','=', False),('type','=', 'contact'),('parent_id','=', self.partner_id.id)])
            if len(contact) >=1:
                contact_id = contact[0]
            else:
                contact_id = False
        else:
            addr = self.partner_id.address_get(['delivery', 'invoice'])
            contact_id = addr['contact']
        if not self.partner_id.is_company and not self.partner_id.parent_id:
            contact_id = self.partner_id
        # Not sure about this!
        self.user_id = self._uid
        if not self.customer_contact:
            self.customer_contact = contact_id
        if self.order_line:
            warning = {'title':_('Warning'),
                                 'message':_('Changing the Customer can have a change in Agency Discount as a result.'
                                             'This change will only show after saving the order!'
                                             'Before saving the order the order lines and the total amounts may therefor'
                                             'show wrong values.')}
            return {'warning': warning}


    @api.multi
    def action_submit(self):
        orders = self.filtered(lambda s: s.state in ['draft'])
        for o in orders:
            if not o.order_line:
                raise UserError(_('You cannot submit a quotation/sales order which has no line.'))
        return self.write({'state': 'submitted'})

    # --added deep
    @api.multi
    def action_approve1(self):
        orders = self.filtered(lambda s: s.state in ['submitted'])
        orders.write({'state':'approved1'})
        return True

    @api.multi
    def action_approve2(self):
        orders = self.filtered(lambda s: s.state in ['approved1', 'submitted'])
        orders.write({'state': 'approved2',
                      'traffic_appr_date': fields.Date.context_today(self)})
        return True

    # --added deep
    @api.multi
    def action_refuse(self):
        orders = self.filtered(lambda s: s.state in ['submitted', 'sale', 'sent', 'approved1', 'approved2'])
        orders.write({'state':'draft'})
        return True

    # overridden: -- added deep
    @api.multi
    def print_quotation(self):
        orders = self.filtered(lambda s: s.advertising and s.state in ['draft','approved1', 'submitted', 'approved2'])
        for order in orders:
            olines = []
            for line in order.order_line:
                if line.multi_line:
                    olines.append(line.id)
            if not olines == []:
                self.env['sale.order.line.create.multi.lines'].create_multi_from_order_lines(orderlines=olines)
        self._cr.commit()
        orders.write({'state': 'sent'})
        return super(SaleOrder, self).print_quotation()

    @api.multi
    def action_quotation_send(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        if not self.advertising:
            return super(SaleOrder, self).action_quotation_send()

        elif self.state in ['draft', 'approved1', 'submitted', 'approved2']:
            olines = []
            for line in self.order_line:
                if line.multi_line:
                    olines.append(line.id)
            if not olines == []:
                self.env['sale.order.line.create.multi.lines'].create_multi_from_order_lines(orderlines=olines,
                                                                                             orders=self)
        # self.write({'state': 'sent'}) #Task: SMA-1 Action button for state [sent] in sale.order

        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('sale_advertising_order', 'email_template_edi_sale_adver')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "sale.mail_template_data_notification_email_sale_order"
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }


    @api.multi
    def action_cancel(self):
        for order in self.filtered(lambda s: s.state == 'sale' and s.advertising):
            for line in order.order_line:
                line.page_qty_check_unlink()
        return super(SaleOrder, self).action_cancel()

    @api.multi
    def action_confirm(self):
        for order in self.filtered('advertising'):
            olines = []
            for line in order.order_line:
                if line.multi_line:
                    olines.append(line.id)
                else:
                    if line.deadline_check():
                        line.page_qty_check_create()
            if not olines == []:
                list = self.env['sale.order.line.create.multi.lines'].create_multi_from_order_lines(
                    orderlines=olines, orders=order)
                newlines = self.env['sale.order.line'].browse(list)
                for newline in newlines:
                    if newline.deadline_check():
                        newline.page_qty_check_create()
        #@by Sushma: context no_checks always by pass order comparision with verify_discount_setting & verify_order_setting
        # return super(SaleOrder, self.with_context(no_checks=True)).action_confirm()
        return super(SaleOrder, self).action_confirm()

    @api.model
    def create(self, vals):
        if vals.get('partner_id', False):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            if partner.sale_warn == 'block':
                raise UserError(_(partner.sale_warn_msg))

        result = super(SaleOrder, self).create(vals)
        return result

    @api.multi
    def write(self, vals):
        result = super(SaleOrder, self).write(vals)
        orders = self.filtered(lambda s: s.state in ['sale'] and s.advertising and not s.env.context.get('no_checks'))
        for order in orders:
            user = self.env['res.users'].browse(self.env.uid)
            if not user.has_group('sale_advertising_order.group_no_discount_check') \
               and self.ver_tr_exc:
                raise UserError(_(
                    'You cannot save a Sale Order with a line more than %s%s discount or order total amount is more than %s.'
                    '\nYou\'ll have to cancel the order and '
                    'resubmit it or ask Sales Support for help.') % (
                                order.company_id.verify_discount_setting, '%', order.company_id.verify_order_setting))
            olines = []
            for line in order.order_line:
                if line.multi_line:
                    olines.append(line.id)
                    continue
            if not olines == []:
                list = self.env['sale.order.line.create.multi.lines'].create_multi_from_order_lines(
                    orderlines=olines, orders=order)
                newlines = self.env['sale.order.line'].browse(list)
                for newline in newlines:
                    if newline.deadline_check():
                        newline.page_qty_check_create()

        return result

    @api.multi
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.advertising:
            invoice_vals['published_customer'] = self.published_customer.id,
        return invoice_vals



class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends('product_uom_qty', 'order_id.partner_id', 'order_id.nett_nett', 'nett_nett', 'subtotal_before_agency_disc',
                 'price_unit', 'tax_id')
    @api.multi
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        super(SaleOrderLine, self.filtered(lambda record: record.advertising != True))._compute_amount()
        for line in self.filtered('advertising'):
            nn = True if line.order_id.nett_nett or line.nett_nett else False
            comp_discount = line.computed_discount or 0.0
            price_unit = line.price_unit or 0.0
            unit_price = line.actual_unit_price or 0.0
            qty = line.product_uom_qty or 0.0
            csa = line.color_surcharge_amount or 0.0
            subtotal_bad = line.subtotal_before_agency_disc or 0.0
            if line.order_id.partner_id.is_ad_agency and not nn:
                discount = line.order_id.partner_id.agency_discount
            else:
                discount = 0.0

            if not line.multi_line:
                if price_unit == 0.0:
                    unit_price = csa
                    comp_discount = 0.0
                elif price_unit > 0.0 and qty > 0.0 :
                    comp_discount = round((1.0 - float(subtotal_bad) / (float(price_unit) * float(qty) + float(csa) *
                                                                        float(qty))) * 100.0, 5)
                    unit_price = round((float(price_unit) + float(csa)) * (1 - float(comp_discount) / 100), 5)
                    decimals=self.env['decimal.precision'].search([('name','=','Product Price')]).digits or 4
                    unit_price = round((float(price_unit) + float(csa)) * (1 - float(comp_discount) / 100), decimals)
                elif qty == 0.0:
                    unit_price = 0.0
                    comp_discount = 0.0
                price = round(unit_price * (1 - (discount or 0.0) / 100.0), 5)
                taxes = line.tax_id.compute_all(
                    price,
                    line.order_id.currency_id,
                    line.product_uom_qty,
                    product=line.product_id,
                    partner=line.order_id.partner_id
                )
                line.update({
                    'actual_unit_price': unit_price,
                    'price_tax': taxes['total_included'] - taxes['total_excluded'],
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                    'computed_discount': comp_discount,
                    'discount': discount,
                })
            else:
                clp = line.comb_list_price or 0.0
                if clp > 0.0:
                    comp_discount = round((1.0 - float(subtotal_bad) / (float(clp) + float(csa))) * 100.0, 2)
                    unit_price = 0.0
                    price_unit = 0.0
                else:
                    comp_discount = 0.0
                    unit_price = 0.0
                    price_unit = 0.0

#                price = round(float(subtotal_bad) * (1.0 - float(discount or 0) / 100.0), 2)
                price = round(subtotal_bad * (1 - (discount or 0.0) / 100.0), 4)
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, quantity=1,
                                                product=line.product_template_id, partner=line.order_id.partner_id)
                line.update({
                    'price_tax': taxes['total_included'] - taxes['total_excluded'],
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                    'computed_discount': comp_discount,
                    'actual_unit_price': unit_price,
                    'price_unit': price_unit,
                    'discount': discount,
                })
        return True


    @api.depends('issue_product_ids.price')
    @api.multi
    def _multi_price(self):
        """
        Compute the combined price in the multi_line.
        """
        for order_line in self.filtered('advertising'):
            if order_line.issue_product_ids:
                price_tot = 0.0
                count = 0
                for ipi in order_line.issue_product_ids:
                    price_tot += ipi.price
                    count += 1
                order_line.update({
                    'comb_list_price': price_tot,
                    'multi_line_number': count,
                })

    @api.depends('adv_issue', 'ad_class')
    @api.multi
    def _compute_deadline(self):
        """
        Compute the deadline for this placement.
        """
        user = self.env['res.users'].browse(self.env.uid)
        for line in self.filtered('advertising'):
            line.deadline_passed = False
            line.deadline = False
            line.deadline_offset = False
            if line.ad_class:
                if not user.has_group('sale_advertising_order.group_no_deadline_check'):
                    dt_offset = timedelta(hours=line.ad_class.deadline_offset or 0)
                    line.deadline_offset = fields.Datetime.to_string(datetime.now() + dt_offset)
                    if line.adv_issue and line.adv_issue.deadline and line.adv_issue.issue_date:
                        dt_deadline = fields.Datetime.from_string(line.adv_issue.deadline)
                        line.deadline = fields.Datetime.to_string(dt_deadline - dt_offset)
                        line.deadline_passed = datetime.now() > (dt_deadline - dt_offset) and \
                                               datetime.now() < fields.Datetime.from_string(line.adv_issue.issue_date)


    @api.depends('ad_class')
    @api.multi
    def _compute_tags_domain(self):
        """
        Compute the domain for the Pageclass domain.
        """
        for rec in self:
            rec.page_class_domain = json.dumps(
                [('id', 'in', rec.ad_class.tag_ids.ids)]
            )

    @api.depends('title', 'product_template_id')
    @api.multi
    def _compute_price_edit(self):
        """
        Compute if price_unit should be editable.
        """
        for line in self.filtered('advertising'):
            if line.product_template_id.price_edit or line.title.price_edit:
                line.price_edit = True

    mig_remark = fields.Text('Migration Remark')
    layout_remark = fields.Text('Material Remark')
    title = fields.Many2one('sale.advertising.issue', 'Title', domain=[('child_ids','<>', False)])
    page_class_domain = fields.Char(compute='_compute_tags_domain', readonly=True, store=False,)
    title_ids = fields.Many2many('sale.advertising.issue', 'sale_order_line_adv_issue_title_rel', 'order_line_id', 'adv_issue_id', 'Titles')
    adv_issue_ids = fields.Many2many('sale.advertising.issue','sale_order_line_adv_issue_rel', 'order_line_id', 'adv_issue_id',  'Advertising Issues')
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
    issue_date = fields.Date(related='adv_issue.issue_date', string='Issue Date', store=True)
    medium = fields.Many2one('product.category', string='Medium')
    ad_class = fields.Many2one('product.category', 'Advertising Class')
    deadline_passed = fields.Boolean(compute='_compute_deadline', string='Deadline Passed')
    deadline = fields.Datetime(compute='_compute_deadline', string='Deadline', store=False)
    deadline_offset = fields.Datetime(compute='_compute_deadline')
    product_template_id = fields.Many2one('product.template', string='Product', domain=[('sale_ok', '=', True)],
                                 change_default=True, ondelete='restrict')
    page_reference = fields.Char('Page Preference', size=32)
    ad_number = fields.Char('External Reference', size=32)
    url_to_material = fields.Char('URL Material')
    from_date = fields.Date('Start of Validity')
    to_date = fields.Date('End of Validity')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('submitted', 'Submitted for Approval'),
        ('approved1', 'Approved by Sales Mgr'),
        ('approved2', 'Approved by Traffic'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sale Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], related='order_id.state', string='Order Status', readonly=True, copy=False, store=True, default='draft')
    multi_line_number = fields.Integer(compute='_multi_price', string='Number of Lines', store=True)
    partner_acc_mgr = fields.Many2one(related='order_id.partner_acc_mgr', store=True, string='Account Manager', readonly=True)
    order_partner_id = fields.Many2one(related='order_id.partner_id', relation='res.partner', string='Customer', store=True)
    order_advertiser_id = fields.Many2one(related='order_id.published_customer', relation='res.partner',
                                          string='Advertising Customer', store=True)
    order_agency_id = fields.Many2one(related='order_id.advertising_agency', relation='res.partner',
                                          string='Advertising Agency', store=True)
    order_pricelist_id = fields.Many2one(related='order_id.pricelist_id', relation='product.pricelist', string='Pricelist')
    company_id = fields.Many2one(related='order_id.company_id',
                                 string='Company', store=True, readonly=True, index=True)
    discount_dummy = fields.Float(related='discount', string='Agency Commission (%)', readonly=True )
    price_unit_dummy = fields.Float(related='price_unit', string='Unit Price', readonly=True)
    actual_unit_price = fields.Float(compute='_compute_amount', string='Actual Unit Price', digits=dp.get_precision('Product Price'),
                                        default=0.0, readonly=True)
    comb_list_price = fields.Monetary(compute='_multi_price', string='Combined_List Price', default=0.0, store=True,
                                digits=dp.get_precision('Account'))
    computed_discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)
    subtotal_before_agency_disc = fields.Monetary(string='Subtotal before Commission', digits=dp.get_precision('Account'))
    advertising = fields.Boolean(related='order_id.advertising', string='Advertising', store=True)
    multi_line = fields.Boolean(string='Multi Line')
    color_surcharge = fields.Boolean(string='Color Surcharge')
    price_edit = fields.Boolean(compute='_compute_price_edit', string='Price Editable')
    color_surcharge_amount = fields.Monetary(string='Color Surcharge', digits=dp.get_precision('Product Price'))
    discount_reason_id = fields.Many2one('discount.reason', 'Discount Reason')
    nett_nett = fields.Boolean(string='Netto Netto Line')
    proof_number_adv_customer = fields.Boolean('Proof Number Advertising Customer', default=False)
    proof_number_payer = fields.Boolean('Proof Number Payer', default=False)
    booklet_surface_area = fields.Float(related='product_template_id.booklet_surface_area', readonly=True, string='Booklet Surface Area',digits=dp.get_precision('Product Unit of Measure'))

    @api.onchange('medium')
    def onchange_medium(self):
        vals, data, result = {}, {}, {}
        if not self.advertising:
            return {'value': vals }
        if self.medium:
            child_id = [x.id for x in self.medium.child_id]
            if len(child_id) == 1:
                vals['ad_class'] = child_id[0]
            else:
                vals['ad_class'] = False
                data = {'ad_class': [('id', 'child_of', self.medium.id), ('type', '!=', 'view')]}
            titles = self.env['sale.advertising.issue'].search([('parent_id','=', False),('medium', '=', self.medium.id)]).ids
            if titles and len(titles) == 1:
                vals['title'] = titles[0]
                vals['title_ids'] = [(6, 0, [])]
            else:
                vals['title'] = False
                vals['title_ids'] = [(6, 0, [])]
        else:
            vals['ad_class'] = False
            vals['title'] = False
            vals['title_ids'] = [(6, 0, [])]
            data = {'ad_class': []}
        return {'value': vals, 'domain': data }

    @api.onchange('ad_class')
    def onchange_ad_class(self):
        vals, data, result = {}, {}, {}
        if not self.advertising:
            return {'value': vals}
        titles = self.title_ids if self.title_ids else self.title or False
        domain = []
        if titles:
            product_ids = self.env['product.product']
            for title in titles:
                if title.product_attribute_value_id:
                    ids = product_ids.search([('attribute_value_ids', '=', [title.product_attribute_value_id.id])])
                    product_ids += ids
            product_tmpl_ids = product_ids.mapped('product_tmpl_id').ids
            domain = [('id', 'in', product_tmpl_ids)]
        if self.ad_class:
            product_ids = self.env['product.template'].search(domain+[('categ_id', '=', self.ad_class.id)])
            if product_ids and len(product_ids) == 1:
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

    @api.onchange('title')
    def title_oc(self):
        data, vals = {}, {}
        if not self.advertising:
            return {'value': vals}
        if self.title:
            adissue_ids = self.title.child_ids.ids
            if len(adissue_ids) == 1:
                vals['adv_issue'] = adissue_ids[0]
                vals['adv_issue_ids'] = [(6, 0, [])]
                vals['product_id'] = False
            else:
                vals['adv_issue'] = False
                vals['product_id'] = False
        else:
            vals['adv_issue'] = False
            vals['product_id'] = False
            vals['adv_issue_ids'] = [(6, 0, [])]
        return {'value': vals, 'domain': data}

    @api.onchange('title_ids')
    def title_ids_oc(self):
        vals = {}
        if not self.advertising:
            return {'value': vals}
        if self.title_ids and self.adv_issue_ids:
            titles = self.title_ids.ids
            issue_ids = self.adv_issue_ids.ids
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', issue_ids)])
            issue_parent_ids = [x.parent_id.id for x in adv_issues]
            for title in titles:
                if not (title in issue_parent_ids):
                    raise UserError(_('Not for every selected Title an Issue is selected.'))
            if len(self.title_ids) == 1:
                self.title = self.title_ids[0]
                self.title_ids = [(6, 0, [])]

        elif self.title_ids and self.issue_product_ids:
            titles = self.title_ids.ids
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', [x.adv_issue_id.id for x in self.issue_product_ids])])
            issue_parent_ids = [x.parent_id.id for x in adv_issues]
            back = False
            for title in titles:
                if not (title in issue_parent_ids):
                    back = True
                    break
            if back:
                self.adv_issue_ids = [(6, 0, adv_issues.ids)]
                self.issue_product_ids = [(6, 0, [])]
            if len(self.title_ids) == 1:
                self.title = self.title_ids[0]
                self.title_ids = [(6, 0, [])]
            self.titles_issues_products_price()

        elif self.title_ids:
            self.product_template_id = False
            self.product_id = False
        else:
            self.adv_issue = False
            self.adv_issue_ids = [(6, 0, [])]
            self.issue_product_ids = [(6, 0, [])]
            self.product_id = False
            self.product_template_id = False
            self.product_uom = False


    @api.onchange('product_template_id')
    def titles_issues_products_price(self):
        vals = {}
        if not self.advertising:
            return {'value': vals}
        volume_discount = self.product_template_id.volume_discount
        if self.product_template_id and self.adv_issue_ids and len(self.adv_issue_ids) > 1:
            self.product_uom = self.product_template_id.uom_id
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', self.adv_issue_ids.ids)])
            values = []
            product_id = False
            price = 0
            issues_count = len(adv_issues)
            for adv_issue in adv_issues:
                if adv_issue.parent_id.id in self.title_ids.ids or adv_issue.parent_id.id == self.title.id:
                    value = {}
                    if adv_issue.product_attribute_value_id:
                        pav = adv_issue.product_attribute_value_id.id
                    else:
                        pav = adv_issue.parent_id.product_attribute_value_id.id
                    product_id = self.env['product.product'].search(
                        [('product_tmpl_id', '=', self.product_template_id.id), ('attribute_value_ids', '=', pav)])
                    if product_id:
                        product = product_id.with_context(
                            lang=self.order_id.partner_id.lang,
                            partner=self.order_id.partner_id.id,
                            quantity=self.product_uom_qty or 0 if not volume_discount else issues_count,
                            date=self.order_id.date_order,
                            pricelist=self.order_id.pricelist_id.id,
                            uom=self.product_uom.id
                        )
                        if self.order_id.pricelist_id and self.order_id.partner_id:
                            value['product_id'] = product_id.id
                            value['adv_issue_id'] = adv_issue.id
                            value['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                                self._get_display_price(product), product.taxes_id, self.tax_id,
                                self.company_id)

                            price += value['price_unit'] * self.product_uom_qty
                            values.append(value)
            if product_id:
                self.update({
                    'adv_issue_ids': [(6, 0, [])],
                    'issue_product_ids': values,
                    'product_id': product_id.id,
                    'multi_line_number': issues_count,
                    'multi_line': True,
                })
            self.comb_list_price = price
            self.subtotal_before_agency_disc = price
        elif self.product_template_id and self.issue_product_ids and len(self.issue_product_ids) > 1:
            self.product_uom = self.product_template_id.uom_id
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', [x.adv_issue_id.id for x in self.issue_product_ids])])
            values = []
            product_id = False
            price = 0
            issues_count = len(adv_issues)
            for adv_issue in adv_issues:
                if adv_issue.parent_id.id in self.title_ids.ids or adv_issue.parent_id.id == self.title.id:
                    value = {}
                    if adv_issue.product_attribute_value_id:
                        pav = adv_issue.product_attribute_value_id.id
                    else:
                        pav = adv_issue.parent_id.product_attribute_value_id.id
                    product_id = self.env['product.product'].search(
                        [('product_tmpl_id', '=', self.product_template_id.id), ('attribute_value_ids', '=', pav)])
                    if product_id:
                        product = product_id.with_context(
                            lang=self.order_id.partner_id.lang,
                            partner=self.order_id.partner_id.id,
                            quantity=self.product_uom_qty or 0 if not volume_discount else issues_count,
                            date=self.order_id.date_order,
                            pricelist=self.order_id.pricelist_id.id,
                            uom=self.product_uom.id
                        )
                        if self.order_id.pricelist_id and self.order_id.partner_id:
                            value['product_id'] = product_id.id
                            value['adv_issue_id'] = adv_issue.id
                            value['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                                self._get_display_price(product), product.taxes_id, self.tax_id,
                                self.company_id)

                            price += value['price_unit'] * self.product_uom_qty
                            values.append(value)
            if product_id:
                self.update({
                    'issue_product_ids': values,
                    'product_id': product_id.id,
                    'multi_line_number': issues_count,
                    'multi_line': True,
                })
            self.comb_list_price = price
            self.subtotal_before_agency_disc = price
        elif self.product_template_id and (self.adv_issue or len(self.adv_issue_ids) == 1):
                if self.adv_issue_ids and len(self.adv_issue_ids) == 1:
                    self.adv_issue = self.adv_issue_ids.id
                if self.adv_issue.parent_id.id == self.title.id:
                    if self.adv_issue.product_attribute_value_id:
                        pav = self.adv_issue.product_attribute_value_id.id
                    else:
                        pav = self.adv_issue.parent_id.product_attribute_value_id.id
                    product_id = self.env['product.product'].search(
                        [('product_tmpl_id', '=', self.product_template_id.id), ('attribute_value_ids', '=', pav)])
                    if product_id:
                        self.update({
                            'adv_issue_ids': [(6, 0, [])],
                            'issue_product_ids': [(6, 0, [])],
                            'product_id': product_id.id,
                            'multi_line_number': 1,
                            'multi_line': False,
                        })

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        result = super(SaleOrderLine, self).product_id_change()
        if not self.advertising:
            return result
        self.color_surcharge = False
        self.product_uom_qty = 1
        self.computed_discount = 0.0
        if not self.multi_line:
            self.subtotal_before_agency_disc = self.price_unit
        else:
            self.price_unit = 0.0
            self.subtotal_before_agency_disc = self.comb_list_price
        pt = self.product_template_id
        name = pt.name or ''
        if pt.description_sale:
            name += '\n' + pt.description_sale
        self.name = name
        return result

    @api.onchange('date_type')
    def onchange_date_type(self):
        vals = {}
        if not self.advertising:
            return {'value': vals}
        if self.date_type:
            if self.date_type == 'date':
                if self.dateperiods:
                    vals['dateperiods'] = [(6,0,[])]
                if self.adv_issue_ids:
                    vals['adv_issue_ids'] = [(6,0,[])]
            elif self.date_type == 'validity':
                if self.dates:
                    vals['dates'] = [(6,0,[])]
                if self.adv_issue_ids:
                    vals['adv_issue_ids'] = [(6,0,[])]
            elif self.date_type == 'issue_date':
                if self.dates:
                    vals['dates'] = [(6,0,[])]
                if self.dateperiods:
                    vals['dateperiods'] = [(6,0,[])]
        return {'value': vals}



    @api.onchange('price_unit')
    def onchange_price_unit(self):
        result = {}
        if not self.advertising:
            return {'value': result}
        if self.price_unit > 0 and self.product_uom_qty > 0:
            result['subtotal_before_agency_disc'] = self.price_unit * self.product_uom_qty
        return {'value': result}

    @api.onchange('computed_discount')
    def onchange_actualcd(self):
        result = {}
        if not self.advertising:
            return {'value': result}
        csa = self.color_surcharge_amount or 0.0
        comp_discount = self.computed_discount
        if comp_discount < 0.0:
            comp_discount = self.computed_discount = 0.000
        if comp_discount > 100.0:
            comp_discount = self.computed_discount = 100.0
        price = self.price_unit or 0.0
        fraction_param = int(self.env['ir.config_parameter'].get_param('sale_advertising_order.fraction'))

        if self.multi_line:
            clp = self.comb_list_price or 0.0
            fraction = (float(clp) + float(csa)) / fraction_param
            subtotal_bad = round((float(clp) + float(csa)) * (1.0 - float(comp_discount) / 100.0), 2)
        else:
            gross_price = (float(price) + float(csa)) * float(self.product_uom_qty)
            fraction = gross_price / fraction_param
            subtotal_bad = round(float(gross_price) * (1.0 - float(comp_discount) / 100.0), 2)
        if self.subtotal_before_agency_disc == 0 or (self.subtotal_before_agency_disc > 0 and
                abs(float(subtotal_bad) - float(self.subtotal_before_agency_disc)) > fraction):
            result['subtotal_before_agency_disc'] = subtotal_bad
        return {'value': result}



    @api.onchange('product_uom_qty','comb_list_price')
    def onchange_actualqty(self):
        result = {}
        if not self.advertising:
            return {'value': result}
        if not self.multi_line:
            self.subtotal_before_agency_disc = round((float(self.price_unit) + (float(self.color_surcharge_amount))) *
                                                      float(self.product_uom_qty) * float(1.0 - self.computed_discount / 100.0), 2)
        else:
            self.subtotal_before_agency_disc = round((float(self.comb_list_price) + float(self.color_surcharge_amount)), 2)

    @api.onchange('color_surcharge' )
    def onchange_color(self):
        result = {}
        if not self.advertising:
            return {'value': result}
        pu = self.price_unit
        clp = self.comb_list_price
        if not self.multi_line:
            if self.color_surcharge:
                self.color_surcharge_amount = pu / 2
            else:
                self.color_surcharge_amount = 0.0
        else:
            if self.color_surcharge:
                self.color_surcharge_amount = clp / 2
            else:
                self.color_surcharge_amount = 0.0

    @api.onchange('color_surcharge_amount')
    def onchange_csa(self):
        result = {}
        if not self.advertising:
            return {'value': result}
        csa = self.color_surcharge_amount
        if not self.multi_line:
            self.subtotal_before_agency_disc = (self.price_unit + csa) * self.product_uom_qty * (
                        1 - self.computed_discount / 100)
        else:
            self.subtotal_before_agency_disc = (self.comb_list_price + csa) * (1 - self.computed_discount / 100)

    @api.onchange('adv_issue', 'adv_issue_ids','dates','issue_product_ids')
    def onchange_getQty(self):
        result = {}
        if not self.advertising:
            return {'value': result}
        ml_qty = 0
        ai = self.adv_issue
        ais = self.adv_issue_ids
        ds = self.dates
        iis = self.issue_product_ids
        if self.title_ids and ais:
            titles = self.title_ids.ids
            issue_ids = ais.ids
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', issue_ids)])
            issue_parent_ids = [x.parent_id.id for x in adv_issues]
            for title in titles:
                if not (title in issue_parent_ids):
                    raise UserError(_('Not for every selected Title an Issue is selected.'))
        if ais:
            if len(ais) > 1:
                ml_qty = len(ais)
                ai = False
            else:
                ai = ais.id
                ais = [(6,0,[])]
                ml_qty = 1
        elif ai:
            ml_qty = 1
        elif ds:
            if len(ds) >= 1:
                ml_qty = 1
                self.product_uom_qty = len(ds)
        elif iis:
            if len(iis) > 1:
                ml_qty = len(iis)
        if ml_qty > 1:
            self.multi_line = True
        else:
            self.multi_line = False
            if not self.title and self.title_ids:
                self.title = self.title_ids[0]
            elif self.title:
                self.title_ids = [(6,0,[])]
        self.multi_line_number = ml_qty
        self.adv_issue = ai
        self.adv_issue_ids = ais

    #added by sushma
    @api.onchange('dateperiods')
    def onchange_dateperiods(self):
        if self.date_type == 'validity':
            arr_frm_dates = [d.from_date for d in self.dateperiods]
            arr_to_dates = [d.to_date for d in self.dateperiods]
            if arr_frm_dates and arr_to_dates :
                self.from_date = min(arr_frm_dates)
                self.to_date = max(arr_to_dates)


    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        if self.advertising:
            res['account_analytic_id'] = self.adv_issue.analytic_account_id.id
            res['so_line_id'] = self.id
            res['price_unit'] = self.actual_unit_price
            res['ad_number'] = self.ad_number
            res['computed_discount'] = self.computed_discount
            res['opportunity_subject'] = self.order_id.opportunity_subject
        return res

    @api.model
    def create(self, values):
        result = super(SaleOrderLine, self).create(values)
        if self.env.context.get('LoopBreaker'):
            return result
        self = self.with_context(LoopBreaker=True)
        if result.state == 'sale' and result.advertising and result.multi_line:
            newlines = self.env['sale.order.line.create.multi.lines'].\
                create_multi_from_order_lines(orderlines=[result.id], orders=None)
            lines = self.env['sale.order.line'].browse(newlines)
            for line in lines:
                line.page_qty_check_create()
            return
        return result

    @api.multi
    def write(self, vals):
        result = super(SaleOrderLine, self).write(vals)
        user = self.env['res.users'].browse(self.env.uid)
        for line in self.filtered(lambda s: s.state in ['sale'] and s.advertising):
            if 'pubble_sent' in vals:
                continue
            is_allowed = user.has_group('account.group_account_invoice') or 'allow_user' in self.env.context
            if line.invoice_status == 'invoiced' and not (vals.get('product_uom_qty') == 0 and line.qty_invoiced == 0) \
                                                 and not is_allowed \
                                                 and not user.id == 1:

                raise UserError(_('You cannot change an order line after it has been fully invoiced.'))
            if not line.multi_line and ('product_id' in vals or 'adv_issue' in vals or 'product_uom_qty' in vals):
                if line.deadline_check():
                    line.page_qty_check_update()
        return result

    @api.multi
    def unlink(self):
        res = self.filtered(lambda x: x.env.context.get('multi'))
        if len(res) > 0:
            models.Model.unlink(res)
        return super(SaleOrderLine, self - res).unlink()

    @api.multi
    def deadline_check(self):
        self.ensure_one()
        user = self.env['res.users'].browse(self.env.uid)
        if self.issue_date and fields.Datetime.from_string(self.issue_date) <= datetime.now():
            return False
        elif not user.has_group('sale_advertising_order.group_no_deadline_check') and self.deadline:
            if fields.Datetime.from_string(self.deadline) < datetime.now():
                raise UserError(_('The deadline %s for this Category/Advertising Issue has passed.') %(self.deadline))
        return True


    @api.multi
    def page_qty_check_create(self):
        self.ensure_one()
        if not self.product_template_id.page_id:
            return
        user = self.env['res.users'].browse(self.env.uid)
        lspace = self.product_uom_qty * self.product_template_id.space
        lpage = self.product_template_id.page_id
        lpage_id = lpage.id
        avail = self.adv_issue.calc_page_space(lpage_id)
        if lspace > avail and not user.has_group('sale_advertising_order.group_no_availability_check'):
            raise UserError(_('There is not enough availability for this placement in Ordernumber %s line %s on %s in %s. '
                              'Available Capacity is %d and required is %d') % (self.order_id.name, self.id, lpage.name, self.adv_issue.name, avail, lspace))
        else:
            vals = {
                'adv_issue_id': self.adv_issue.id,
                'name': 'Afboeking',
                'order_line_id': self.id,
                'page_id': lpage_id,
                'available_qty': - int(lspace)
            }
            self.env['sale.advertising.available'].create(vals)

    @api.multi
    def page_qty_check_update(self):
        self.ensure_one()
        if not self.product_template_id.page_id:
            return
        self.page_qty_check_unlink()
        self.page_qty_check_create()

    @api.multi
    def page_qty_check_unlink(self):
        self.ensure_one()
        if not self.product_template_id.page_id:
            return
        res = self.env['sale.advertising.available'].search([('order_line_id', '=', self.id)])
        if res and len(res) > 0:
            res.unlink()



class OrderLineAdvIssuesProducts(models.Model):

    _name = "sale.order.line.issues.products"
    _description= "Advertising Order Line Advertising Issues"
    _order = "order_line_id,sequence,id"


    @api.depends('price_unit', 'qty')
    @api.multi
    def _compute_price(self):
        for line in self:
            line.price = line.price_unit * line.qty

    @api.depends('adv_issue_id', 'order_line_id.price_edit')
    @api.multi
    def _compute_price_edit(self):
        for line in self:
            if line.order_line_id.price_edit:
                line.price_edit = True
                continue
            if line.adv_issue_id.parent_id.price_edit:
                line.price_edit = True


    sequence = fields.Integer('Sequence', help="Gives the sequence of this line .", default=10)
    order_line_id = fields.Many2one('sale.order.line', 'Line', ondelete='cascade', index=True, required=True)
    adv_issue_id = fields.Many2one('sale.advertising.issue', 'Issue', ondelete='cascade', index=True, readonly=True, required=True)
    product_attribute_value_id = fields.Many2one(related='adv_issue_id.parent_id.product_attribute_value_id', relation='sale.advertising.issue',
                                      string='Title', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', ondelete='cascade', index=True, readonly=True)
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'), default=0.0, readonly=True)
    price_edit = fields.Boolean(compute=_compute_price_edit, readonly=True)
    qty = fields.Float(related='order_line_id.product_uom_qty', readonly=True)
    price = fields.Float(compute='_compute_price', string='Price', readonly=True, required=True, digits=dp.get_precision('Product Price'), default=0.0)
    page_reference = fields.Char('Reference of the Page', size=64)
    ad_number = fields.Char('External Reference', size=32)
    url_to_material = fields.Char('URL Material', size=64)


class OrderLineDate(models.Model):

    _name = "sale.order.line.date"
    _description= "Advertising Order Line Dates"
    _order = "order_line_id,sequence,id"

    sequence = fields.Integer('Sequence', help="Gives the sequence of this line .", default=10)
    order_line_id = fields.Many2one('sale.order.line', 'Line', ondelete='cascade', index=True, required=True)
    issue_date = fields.Date('Date of Issue')
    name = fields.Char('Name', size=64)
    page_reference = fields.Char('Page Preference', size=64)
    ad_number = fields.Char('External Reference', size=32)


class OrderLineDateperiod(models.Model):

    _name = "sale.order.line.dateperiod"
    _description= "Advertising Order Line Date Periods"
    _order = "order_line_id,sequence,id"

    sequence = fields.Integer('Sequence', help="Gives the sequence of this line .", default=10)
    order_line_id = fields.Many2one('sale.order.line', 'Line', ondelete='cascade', index=True, required=True)
    from_date = fields.Date('Start of Validity')
    to_date = fields.Date('End of Validity')
    name = fields.Char('Name', size=64)
    page_reference = fields.Char('Page Preference', size=64)
    ad_number = fields.Char('External Reference', size=32)


class AdvertisingProof(models.Model):
    _name = "sale.advertising.proof"
    _description="Sale Advertising Proof"

    name = fields.Char('Name', size=32, required=True)
    address_id = fields.Many2one('res.partner','Delivery Address', required=True)
    number = fields.Integer('Number of Copies', required=True, default=1)
    target_id = fields.Many2one('sale.order','Target', required=True)

class DiscountReason(models.Model):
    _name = "discount.reason"
    _description="Discount Reason"
    
    name = fields.Char('Name', size=64, required=True)



class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        if self._context.get('default_model') == 'sale.order' and self._context.get('default_res_id') and self._context.get('mark_so_as_sent'):
            order = self.env['sale.order'].browse([self._context['default_res_id']])
            if order.state in ['approved2','approved1']:
                order.state = 'sent'
        return super(MailComposeMessage, self.with_context(mail_post_autofollow=True)).send_mail(auto_commit=auto_commit)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

