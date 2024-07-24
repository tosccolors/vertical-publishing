# -*- coding: utf-8 -*-
# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from odoo.tools.translate import unquote

from functools import partial
from odoo.tools.misc import formatLang

import logging
_logger = logging.getLogger(__name__)



class SaleOrder(models.Model):
    _inherit = ["sale.order"]

    @api.depends('agency_is_publish')
    def _compute_pub_cust_domain(self):
        """
        Compute the domain for the published_customer domain.
        """
        for rec in self:
            if rec.agency_is_publish:
                rec.pub_cust_domain = json.dumps(
                    [('is_ad_agency', '=', True), ('parent_id', '=', False), ('is_customer', '=', True)]
                )
            else:
                rec.pub_cust_domain = json.dumps(
                    [('is_ad_agency', '!=', True),('parent_id', '=', False), ('is_customer', '=', True)]
                )


    state = fields.Selection(selection_add=[
        ('submitted', 'Submitted for Approval'),
        ('approved1', 'Approved by Sales Mgr'),])

    published_customer = fields.Many2one('res.partner', 'Advertiser', domain=[('is_customer', '=', True)])
    advertising_agency = fields.Many2one('res.partner', 'Advertising Agency', domain=[('is_customer', '=', True)])
    nett_nett = fields.Boolean('Netto Netto Deal', default=False)
    pub_cust_domain = fields.Char(compute=_compute_pub_cust_domain, readonly=True, store=False)
    customer_contact = fields.Many2one('res.partner', 'Payer Contact Person', domain=[('is_customer', '=', True)])
    advertising = fields.Boolean('Advertising', default=False)

    # TODO: Check [START]
    agency_is_publish = fields.Boolean('Agency is Publishing Customer', default=False)
    opportunity_subject = fields.Char('Opportunity Subject', size=64,
                                      help="Subject of Opportunity from which this Sales Order is derived.")


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

    # --added deep
    def action_refuse(self):
        orders = self.filtered(lambda s: s.state in ['submitted', 'sale', 'sent', 'approved1'])
        orders.write({'state':'draft'})
        return True

    def action_cancel(self):
        for order in self.filtered(lambda s: s.state == 'sale' and s.advertising):
            for line in order.order_line:
                line.page_qty_check_unlink()
        return super(SaleOrder, self).action_cancel()

    def action_confirm(self):
        # FIXME: This logic is no longer needed: To Refactor
        # FIXME: Logic 1: Multi line creation
        # FIXME: Logic 2: Page Qty check: NTD

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
        return super(SaleOrder, self).action_confirm()

    @api.model
    def create(self, vals):
        # FIXME: custom Warn block?
        if vals.get('partner_id', False):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            if partner.sale_warn == 'block':
                raise UserError(_(partner.sale_warn_msg))

        result = super(SaleOrder, self).create(vals)

        # multi-split only works with order.create not order_line.create,
        # due to removing old one and creating new ones
        olines = []
        for line in result.order_line:
            if line.multi_line:
                olines.append(line.id)
                continue
        if not olines == []:
            self.env['sale.order.line.create.multi.lines'].create_multi_from_order_lines(
                orderlines=olines, orders=result)
        return result

    def write(self, vals):
        result = super(SaleOrder, self).write(vals)

        for order in self:
            olines = []
            for line in order.order_line:
                if line.multi_line:
                    olines.append(line.id)
                    continue
            if not olines == []:
                list = self.env['sale.order.line.create.multi.lines'].create_multi_from_order_lines(
                    orderlines=olines, orders=order)
                newlines = self.env['sale.order.line'].browse(list)
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


    def action_quotation_send(self):
        '''
        This function opens a window to compose an email, with the edi sale template message
        loaded by default
        '''
        # FIXME: Fintune

        self.ensure_one()
        if not self.advertising:
            return super(SaleOrder, self).action_quotation_send()

        # FIXME: Multi line split: seems unnecessary here!
        elif self.state in ['draft', 'approved1', 'submitted']:
            olines = []
            for line in self.order_line:
                if line.multi_line:
                    olines.append(line.id)
            if not olines == []:
                self.env['sale.order.line.create.multi.lines'].create_multi_from_order_lines(orderlines=olines,
                                                                                             orders=self)
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

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model
    def _get_adClass_domain(self):
        if not self.medium:
            return [('id','child_of', self.env.ref('sale_advertising_order.advertising_category', raise_if_not_found=False).id)]

        return [('id','child_of', self.medium.id), ('id', '!=', self.medium.id)]


    @api.depends('ad_class')
    def _compute_tags_domain(self):
        """
        Compute the domain for the Pageclass domain.
        """
        # FIXME: Check
        for rec in self:
            rec.page_class_domain = json.dumps(
                [('id', 'in', rec.ad_class.tag_ids.ids)]
            )

    @api.depends('product_id')
    def _get_product_data(self):
        for line in self:
            prod = line.product_id
            line.product_width = prod.width or 0.0
            line.product_height = prod.height or 0.0


    @api.depends('adv_issue_ids')
    def _compute_Issuedt(self):
        """ Compute the Issue date """
        for line in self.filtered('advertising'):
            # First advIssue's date
            line.issue_date = line.adv_issue_ids and line.adv_issue_ids[0].issue_date or False


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

    mig_remark = fields.Text('Migration Remark') # FIXME: Remove?
    layout_remark = fields.Text('Material Remark') # FIXME: Rename?
    page_class_domain = fields.Char(compute='_compute_tags_domain', readonly=True, store=False,) #FIXME ?

    advertising = fields.Boolean(related='order_id.advertising', string='Advertising', store=True)

    medium = fields.Many2one('product.category', string='Medium')
    title = fields.Many2one('sale.advertising.issue', 'Title', domain=[('child_ids','<>', False)])
    title_ids = fields.Many2many('sale.advertising.issue', 'sale_order_line_adv_issue_title_rel', 'order_line_id', 'adv_issue_id', 'Titles')
    adv_issue = fields.Many2one('sale.advertising.issue', 'Advertising Issue')
    adv_issue_ids = fields.Many2many('sale.advertising.issue','sale_order_line_adv_issue_rel', 'order_line_id', 'adv_issue_id',  'Advertising Issues')

    ad_class = fields.Many2one('product.category', 'Advertising Class', domain=_get_adClass_domain)
    issue_date = fields.Date(compute='_compute_Issuedt', string='Issue Date', store=True)
    date_type = fields.Selection(related='ad_class.date_type', type='selection', readonly=True)
    # issue_product_ids = fields.One2many('sale.order.line.issues.products', 'order_line_id',
    #                                     'Adv. Issues with Product Prices') #TODO

    deadline_passed = fields.Boolean(compute='_compute_deadline', string='Deadline Passed', store=False)
    deadline = fields.Datetime(compute='_compute_deadline', string='Deadline', store=False)
    deadline_offset = fields.Datetime(compute='_compute_deadline', store=False)

    product_template_id = fields.Many2one('product.template', string='Product', domain=[('sale_ok', '=', True)],
                                 change_default=True, ondelete='restrict')
    domain4prod_ids = fields.Many2many('product.template', string='Domain for Product Template',
                                       compute=_get_prodTemplate2filter)

    page_reference = fields.Char('Page Preference', size=32)
    ad_number = fields.Char('External Reference', size=50)
    url_to_material = fields.Char('URL Material')
    from_date = fields.Date('Start of Validity')
    to_date = fields.Date('End of Validity')

    multi_line = fields.Boolean(string='Multi Line')
    multi_line_number = fields.Integer(compute='_multi_price', string='Number of Lines', store=True)

    order_partner_id = fields.Many2one(related='order_id.partner_id', string='Customer', store=True)
    order_advertiser_id = fields.Many2one(related='order_id.published_customer',
                                          string='Advertising Customer', store=True)
    order_agency_id = fields.Many2one(related='order_id.advertising_agency',
                                          string='Advertising Agency', store=True)
    order_pricelist_id = fields.Many2one(related='order_id.pricelist_id', string='Pricelist')

    price_unit_dummy = fields.Float(related='price_unit', string='Unit Price', readonly=True)
    actual_unit_price = fields.Float(compute='_compute_amount', string='Actual Unit Price', digits='Product Price',
                                     default=0.0, readonly=True)
    comb_list_price = fields.Monetary(compute='_multi_price', string='Combined_List Price', default=0.0, store=True,
                                      digits='Account')
    computed_discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    subtotal_before_agency_disc = fields.Monetary(string='Subtotal before Commission', digits='Account')
    price_edit = fields.Boolean(compute='_compute_price_edit', string='Price Editable')

    discount_reason_id = fields.Many2one('discount.reason', 'Discount Reason', ondelete='restrict')

    proof_number_payer = fields.Boolean('Proof Number Payer', default=False)
    proof_number_payer_id = fields.Many2one('res.partner', 'Proof Number Payer ID')
    proof_number_adv_customer = fields.Many2many('res.partner', 'partner_line_proof_rel', 'line_id', 'partner_id',
                                                 string='Proof Number Advertising Customer')
    proof_number_amt_payer = fields.Integer('Proof Number Amount Payer', default=1)
    proof_number_amt_adv_customer = fields.Integer('Proof Number Amount Advertising', default=1)

    product_width = fields.Float(compute='_get_product_data', readonly=True, store=True, string="Width")
    product_height = fields.Float(compute='_get_product_data', readonly=True, store=True, string="Height")
