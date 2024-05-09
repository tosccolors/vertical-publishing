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
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from odoo.tools.translate import unquote

import logging
_logger = logging.getLogger(__name__)



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
            # ver_tr_exc = False
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
            # if order.company_id.verify_order_setting != -1.00 and order.company_id.verify_order_setting < amount_untaxed \
            #                                                       or order.company_id.verify_discount_setting < max_cdiscount:
            #     ver_tr_exc = True
            if order.pricelist_id.currency_id:
                order.update({
                    'amount_untaxed': order.pricelist_id.currency_id.round(
                        amount_untaxed),
                    'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                    'amount_total': amount_untaxed + amount_tax,
                })

            order.update({
                # 'amount_untaxed': order.pricelist_id.currency_id and order.pricelist_id.currency_id.round(amount_untaxed) or 0.0,
                # 'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                # 'amount_total': amount_untaxed + amount_tax,
                # 'ver_tr_exc': ver_tr_exc,
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
                # invoice_status = 'not invoiced'
                invoice_status = 'to invoice'
                order['invoice_status'] = invoice_status

    @api.depends('agency_is_publish')
    
    def _compute_pub_cust_domain(self):
        """
        Compute the domain for the published_customer domain.
        """
        for rec in self:
            if rec.agency_is_publish:
                rec.pub_cust_domain = json.dumps(
                    [('is_ad_agency', '=', True), ('parent_id', '=', False), ('customer_rank', '>', 0)]
                )
            else:
                rec.pub_cust_domain = json.dumps(
                    [('is_ad_agency', '!=', True),('parent_id', '=', False), ('customer_rank', '>', 0)]
                )

    state = fields.Selection(selection=[
        ('draft', 'Draft Quotation'),
        ('submitted', 'Submitted for Approval'),
        ('approved1', 'Approved by Sales Mgr'),
        ('sent', 'Quotation Sent'),
        ('cancel', 'Cancelled'),
        ('sale', 'Sales Order'),
        ('done', 'Done'),
        ])
        # ('approved2', 'Approved by Traffic'), -- deprecated
    invoice_status = fields.Selection(selection_add=[
        ('not invoiced', 'Nothing Invoiced Yet')
        ])
    published_customer = fields.Many2one('res.partner', 'Advertiser', domain=[('customer_rank', '>', 0)])
    advertising_agency = fields.Many2one('res.partner', 'Advertising Agency', domain=[('customer_rank', '>', 0)])
    nett_nett = fields.Boolean('Netto Netto Deal', default=False)
    pub_cust_domain = fields.Char(compute=_compute_pub_cust_domain, readonly=True, store=False, )
    agency_is_publish = fields.Boolean('Agency is Publishing Customer', default=False)
    customer_contact = fields.Many2one('res.partner', 'Payer Contact Person', domain=[(('customer_rank', '>', 0))])
    traffic_employee = fields.Many2one('res.users', 'Traffic Employee',)
    traffic_comments = fields.Text('Traffic Comments')
    # traffic_appr_date = fields.Date('Traffic Confirmation Date', index=True, help="Date on which sales order is confirmed bij Traffic.") deprecated
    opportunity_subject = fields.Char('Opportunity Subject', size=64,
                          help="Subject of Opportunity from which this Sales Order is derived.")
    partner_acc_mgr = fields.Many2one(related='published_customer.user_id', relation='res.users', string='Account Manager', store=True , readonly=True)
    date_from = fields.Date(compute=lambda *a, **k: {}, string="Date from")
    date_to = fields.Date(compute=lambda *a, **k: {}, string="Date to")
    # ver_tr_exc = fields.Boolean(string='Verification Treshold', store=True, readonly=True, compute='_amount_all', track_visibility='always') # -- deep: deprecated
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

    def _ctx_4_action_orders_advertising_smart_button(self):
        " Context to use both active & ref"
        ref = self.env.ref
        active_id = unquote("active_id")

        return {
            'type_id': ref('sale_advertising_order.ads_sale_type').id,
            'default_advertising': True,
            'default_published_customer': active_id
        }

    def _domain_4_action_orders_advertising_smart_button(self):
        " Domain to use both active & ref"
        ref = self.env.ref
        active_id = unquote("active_id")

        return [('type_id','=', ref('sale_advertising_order.ads_sale_type').id), ('advertising','=',True),
                            ('state','in',('sale','done')),'|',('published_customer','=',active_id),
                            ('advertising_agency','=',active_id)]


    def _ctx_4_sale_action_quotations_new_adv(self):
        " Context to use both active & ref"
        ref = self.env.ref
        active_id = unquote("active_id")

        return {'default_advertising': 1, 'default_type_id': ref('sale_advertising_order.ads_sale_type').id,
                'search_default_opportunity_id': active_id,
                'default_opportunity_id': active_id}

    def _domain_4_sale_action_quotations_new_adv(self):
        " Domain to use both active & ref"
        ref = self.env.ref
        active_id = unquote("active_id")

        return [('type_id','=', ref('sale_advertising_order.ads_sale_type').id), ('opportunity_id', '=', active_id), ('advertising','=',True)]


    def _ctx_4_sale_action_quotations_adv(self):
        " Context to use both active & ref"
        ref = self.env.ref
        active_id = unquote("active_id")

        return {'hide_sale': True, 'default_advertising': 1, 'default_type_id': ref('sale_advertising_order.ads_sale_type').id
                , 'search_default_opportunity_id': [active_id], 'default_opportunity_id': active_id}

    def _domain_4_sale_action_quotations_adv(self):
        " Domain to use both active & ref"
        ref = self.env.ref
        active_id = unquote("active_id")

        return [('type_id','=', ref('sale_advertising_order.ads_sale_type').id), ('opportunity_id', '=', active_id), ('advertising','=',True)]


    # overridden:
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
        if self.env.user.company_id.call_onchange_for_payers_advertisers:
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


    
    def action_submit(self):
        orders = self.filtered(lambda s: s.state in ['draft'])
        for o in orders:
            if not o.order_line:
                raise UserError(_('You cannot submit a quotation/sales order which has no line.'))
        return self.write({'state': 'submitted'})

    # --added deep
    def action_approve1(self):
        orders = self.filtered(lambda s: s.state in ['submitted'])
        orders.write({'state':'approved1'})
        return True

    # deprecated
    # def action_approve2(self):
    #     orders = self.filtered(lambda s: s.state in ['approved1', 'submitted'])
    #     orders.write({'state': 'approved2',
    #                   'traffic_appr_date': fields.Date.context_today(self)})
    #     return True

    # --added deep
    def action_refuse(self):
        orders = self.filtered(lambda s: s.state in ['submitted', 'sale', 'sent', 'approved1'])
        orders.write({'state':'draft'})
        return True

    # overridden: -- added deep
    # # FIXME: deprecated method:
    # def print_quotation(self):
    #     self.ensure_one()
    #
    #     orders = self.filtered(lambda s: s.advertising and s.state in ['draft','approved1', 'submitted', 'approved2'])
    #     for order in orders:
    #         olines = []
    #         for line in order.order_line:
    #             if line.multi_line:
    #                 olines.append(line.id)
    #         if not olines == []:
    #             self.env['sale.order.line.create.multi.lines'].create_multi_from_order_lines(orderlines=olines)
    #     self._cr.commit()
    #     orders.write({'state': 'sent'})
    #     # return super(SaleOrder, self).print_quotation() -- deprecated method.

    def action_quotation_send(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        if not self.advertising:
            return super(SaleOrder, self).action_quotation_send()

        elif self.state in ['draft', 'approved1', 'submitted']:
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


    
    def action_cancel(self):
        for order in self.filtered(lambda s: s.state == 'sale' and s.advertising):
            for line in order.order_line:
                line.page_qty_check_unlink()
        return super(SaleOrder, self).action_cancel()

    
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

    
    def write(self, vals):
        result = super(SaleOrder, self).write(vals)
        # import pdb; pdb.set_trace()

        _logger.info("GET I COME HERE SO WRITE ")
        orders = self.filtered(lambda s: s.state in ['sale'] and s.advertising and not s.env.context.get('no_checks'))
        for order in orders:
            user = self.env['res.users'].browse(self.env.uid)
            # -- deep: deprecated
            # if not user.has_group('sale_advertising_order.group_no_discount_check') \
            #    and self.ver_tr_exc:
            #     raise UserError(_(
            #         'You cannot save a Sale Order with a line more than %s%s discount or order total amount is more than %s.'
            #         '\nYou\'ll have to cancel the order and '
            #         'resubmit it or ask Sales Support for help.') % (
            #                     order.company_id.verify_discount_setting, '%', order.company_id.verify_order_setting))
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


    def _get_name_quotation_report(self):
        self.ensure_one()
        ref = self.env.ref
        template = 'sale.report_saleorder_document'

        if self.type_id.id == ref('sale_advertising_order.ads_sale_type').id:
            template = 'sale_advertising_order.report_saleorder_document_sao'

        return template




class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends('product_uom_qty', 'order_id.partner_id', 'order_id.nett_nett', 'nett_nett', 'subtotal_before_agency_disc',
                 'price_unit', 'tax_id')
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
                    decimals=self.env['decimal.precision'].sudo().search([('name','=','Product Price')]).digits or 4
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
                if clp > 0.0 and comp_discount > 0.0:
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

    @api.depends('adv_issue', 'ad_class', 'from_date')
    def _compute_deadline(self):
        """
        Compute the deadline for this placement.
        """
        user = self.env['res.users'].browse(self.env.uid)
        for line in self.filtered('advertising'):
            line.deadline_passed = False
            line.deadline = False
            line.deadline_offset = False
            if line.date_type == 'issue_date':
                line.deadline = line.adv_issue.deadline
            elif line.date_type == 'validity' and line.from_date:
                deadline_dt = (datetime.strptime(str(line.from_date), "%Y-%m-%d") + timedelta(hours=3, minutes=30)) - timedelta(days=14)
                line.deadline = deadline_dt
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
    def _compute_tags_domain(self):
        """
        Compute the domain for the Pageclass domain.
        """
        for rec in self:
            rec.page_class_domain = json.dumps(
                [('id', 'in', rec.ad_class.tag_ids.ids)]
            )

    @api.depends('title', 'product_template_id')
    def _compute_price_edit(self):
        """
        Compute if price_unit should be editable.
        """
        for line in self.filtered('advertising'):
            line.price_edit = False
            if line.product_template_id and line.product_template_id.price_edit or line.title.price_edit:
                line.price_edit = True

    @api.model
    def _get_adClass_domain(self):
        if not self.medium:
            return [('id','child_of', self.env.ref('sale_advertising_order.advertising_category', raise_if_not_found=False).id)]

        return [('id','child_of', self.medium.id), ('id', '!=', self.medium.id)]


    @api.depends('ad_class', 'title_ids')
    def _get_prodTemplate2filter(self):
        " Explicit Domain to filter Product based on Title Attribute "

        AdsSOT = self.env.ref('sale_advertising_order.ads_sale_type').id
        defSOT = self._context.get('default_type_id', False)

        for line in self:
            ptmplIDs = []

            # Check SO type: Ads SOT
            if (line.order_id and line.order_id.type_id.id == AdsSOT) or (defSOT == AdsSOT):

                if line.ad_class and line.title_ids:
                    ATpavIds = line.title_ids.mapped('product_attribute_value_id').ids
                    prodTmpls = self.env['product.product'].search(
                        [('sale_ok', '=', True),
                         ('categ_id', '=', line.ad_class.id),
                         ('product_template_attribute_value_ids.product_attribute_value_id', 'in', ATpavIds)]).mapped('product_tmpl_id')

                    # Ensure all Title's PAV combination exists:
                    for pt in prodTmpls:
                        validPAV = pt.valid_product_template_attribute_line_ids.mapped("product_template_value_ids").mapped('product_attribute_value_id').ids
                        if all(i in validPAV for i in ATpavIds):
                            ptmplIDs.append(pt.id)

            line.domain4prod_ids = [(6, 0, ptmplIDs)]

    @api.depends('state')
    def _get_product_data(self):
        for line in self:
            prod = line.product_id
            if prod:
                line.product_width = prod.width
                line.product_height = prod.height

    @api.model
    def _get_domain4Titles(self):
        domain = [('parent_id','=', False)] # default
        if self.medium:
            domain += [('medium','child_of', self.medium.id)]
        return domain

    @api.model
    def _get_domain4Issues(self):
        domain = []
        if self.title_ids:
            domain = [('parent_id', 'in', self.title_ids.ids)]

        # No deadline check
        if not self.env.user.has_group('sale_advertising_order.group_no_deadline_check'):
            domain += ['|', '|', ('deadline', '>=', self.deadline_offset), ('deadline', '=', False),
                       ('issue_date', '<=', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))]

        return domain


    mig_remark = fields.Text('Migration Remark')
    layout_remark = fields.Text('Material Remark')
    title = fields.Many2one('sale.advertising.issue', 'Title', domain=[('child_ids','<>', False)])
    page_class_domain = fields.Char(compute='_compute_tags_domain', readonly=True, store=False,)
    title_ids = fields.Many2many('sale.advertising.issue', 'sale_order_line_adv_issue_title_rel', 'order_line_id', 'adv_issue_id', 'Titles',
                                 domain=_get_domain4Titles)
    adv_issue_ids = fields.Many2many('sale.advertising.issue','sale_order_line_adv_issue_rel', 'order_line_id', 'adv_issue_id',  'Advertising Issues',
                                     domain=_get_domain4Issues)
    issue_product_ids = fields.One2many('sale.order.line.issues.products', 'order_line_id', 'Adv. Issues with Product Prices')
    dates = fields.One2many('sale.order.line.date', 'order_line_id', 'Advertising Dates') # FIXME: deprecated
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
    ad_class = fields.Many2one('product.category', 'Advertising Class', domain=_get_adClass_domain)
    deadline_passed = fields.Boolean(compute='_compute_deadline', string='Deadline Passed')
    deadline = fields.Datetime(compute='_compute_deadline', string='Deadline', store=False)
    deadline_offset = fields.Datetime(compute='_compute_deadline')
    product_template_id = fields.Many2one('product.template', string='Product', domain=[('sale_ok', '=', True)],
                                 change_default=True, ondelete='restrict')
    page_reference = fields.Char('Page Preference', size=32)
    ad_number = fields.Char('External Reference', size=50)
    url_to_material = fields.Char('URL Material')
    from_date = fields.Date('Start of Validity')
    to_date = fields.Date('End of Validity')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('submitted', 'Submitted for Approval'),
        ('approved1', 'Approved by Sales Mgr'),
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
    actual_unit_price = fields.Float(compute='_compute_amount', string='Actual Unit Price', digits='Product Price',
                                        default=0.0, readonly=True)
    comb_list_price = fields.Monetary(compute='_multi_price', string='Combined_List Price', default=0.0, store=True,
                                digits='Account')
    computed_discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    subtotal_before_agency_disc = fields.Monetary(string='Subtotal before Commission', digits='Account')
    advertising = fields.Boolean(related='order_id.advertising', string='Advertising', store=True)
    multi_line = fields.Boolean(string='Multi Line')
    color_surcharge = fields.Boolean(string='Color Surcharge') # deprecated in UI
    price_edit = fields.Boolean(compute='_compute_price_edit', string='Price Editable')
    color_surcharge_amount = fields.Monetary(string='Color Surcharge', digits='Product Price') # deprecated in UI
    discount_reason_id = fields.Many2one('discount.reason', 'Discount Reason')
    nett_nett = fields.Boolean(string='Netto Netto Line')
    # proof_number_adv_customer = fields.Boolean('Proof Number Advertising Customer', default=False) #deep: has been overridden to M2M as below
    proof_number_payer = fields.Boolean('Proof Number Payer', default=False)
    booklet_surface_area = fields.Float(related='product_template_id.booklet_surface_area', readonly=True, string='Booklet Surface Area',digits='Product Unit of Measure')
    domain4prod_ids = fields.Many2many('product.template', string='Domain for Product Template', compute=_get_prodTemplate2filter)


    # Brought from nsm_sale_advertising_order
    proof_number_payer_id = fields.Many2one('res.partner', 'Proof Number Payer ID')
    proof_number_adv_customer = fields.Many2many('res.partner', 'partner_line_proof_rel', 'line_id', 'partner_id',
                                                 string='Proof Number Advertising Customer')
    proof_number_amt_payer = fields.Integer('Proof Number Amount Payer', default=1)
    proof_number_amt_adv_customer = fields.Integer('Proof Number Amount Advertising', default=1)

    product_width = fields.Float(compute='_get_product_data', readonly=True, store=False, string="Width")
    product_height = fields.Float(compute='_get_product_data', readonly=True, store=False, string="Height")


    @api.onchange('medium')
    def onchange_medium(self):
        vals, data, result = {}, {}, {}
        _logger.info("\n Came inside >>> onchange_medium [medium]")
        if not self.advertising:
            return {'value': vals }
        if self.medium:
            # import pdb; pdb.set_trace()
            child_id = [(x.id != self.medium.id) and x.id for x in self.medium.child_id]

            if len(child_id) == 1:
                vals['ad_class'] = child_id[0]
            else:
                vals['ad_class'] = False
                data = {'ad_class': [('id', 'child_of', self.medium.id), ('id', '!=', self.medium.id)]}
            titles = self.env['sale.advertising.issue'].search([('parent_id','=', False),('medium', 'child_of', self.medium.id)]).ids
            if titles and len(titles) == 1:
                vals['title'] = titles[0]
                # vals['title_ids'] = [(6, 0, [])]
                vals['title_ids'] = [(6, 0, titles)]
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
        _logger.info("\n Came inside >>> onchange_ad_class [ad_class]")
        if not self.advertising:
            return {'value': vals}

        # Reset
        if not self.ad_class:
            self.product_template_id = False

        # -- deprecated -- NOT needed anymore
        # titles = self.title_ids if self.title_ids else self.title or False
        # domain = []
        # if titles:
        #     product_ids = self.env['product.product']
        #     for title in titles:
        #         if title.product_attribute_value_id:
        #             ids = product_ids.search([('product_template_attribute_value_ids', 'in', [title.product_attribute_value_id.id])])
        #             product_ids += ids
        #     product_tmpl_ids = product_ids.mapped('product_tmpl_id').ids
        #     domain = [('id', 'in', product_tmpl_ids)]

        # if self.ad_class:
        #     product_ids = self.env['product.template'].search(domain+[('categ_id', '=', self.ad_class.id)])
        #     if product_ids and len(product_ids) == 1:
        #         vals['product_template_id'] = product_ids[0]
        #     else:
        #         vals['product_template_id'] = False
        #     date_type = self.ad_class.date_type
        #     if date_type:
        #         vals['date_type'] = date_type
        #     else: result = {'title':_('Warning'),
        #                          'message':_('The Ad Class has no Date Type. You have to define one')}
        # else:
        #     vals['product_template_id'] = False
        #     vals['date_type'] = False
        # return {'value': vals, 'domain' : data, 'warning': result}

    # @api.onchange('title')
    # def title_oc(self):
    #     data, vals = {}, {}
    #     _logger.info("\n Came inside >>> title_oc [title]")
    #     if not self.advertising:
    #         return {'value': vals}
    #     if self.title:
    #         adissue_ids = self.title.child_ids.ids
    #         if len(adissue_ids) == 1:
    #             vals['adv_issue'] = adissue_ids[0]
    #             vals['adv_issue_ids'] = [(6, 0, [])]
    #             vals['product_id'] = False
    #         else:
    #             vals['adv_issue'] = False
    #             vals['product_id'] = False
    #     else:
    #         vals['adv_issue'] = False
    #         vals['product_id'] = False
    #         vals['adv_issue_ids'] = [(6, 0, [])]
    #     return {'value': vals, 'domain': data}
    #
    # @api.onchange('title_ids')
    # def title_ids_oc(self):
    #     _logger.info("\n Came inside >>> title_ids_oc [title_ids]")
    #     vals = {}
    #     if not self.advertising:
    #         return {'value': vals}
    #     if self.title_ids and self.adv_issue_ids:
    #         titles = self.title_ids.ids
    #         issue_ids = self.adv_issue_ids.ids
    #         adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', issue_ids)])
    #         issue_parent_ids = [x.parent_id.id for x in adv_issues]
    #         for title in titles:
    #             if not (title in issue_parent_ids):
    #                 raise UserError(_('Not for every selected Title an Issue is selected.'))
    #         if len(self.title_ids) == 1:
    #             self.title = self.title_ids[0]
    #             self.title_ids = [(6, 0, [])]
    #
    #     elif self.title_ids and self.issue_product_ids:
    #         titles = self.title_ids.ids
    #         adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', [x.adv_issue_id.id for x in self.issue_product_ids])])
    #         issue_parent_ids = [x.parent_id.id for x in adv_issues]
    #         back = False
    #         for title in titles:
    #             if not (title in issue_parent_ids):
    #                 back = True
    #                 break
    #         if back:
    #             self.adv_issue_ids = [(6, 0, adv_issues.ids)]
    #             self.issue_product_ids = [(6, 0, [])]
    #         if len(self.title_ids) == 1:
    #             self.title = self.title_ids[0]
    #             self.title_ids = [(6, 0, [])]
    #         self.titles_issues_products_price()
    #
    #     elif self.title_ids:
    #         self.product_template_id = False
    #         self.product_id = False
    #     else:
    #         self.adv_issue = False
    #         self.adv_issue_ids = [(6, 0, [])]
    #         self.issue_product_ids = [(6, 0, [])]
    #         self.product_id = False
    #         self.product_template_id = False
    #         self.product_uom = False




    @api.onchange('title', 'title_ids')
    def onchange_title(self):
        " Merge & Deprecate usage of  field title & adv_issue "

        _logger.info("\n Came inside >>> DEEP onchange  [title | title_ids]")
        vals = {}
        if not self.advertising:
            return {'value': vals}

        # Single Title: pre-populate Issue if only one present:
        if len(self.title_ids) == 1 and not self.adv_issue_ids:
            self.title = self.title_ids[0]
            adissue_ids = self.title_ids.child_ids.ids
            if len(adissue_ids) == 1:
                self.adv_issue = adissue_ids[0]
                self.adv_issue_ids = [(6, 0, adissue_ids)]

        elif len(self.title_ids) > 1: # Multi Titles:
            self.title = False

        if self.title_ids and self.adv_issue_ids:
            titles = self.title_ids.ids
            issue_ids = self.adv_issue_ids.ids
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', issue_ids)])
            issue_parent_ids = [x.parent_id.id for x in adv_issues]
            for title in titles:
                if not (title in issue_parent_ids):
                    raise UserError(_('Not for every selected Title an Issue is selected.'))
            # if len(self.title_ids) == 1:
            #     self.title = self.title_ids[0]
            #     self.title_ids = [(6, 0, [])]

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
            # if len(self.title_ids) == 1:
            #     self.title = self.title_ids[0]
            #     self.title_ids = [(6, 0, [])]
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

        return {'domain': {'adv_issue_ids': self._get_domain4Issues()}}

    @api.onchange('product_template_id')
    def titles_issues_products_price(self):
        _logger.info("\n Came inside >>> titles_issues_products_price [product_template_id] ")
        vals = {}
        if not self.advertising:
            return {'value': vals}
        # import pdb; pdb.set_trace()
        if not self.product_template_id:
            self.issue_product_ids = [(6, 0, [])]

        if self.title_ids and (len(self.adv_issue_ids) == 0):
            raise UserError(_('Please select Advertising Issue(s) to proceed further.'))

        volume_discount = self.product_template_id.volume_discount
        if self.product_template_id and self.adv_issue_ids and len(self.adv_issue_ids) > 1:
            _logger.info("Did i come here? - Multiple Edition ")
            self.product_uom = self.product_template_id.uom_id
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', self.adv_issue_ids.ids)])
            values = []
            self.issue_product_ids = []  # reset
            product_id = False
            price = 0
            issues_count = len(adv_issues)
            for adv_issue in adv_issues:
                _logger.info("Loop for ==> %s"%adv_issue)
                _logger.info("Inside Loop : %s , %s, %s, %s "%(adv_issue.parent_id.id ,  self.title_ids.ids , adv_issue.parent_id.id , self.title.id))
                if adv_issue.parent_id.id in self.title_ids.ids or adv_issue.parent_id.id == self.title.id:
                    value = {}
                    if adv_issue.product_attribute_value_id:
                        pav = adv_issue.product_attribute_value_id.id
                        _logger.info("IF > pav %s" % pav)
                    else:
                        pav = adv_issue.parent_id.product_attribute_value_id.id
                        _logger.info("ELSE > pav %s" % pav)
                    _logger.info("Found ? pav %s" % pav)
                    product_id = self.env['product.product'].search(
                        [('product_tmpl_id', '=', self.product_template_id.id), ('product_template_attribute_value_ids.product_attribute_value_id', '=', pav)])
                    _logger.info("[Inside Loop] found pp %s \n PT %s" % (product_id, self.product_template_id))
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
                            _logger.info("Value %s"%value)
                            values.append((0,0, value))
            if product_id:
                self.update({
                    # 'adv_issue_ids': [(6, 0, [])], # FIXME: Need this?
                    'issue_product_ids': values,
                    'product_id': product_id.id,
                    'multi_line_number': issues_count,
                    'multi_line': True,
                })
            self.comb_list_price = price
            self.subtotal_before_agency_disc = price

        elif self.product_template_id and self.issue_product_ids and len(self.issue_product_ids) > 1:
            _logger.info("Did i come here? - Single Issue Product ")
            self.product_uom = self.product_template_id.uom_id
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', [x.adv_issue_id.id for x in self.issue_product_ids])])
            values = []
            self.issue_product_ids = [] # reset
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
                        [('product_tmpl_id', '=', self.product_template_id.id), ('product_template_attribute_value_ids.product_attribute_value_id', '=', pav)])
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
                            _logger.info("Values %s" % value)
                            values.append((0,0, value))
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
                _logger.info("Did i come here? - Single Edition ")
                if self.adv_issue_ids and len(self.adv_issue_ids) == 1:
                    self.adv_issue = self.adv_issue_ids.id
                if self.adv_issue.parent_id.id == self.title.id:
                    if self.adv_issue.product_attribute_value_id:
                        pav = self.adv_issue.product_attribute_value_id.id
                        _logger.info("IF > pav ID %s :: %s" % (pav, self.adv_issue.product_attribute_value_id.name))
                    else:
                        pav = self.adv_issue.parent_id.product_attribute_value_id.id
                        _logger.info("ELSE pav ID %s :: %s" % (pav,self.adv_issue.parent_id.product_attribute_value_id))
                    _logger.info("whats pav %s"%pav)
                    product_id = self.env['product.product'].search(
                        [('product_tmpl_id', '=', self.product_template_id.id), ('product_template_attribute_value_ids.product_attribute_value_id', '=', pav)])
                    _logger.info("found pp %s \n PT %s" %(product_id, self.product_template_id))
                    if product_id:
                        self.update({
                            # 'adv_issue_ids': [(6, 0, [])], # FIXME: Need this?
                            # 'issue_product_ids': [(6, 0, [])], # FIXME: Need this?
                            'product_id': product_id.id,
                            'multi_line_number': 1,
                            'multi_line': False,
                        })

    
    @api.onchange('product_id')
    def product_id_change(self):
        _logger.info("\n Came inside >>> product_id_change [product_id] ")
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
        _logger.info("\n Came inside >>> onchange_date_type [date_type] ")
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
                    vals['dates'] = [(6,0,[])] # FIXME: deprecated
                if self.adv_issue_ids:
                    vals['adv_issue_ids'] = [(6,0,[])]
            elif self.date_type == 'issue_date':
                if self.dates:
                    vals['dates'] = [(6,0,[])] # FIXME: deprecated
                if self.dateperiods:
                    vals['dateperiods'] = [(6,0,[])]
        return {'value': vals}



    @api.onchange('price_unit')
    def onchange_price_unit(self):
        _logger.info("\n Came inside >>> onchange_price_unit [price_unit] ")
        result = {}
        stprice = 0
        if not self.advertising:
            return {'value': result}
        if self.price_unit > 0 and self.product_uom_qty > 0:
             stprice = self.price_unit * self.product_uom_qty

        self.subtotal_before_agency_disc = stprice
        return {'value': result}

    @api.onchange('computed_discount')
    def onchange_actualcd(self):
        _logger.info("\n Came inside >>> onchange_actualcd [computed_discount] ")
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
        fraction_param = int(self.env['ir.config_parameter'].sudo().get_param('sale_advertising_order.fraction'))

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
        _logger.info("\n Came inside >>> onchange_actualqty [product_uom_qty, comb_list_price] ")
        result = {}
        if not self.advertising:
            return {'value': result}
        if not self.multi_line:
            self.subtotal_before_agency_disc = round((float(self.price_unit) + (float(self.color_surcharge_amount))) *
                                                      float(self.product_uom_qty) * float(1.0 - self.computed_discount / 100.0), 2)
        else:
            self.subtotal_before_agency_disc = round((float(self.comb_list_price) + float(self.color_surcharge_amount)), 2)

    # deprecated
    # @api.onchange('color_surcharge' )
    # def onchange_color(self):
    #     result = {}
    #     if not self.advertising:
    #         return {'value': result}
    #     pu = self.price_unit
    #     clp = self.comb_list_price
    #     if not self.multi_line:
    #         if self.color_surcharge:
    #             self.color_surcharge_amount = pu / 2
    #         else:
    #             self.color_surcharge_amount = 0.0
    #     else:
    #         if self.color_surcharge:
    #             self.color_surcharge_amount = clp / 2
    #         else:
    #             self.color_surcharge_amount = 0.0

    # deprecated
    # @api.onchange('color_surcharge_amount')
    # def onchange_csa(self):
    #     result = {}
    #     if not self.advertising:
    #         return {'value': result}
    #     csa = self.color_surcharge_amount
    #     if not self.multi_line:
    #         self.subtotal_before_agency_disc = (self.price_unit + csa) * self.product_uom_qty * (
    #                     1 - self.computed_discount / 100)
    #     else:
    #         self.subtotal_before_agency_disc = (self.comb_list_price + csa) * (1 - self.computed_discount / 100)

    # @api.onchange('adv_issue', 'adv_issue_ids','dates','issue_product_ids')
    @api.onchange('adv_issue', 'adv_issue_ids','issue_product_ids')
    def onchange_getQty(self):
        _logger.info("\n Came inside >>> onchange_getQty [adv_issue | adv_issue_ids | dates | issue_product_ids]")
        result = {}
        if not self.advertising:
            return {'value': result}
        ml_qty = 0
        ai = self.adv_issue
        ais = self.adv_issue_ids
        ds = self.dates # FIXME: deprecated
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
        elif ds: # FIXME: deprecated
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
            # if not self.title and self.title_ids: # FIXME: deep
            #     self.title = self.title_ids[0]
            # elif self.title:
            #     self.title_ids = [(6,0,[])]
        self.multi_line_number = ml_qty
        # self.adv_issue = ai # FIXME: deep
        # self.adv_issue_ids = ais # FIXME: deep

    # #added by sushma | deprecated -- deepa
    # @api.onchange('dateperiods')
    # def onchange_dateperiods(self):
    #     if self.date_type == 'validity':
    #         arr_frm_dates = [d.from_date for d in self.dateperiods]
    #         arr_to_dates = [d.to_date for d in self.dateperiods]
    #         if arr_frm_dates and arr_to_dates :
    #             self.from_date = min(arr_frm_dates)
    #             self.to_date = max(arr_to_dates)

    @api.onchange('from_date', 'to_date')
    def _check_validity_dates(self,):
        "Check correctness of date"
        if self.from_date and self.to_date:
            if (self.from_date > self.to_date):
                raise UserError(_('Please make sure that the start date is smaller than or equal to the end date.'))

    @api.constrains('from_date', 'to_date')
    def _check_start_end_dates(self):
        "Check correctness of date"
        for case in self:
            if case.from_date and case.to_date:
                if case.from_date > case.to_date:
                    raise ValidationError(
                        _("Please make sure that the start date is smaller than or equal to the end date '%s'.")
                        % (case.name))

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        if self.advertising:
            res['analytic_account_id'] = self.adv_issue.analytic_account_id.id
            res['so_line_id'] = self.id
            res['price_unit'] = self.actual_unit_price
            res['ad_number'] = self.ad_number
            res['computed_discount'] = self.computed_discount
            res['opportunity_subject'] = self.order_id.opportunity_subject
        else:
            res['so_line_id'] = self.id
            
        return res
    @api.model
    def create(self, values):
        result = super(SaleOrderLine, self).create(values)
        if self.env.context.get('LoopBreaker'):
            return result
        self = self.with_context(LoopBreaker=True)
        if result.state == 'sale' and result.advertising and result.multi_line:
            _logger.info("GET I COME HERE create_multi_from_order_lines ")
            newlines = self.env['sale.order.line.create.multi.lines'].\
                create_multi_from_order_lines(orderlines=[result.id], orders=None)
            lines = self.env['sale.order.line'].browse(newlines)
            for line in lines:
                line.page_qty_check_create()
            return
        return result

    
    def write(self, vals):
        result = super(SaleOrderLine, self).write(vals)
        user = self.env['res.users'].browse(self.env.uid)
        for line in self.filtered(lambda s: s.state in ['sale'] and s.advertising):
            if 'pubble_sent' in vals:
                continue

            # deprecated this logic -- Modification of confirmed SO shall no longer be allowed
            # is_allowed = user.has_group('account.group_account_invoice') or 'allow_user' in self.env.context
            # if line.invoice_status == 'invoiced' and not (vals.get('product_uom_qty') == 0 and line.qty_invoiced == 0) \
            #                                      and not is_allowed \
            #                                      and not user.id == 1:
            #     raise UserError(_('You cannot change an order line after it has been fully invoiced. SO: %s , state: %s, allowed: %s vals : %s'%(line.order_id.name, line.invoice_status, is_allowed, vals)))

            if not line.multi_line and ('product_id' in vals or 'adv_issue' in vals or 'product_uom_qty' in vals):
                if line.deadline_check():
                    line.page_qty_check_update()
        return result

    
    def unlink(self):
        res = self.filtered(lambda x: x.env.context.get('multi'))
        if len(res) > 0:
            models.Model.unlink(res)
        return super(SaleOrderLine, self - res).unlink()

    
    def deadline_check(self):
        self.ensure_one()
        user = self.env['res.users'].browse(self.env.uid)
        if self.issue_date and fields.Datetime.from_string(self.issue_date) <= datetime.now():
            return False
        elif not user.has_group('sale_advertising_order.group_no_deadline_check') and self.deadline:
            if fields.Datetime.from_string(self.deadline) < datetime.now():
                raise UserError(_('The deadline %s for this Category/Advertising Issue has passed.') %(self.deadline))
        return True


    
    def page_qty_check_create(self):
        self.ensure_one()
        if not self.product_template_id.page_id:
            return
        # user = self.env['res.users'].browse(self.env.uid)
        lspace = self.product_uom_qty * self.product_template_id.space
        lpage = self.product_template_id.page_id
        lpage_id = lpage.id
        # avail = self.adv_issue.calc_page_space(lpage_id)
        vals = {
            'adv_issue_id': self.adv_issue.id,
            'name': 'Afboeking',
            'order_line_id': self.id,
            'page_id': lpage_id,
            'available_qty': - int(lspace)
        }
        self.env['sale.advertising.available'].create(vals)

        # --deep deprecated
        # if lspace > avail and not user.has_group('sale_advertising_order.group_no_availability_check'):
        #     raise UserError(_('There is not enough availability for this placement in Ordernumber %s line %s on %s in %s. '
        #                       'Available Capacity is %d and required is %d') % (self.order_id.name, self.id, lpage.name, self.adv_issue.name, avail, lspace))
        # else:
        #     vals = {
        #         'adv_issue_id': self.adv_issue.id,
        #         'name': 'Afboeking',
        #         'order_line_id': self.id,
        #         'page_id': lpage_id,
        #         'available_qty': - int(lspace)
        #     }
        #     self.env['sale.advertising.available'].create(vals)

    
    def page_qty_check_update(self):
        self.ensure_one()
        if not self.product_template_id.page_id:
            return
        self.page_qty_check_unlink()
        self.page_qty_check_create()

    
    def page_qty_check_unlink(self):
        self.ensure_one()
        if not self.product_template_id.page_id:
            return
        res = self.env['sale.advertising.available'].search([('order_line_id', '=', self.id)])
        if res and len(res) > 0:
            res.unlink()

    @api.model
    def default_get(self, fields_list):
        'Migration: from nsm_sale_advertising_order'
        result = super(SaleOrderLine, self).default_get(fields_list)
        if 'customer_contact' in self.env.context:
            result.update({'proof_number_payer_id': self.env.context['customer_contact']})
            result.update({'proof_number_amt_payer': 1})

        result.update({'proof_number_adv_customer': False})
        result.update({'proof_number_amt_adv_customer': 0})
        return result


    @api.onchange('proof_number_adv_customer')
    def onchange_proof_number_adv_customer(self):
        'Migration: from nsm_sale_advertising_order'
        self.proof_number_amt_adv_customer = 1 if self.proof_number_adv_customer else 0

    @api.onchange('proof_number_amt_adv_customer')
    def onchange_proof_number_amt_adv_customer(self):
        'Migration: from nsm_sale_advertising_order'
        if self.proof_number_amt_adv_customer <= 0: self.proof_number_adv_customer = False

    @api.onchange('proof_number_amt_payer')
    def onchange_proof_number_amt_payer(self):
        'Migration: from nsm_sale_advertising_order'
        if self.proof_number_amt_payer < 1: self.proof_number_payer_id = False

    @api.onchange('proof_number_payer_id')
    def onchange_proof_number_payer_id(self):
        'Migration: from nsm_sale_advertising_order'
        self.proof_number_amt_payer = 1 if self.proof_number_payer_id else 0

    def cancel_line(self):
        'Allow cancel of SOL by resetting qty to Zero'
        self.ensure_one()
        if self.invoice_status != 'to invoice':
            return
        self.product_uom_qty = 0



class OrderLineAdvIssuesProducts(models.Model):

    _name = "sale.order.line.issues.products"
    _description= "Advertising Order Line Advertising Issues"
    _order = "order_line_id,sequence,id"


    @api.depends('price_unit', 'qty')
    
    def _compute_price(self):
        for line in self:
            line.price = line.price_unit * line.qty

    @api.depends('adv_issue_id', 'order_line_id.price_edit')
    def _compute_price_edit(self):
        for line in self:
            line.price_edit = False
            if line.order_line_id and line.order_line_id.price_edit:
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
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0, readonly=True)
    price_edit = fields.Boolean(compute=_compute_price_edit, readonly=True)
    qty = fields.Float(related='order_line_id.product_uom_qty', readonly=True)
    price = fields.Float(compute='_compute_price', string='Price', readonly=True, required=True, digits='Product Price', default=0.0)
    page_reference = fields.Char('Reference of the Page', size=64)
    ad_number = fields.Char('External Reference', size=50)
    url_to_material = fields.Char('URL Material', size=64)


# FIXME: deprecated model
class OrderLineDate(models.Model):

    _name = "sale.order.line.date"
    _description= "Advertising Order Line Dates"
    _order = "order_line_id,sequence,id"

    sequence = fields.Integer('Sequence', help="Gives the sequence of this line .", default=10)
    order_line_id = fields.Many2one('sale.order.line', 'Line', ondelete='cascade', index=True, required=True)
    issue_date = fields.Date('Date of Issue')
    name = fields.Char('Name', size=64)
    page_reference = fields.Char('Page Preference', size=64)
    ad_number = fields.Char('External Reference', size=50)


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
    ad_number = fields.Char('External Reference', size=50)


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

    
    def send_mail(self, auto_commit=False):
        if self._context.get('default_model') == 'sale.order' and self._context.get('default_res_id') and self._context.get('mark_so_as_sent'):
            order = self.env['sale.order'].browse([self._context['default_res_id']])
            if order.state in ['approved1']:
                order.state = 'sent'
        return super(MailComposeMessage, self.with_context(mail_post_autofollow=True)).send_mail(auto_commit=auto_commit)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

