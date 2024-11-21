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


    # @api.depends('agency_is_publish')
    # def _compute_pub_cust_domain(self):
    #     """
    #     Compute the domain for the published_customer domain.
    #     """
    #     for rec in self:
    #         rec.pub_cust_domain = [('is_ad_agency', '=', True)] #json.dumps([('is_ad_agency', '=', True)])
    #         # if rec.agency_is_publish:
    #         #     rec.pub_cust_domain = json.dumps(
    #         #         [('is_ad_agency', '=', True), ('parent_id', '=', False), ('is_customer', '=', True)]
    #         #     )
    #         # else:
    #         #     rec.pub_cust_domain = json.dumps(
    #         #         [('is_ad_agency', '!=', True),('parent_id', '=', False), ('is_customer', '=', True)]
    #         #     )

    # backported:
    amount_by_group = fields.Binary(string="Tax amount by group", compute='_amount_by_group',
                                    help="type: [(name, amount, base, formated amount, formated base)]")

    # overridden:
    state = fields.Selection(selection=[
        ('draft', 'Draft Quotation'),
        ('sent', 'Quotation Sent'),
        ('submitted', 'Submitted for Approval'),
        ('approved1', 'Approved by Sales Mgr'),
        ('sale', "Sales Order"),
        ('done', "Locked"),
        ('cancel', "Cancelled"),
        ])

    # new:
    # pub_cust_domain = fields.Char(compute=_compute_pub_cust_domain, readonly=True, store=False)  -- deprecated
    published_customer = fields.Many2one('res.partner', 'Advertiser', domain=[('parent_id', '=', False), ('is_customer', '=', True)])
    advertising_agency = fields.Many2one('res.partner', 'Advertising Agency', domain=[('is_customer', '=', True)])
    nett_nett = fields.Boolean('Netto Netto Deal', default=False)
    customer_contact = fields.Many2one('res.partner', 'Contact Person', domain=[('is_customer', '=', True)])
    advertising = fields.Boolean('Advertising', default=False)

    agency_is_publish = fields.Boolean('Agency is Publishing Customer?', default=False)
    partner_acc_mgr = fields.Many2one(related='published_customer.user_id',
                                      string='Account Manager', store=True, readonly=True)
    display_discount_to_customer = fields.Boolean("Display Discount", default=False) # TODO: take action later


    #Overridden: SOT
    type_id = fields.Many2one(
        comodel_name="sale.order.type",
        string="Type",
        compute="_compute_sale_type_id",
        store=True,
        readonly=True,
        states={"draft": [("readonly", False)],},
        ondelete="restrict",
        copy=True,
        check_company=True, tracking=True
    )


    @api.depends("partner_id", "company_id")
    def _compute_sale_type_id(self):

        AdsSOT = self.env.ref('sale_advertising_order.ads_sale_type').id
        defSOT = self._context.get('default_type_id', False)

        for record in self:
            sale_type = False

            # Enforce
            if record.advertising or (defSOT == AdsSOT):
                sale_type = AdsSOT
            # else:
            #     # Specific partner sale type value
            #     sale_type = (
            #         record.partner_id.with_company(record.company_id).sale_type
            #         or record.partner_id.commercial_partner_id.with_company(
            #             record.company_id
            #         ).sale_type
            #     )

            # Default user sale type value
            if not sale_type:
                sale_type = record.default_get(["type_id"]).get("type_id", False)

            # Get first sale type value
            if not sale_type:
                sale_type = record._default_type_id()
            record.type_id = sale_type


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


    @api.onchange('agency_is_publish')
    def _onchange_agencyIspublish(self):
        if self.agency_is_publish:
            self.published_customer = False


    @api.onchange('advertising_agency')
    def _onchange_advertiser(self):
        if self.advertising_agency:
            self.partner_id = self.advertising_agency

    @api.onchange('partner_id')
    def _onchange_partner2(self):
        if not self.partner_id:
            self.customer_contact = False

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

        self.customer_contact = contact_id

        # Existing SAO orderlines
        if self.order_line and self.advertising:
            warning = {'title': _('Warning'),
                       'message': _('Changing the Customer can have a change in Agency Discount as a result.'
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

        # for order in self.filtered('advertising'):
        #     olines = []
        #     for line in order.order_line:
        #         if line.multi_line:
        #             olines.append(line.id)
        #         else:
        #             if line.deadline_check():
        #                 line.page_qty_check_create()
        #     if not olines == []:
        #         list = self.env['sale.order.line.create.multi.lines'].create_multi_from_order_lines(
        #             orderlines=olines, orders=order)
        #         newlines = self.env['sale.order.line'].browse(list)
        #         for newline in newlines:
        #             if newline.deadline_check():
        #                 newline.page_qty_check_create()
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
            invoice_vals['published_customer'] = self.published_customer.id

        # Generic
        invoice_vals['customer_contact'] = self.customer_contact.id
        return invoice_vals


    def _get_name_quotation_report(self):
        self.ensure_one()
        ref = self.env.ref
        template = 'sale.report_saleorder_document'

        if self.type_id.id == ref('sale_advertising_order.ads_sale_type').id:
            template = 'sale_advertising_order.report_saleorder_document_sao'

        return template


    # Backported
    def _amount_by_group(self):
        """ ported from v14, for backward compatibility
        """

        # Advertising Orders Only:
        for order in self.filtered('advertising'):
            currency = order.currency_id or order.company_id.currency_id
            fmt = partial(formatLang, self.with_context(lang=order.partner_id.lang).env, currency_obj=currency)
            res = {}
            for line in order.order_line:
                discount = 0.0
                # At this point, it will always be Single Edition:
                nn = True if order.nett_nett or line.nett_nett else False
                if order.partner_id.is_ad_agency and not nn:
                    discount = order.partner_id.agency_discount

                price_reduce = line.actual_unit_price * (1.0 - discount / 100.0)

                taxes = line.tax_id.compute_all(price_reduce, quantity=line.product_uom_qty, product=line.product_id, partner=order.partner_shipping_id)['taxes']
                for tax in line.tax_id:
                    group = tax.tax_group_id
                    res.setdefault(group, {'amount': 0.0, 'base': 0.0})
                    for t in taxes:
                        if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
                            res[group]['amount'] += t['amount']
                            res[group]['base'] += t['base']
            res = sorted(res.items(), key=lambda l: l[0].sequence)

            # round amount and prevent -0.00
            for group_data in res:
                group_data[1]['amount'] = currency.round(group_data[1]['amount']) + 0.0
                group_data[1]['base'] = currency.round(group_data[1]['base']) + 0.0

            order.amount_by_group = [(
                l[0].name, l[1]['amount'], l[1]['base'],
                fmt(l[1]['amount']), fmt(l[1]['base']),
                len(res),
            ) for l in res]


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
        # elif self.state in ['draft', 'approved1', 'submitted']:
        #     olines = []
        #     for line in self.order_line:
        #         if line.multi_line:
        #             olines.append(line.id)
        #     if not olines == []:
        #         self.env['sale.order.line.create.multi.lines'].create_multi_from_order_lines(orderlines=olines,
        #                                                                                      orders=self)
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

    @api.depends('product_uom_qty', 'order_id.partner_id', 'order_id.nett_nett', 'nett_nett',
                 'subtotal_before_agency_disc',
                 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        super(SaleOrderLine, self.filtered(lambda record: record.advertising != True))._compute_amount()
        precision = self.env['decimal.precision'].precision_get('Product Price') or 4

        for line in self.filtered('advertising'):
            nn = True if line.order_id.nett_nett or line.nett_nett else False
            comp_discount = line.computed_discount or 0.0
            price_unit = line.price_unit or 0.0
            unit_price = line.actual_unit_price or 0.0
            qty = line.product_uom_qty or 0.0
            csa = 0.0  # line.color_surcharge_amount or 0.0 -- deprecated
            subtotal_bad = line.subtotal_before_agency_disc or 0.0
            if line.order_id.partner_id.is_ad_agency and not nn:
                discount = line.order_id.partner_id.agency_discount
            else:
                discount = 0.0

            # Single Edition:
            if not line.multi_line:
                if price_unit == 0.0:
                    # unit_price = csa
                    unit_price = 0.0
                    comp_discount = 0.0
                elif price_unit > 0.0 and qty > 0.0:
                    comp_discount = round((1.0 - float(subtotal_bad) / (float(price_unit) * float(qty))) * 100.0, 5)
                    unit_price = round(float(price_unit) * (1 - float(comp_discount) / 100), precision)

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

    @api.depends('title', 'product_template_id')
    def _compute_price_edit(self):
        """
        Compute if price_unit should be editable.
        """
        for line in self.filtered('advertising'):
            line.price_edit = False
            if line.product_template_id and line.product_template_id.price_edit or line.title.price_edit:
                line.price_edit = True


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

    mig_remark = fields.Text('Migration Remark')
    layout_remark = fields.Text('Material Remark')
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
    issue_product_ids = fields.One2many('sale.order.line.issues.products', 'order_line_id',
                                        'Adv. Issues with Product Prices')

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
    partner_acc_mgr = fields.Many2one(related='order_id.partner_acc_mgr', store=True, string='Account Manager',
                                      readonly=True)

    price_unit_dummy = fields.Float(related='price_unit', string='Unit Price', readonly=True)
    actual_unit_price = fields.Float(compute='_compute_amount', string='Actual Unit Price', digits='Product Price',
                                     default=0.0, readonly=True)
    comb_list_price = fields.Monetary(compute='_multi_price', string='Combined_List Price', default=0.0, store=True,
                                      digits='Account')
    computed_discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    subtotal_before_agency_disc = fields.Monetary(string='Subtotal before Commission', digits='Account')
    price_edit = fields.Boolean(compute='_compute_price_edit', string='Price Editable')

    nett_nett = fields.Boolean(string='Netto Netto Line')
    discount_reason_id = fields.Many2one('discount.reason', 'Discount Reason', ondelete='restrict')

    proof_number_payer = fields.Boolean('Proof Number Payer', default=False)
    proof_number_payer_id = fields.Many2one('res.partner', 'Proof Number Payer ID')
    proof_number_adv_customer = fields.Many2many('res.partner', 'partner_line_proof_rel', 'line_id', 'partner_id',
                                                 string='Proof Number Advertising Customer')
    proof_number_amt_payer = fields.Integer('Proof Number Amount Payer', default=1)
    proof_number_amt_adv_customer = fields.Integer('Proof Number Amount Advertising', default=1)

    product_width = fields.Float(compute='_get_product_data', readonly=True, store=True, string="Width")
    product_height = fields.Float(compute='_get_product_data', readonly=True, store=True, string="Height")


    @api.model
    def default_get(self, fields_list):
        result = super(SaleOrderLine, self).default_get(fields_list)
        if 'customer_contact' in self.env.context:
            result.update({'proof_number_payer_id': self.env.context['customer_contact']})
            result.update({'proof_number_amt_payer': 1})

        result.update({'proof_number_adv_customer': False})
        result.update({'proof_number_amt_adv_customer': 0})
        return result

    @api.onchange('medium')
    def onchange_medium(self):
        vals, data, result = {}, {}, {}
        if not self.advertising:
            return {'value': vals}
        if self.medium:
            child_id = [(x.id != self.medium.id) and x.id for x in self.medium.child_id]

            if len(child_id) == 1:
                vals['ad_class'] = child_id[0]
            else:
                vals['ad_class'] = False
                data = {'ad_class': [('id', 'child_of', self.medium.id), ('id', '!=', self.medium.id)]}
            titles = self.env['sale.advertising.issue'].search(
                [('parent_id', '=', False), ('medium', 'child_of', self.medium.id)]).ids
            if titles and len(titles) == 1:
                vals['title'] = titles[0]
                vals['title_ids'] = [(6, 0, titles)]
            else:
                vals['title'] = False
                vals['title_ids'] = [(6, 0, [])]
        else:
            vals['ad_class'] = False
            vals['title'] = False
            vals['title_ids'] = [(6, 0, [])]
            data = {'ad_class': []}
        return {'value': vals, 'domain': data}

    @api.onchange('ad_class')
    def onchange_ad_class(self):
        vals, data, result = {}, {}, {}
        if not self.advertising:
            return {'value': vals}

        # Reset
        if not self.ad_class:
            self.product_template_id = False

    @api.onchange('title', 'title_ids')
    def onchange_title(self):
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

        elif len(self.title_ids) > 1:  # Multi Titles:
            self.title = False

        # Multi Titles & Multi Editions:
        if self.title_ids and self.adv_issue_ids:
            titles = self.title_ids.ids
            issue_ids = self.adv_issue_ids.ids
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', issue_ids)])
            issue_parent_ids = [x.parent_id.id for x in adv_issues]
            for title in titles:
                if not (title in issue_parent_ids):
                    raise UserError(_('Not for every selected Title an Issue is selected.'))

        elif self.title_ids and self.issue_product_ids:
            titles = self.title_ids.ids
            adv_issues = self.env['sale.advertising.issue'].search(
                [('id', 'in', [x.adv_issue_id.id for x in self.issue_product_ids])])
            issue_parent_ids = [x.parent_id.id for x in adv_issues]
            back = False
            for title in titles:
                if not (title in issue_parent_ids):
                    back = True
                    break
            if back:
                self.adv_issue_ids = [(6, 0, adv_issues.ids)]
                self.issue_product_ids = [(6, 0, [])]
            self.titles_issues_products_price()

        elif self.title_ids:
            self.product_template_id = False
            self.product_id = False
        else:
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
        if not self.product_template_id:
            self.issue_product_ids = [(6, 0, [])]

        if self.title_ids and (len(self.adv_issue_ids) == 0):
            raise UserError(_('Please select Advertising Issue(s) to proceed further.'))

        if self.product_template_id and self.adv_issue_ids and len(self.adv_issue_ids) > 1:
            self.product_uom = self.product_template_id.uom_id
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', self.adv_issue_ids.ids)])
            values = []
            self.issue_product_ids = []  # reset
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
                        [('product_tmpl_id', '=', self.product_template_id.id),
                         ('product_template_attribute_value_ids.product_attribute_value_id', '=', pav)])
                    if product_id:
                        self.product_id = product_id.id
                        product = product_id.with_context(
                            lang=self.order_id.partner_id.lang,
                            partner=self.order_id.partner_id.id,
                            quantity=self.product_uom_qty,
                            date=self.order_id.date_order,
                            pricelist=self.order_id.pricelist_id.id,
                            uom=self.product_uom.id
                        )
                        # TODO: Verify w/ all cases
                        # if self.order_id.pricelist_id and self.order_id.partner_id:
                        #     value['product_id'] = product_id.id
                        #     value['adv_issue_id'] = adv_issue.id
                        #     value['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                        #         self._get_display_price(), product.taxes_id, self.tax_id,
                        #         self.company_id)
                        #
                        #     price += value['price_unit'] * self.product_uom_qty
                        #     values.append((0, 0, value))

                        value['product_id'] = product_id.id
                        value['adv_issue_id'] = adv_issue.id
                        self = self.with_company(self.company_id)
                        price = self._get_display_price()
                        value['price_unit'] = product._get_tax_included_unit_price_from_price(
                            price,
                            self.currency_id or self.order_id.currency_id,
                            product_taxes=self.product_id.taxes_id.filtered(
                                lambda tax: tax.company_id == self.env.company
                            ),
                            fiscal_position=self.order_id.fiscal_position_id,
                        )

                        price += value['price_unit'] * self.product_uom_qty
                        values.append((0, 0, value))

            if product_id:
                self.update({
                    'issue_product_ids': values,
                    # 'product_id': product_id.id, # FIXME
                    'multi_line_number': issues_count,
                    'multi_line': True,
                })
            self.comb_list_price = price
            self.subtotal_before_agency_disc = price

        # Issue Products
        elif self.product_template_id and self.issue_product_ids and len(self.issue_product_ids) > 1:
            self.product_uom = self.product_template_id.uom_id
            adv_issues = self.env['sale.advertising.issue'].search(
                [('id', 'in', [x.adv_issue_id.id for x in self.issue_product_ids])])
            values = []
            self.issue_product_ids = []  # reset
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
                        [('product_tmpl_id', '=', self.product_template_id.id),
                         ('product_template_attribute_value_ids.product_attribute_value_id', '=', pav)])
                    if product_id:
                        self.product_id = product_id.id
                        product = product_id.with_context(
                            lang=self.order_id.partner_id.lang,
                            partner=self.order_id.partner_id.id,
                            quantity=self.product_uom_qty,
                            date=self.order_id.date_order,
                            pricelist=self.order_id.pricelist_id.id,
                            uom=self.product_uom.id
                        )
                        # TODO: Verify w/ all cases
                        # if self.order_id.pricelist_id and self.order_id.partner_id:
                        #     value['product_id'] = product_id.id
                        #     value['adv_issue_id'] = adv_issue.id
                        #     value['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                        #         self._get_display_price(), product.taxes_id, self.tax_id,
                        #         self.company_id)
                        #
                        #     price += value['price_unit'] * self.product_uom_qty
                        #     values.append((0, 0, value))

                        value['product_id'] = product_id.id
                        value['adv_issue_id'] = adv_issue.id
                        self = self.with_company(self.company_id)
                        price = self._get_display_price()
                        value['price_unit'] = product._get_tax_included_unit_price_from_price(
                            price,
                            self.currency_id or self.order_id.currency_id,
                            product_taxes=self.product_id.taxes_id.filtered(
                                lambda tax: tax.company_id == self.env.company
                            ),
                            fiscal_position=self.order_id.fiscal_position_id,
                        )

                        price += value['price_unit'] * self.product_uom_qty
                        values.append((0, 0, value))
            if product_id:
                self.update({
                    'issue_product_ids': values,
                    # 'product_id': product_id.id,
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
                    [('product_tmpl_id', '=', self.product_template_id.id),
                     ('product_template_attribute_value_ids.product_attribute_value_id', '=', pav)])
                if product_id:
                    self.product_id = product_id.id
                    self.update({
                        # 'issue_product_ids': [(6, 0, [])], # FIXME: Need this?
                        # 'product_id': product_id.id, FIXME
                        'multi_line_number': 1,
                        'multi_line': False,
                    })

    @api.onchange('product_id')
    def product_id_change(self):
        if not self.advertising:
            return
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

    @api.onchange('date_type')
    def onchange_date_type(self):
        if not self.advertising:
            return

        if self.date_type == 'validity':
            self.adv_issue_ids = [(6, 0, [])]

        elif self.date_type == 'issue_date':
            self.from_date = self.issue_date
            self.to_date = self.issue_date

    @api.onchange('price_unit')
    def onchange_price_unit(self):
        stprice = 0
        if not self.advertising: return
        if self.price_unit > 0 and self.product_uom_qty > 0:
            stprice = self.price_unit * self.product_uom_qty

        self.subtotal_before_agency_disc = stprice

    @api.onchange('computed_discount')
    def onchange_actualcd(self):
        result = {}
        if not self.advertising:
            return {'value': result}
        comp_discount = self.computed_discount
        if comp_discount < 0.0:
            comp_discount = self.computed_discount = 0.000
        if comp_discount > 100.0:
            comp_discount = self.computed_discount = 100.0
        price = self.price_unit or 0.0
        fraction_param = int(self.env['ir.config_parameter'].sudo().get_param('sale_advertising_order.fraction'))

        if self.multi_line:
            clp = self.comb_list_price or 0.0

            fraction = float(clp) / fraction_param
            subtotal_bad = round(float(clp) * (1.0 - float(comp_discount) / 100.0), 2)

        # Single Edition:
        else:
            gross_price = float(price) * float(self.product_uom_qty)
            fraction = gross_price / fraction_param
            subtotal_bad = round(float(gross_price) * (1.0 - float(comp_discount) / 100.0), 2)

        if self.subtotal_before_agency_disc == 0 or (self.subtotal_before_agency_disc > 0 and
                                                     abs(float(subtotal_bad) - float(
                                                         self.subtotal_before_agency_disc)) > fraction):
            result['subtotal_before_agency_disc'] = subtotal_bad
        return {'value': result}

    @api.onchange('product_uom_qty', 'comb_list_price')
    def onchange_actualqty(self):
        if not self.advertising: return

        if not self.multi_line:
            self.subtotal_before_agency_disc = round(
                float(self.price_unit) *
                float(self.product_uom_qty) * float(1.0 - self.computed_discount / 100.0), 2)
        else:
            self.subtotal_before_agency_disc = round(float(self.comb_list_price), 2)

    @api.onchange('adv_issue_ids', 'issue_product_ids')
    def onchange_getQty(self):
        if not self.advertising: return
        ml_qty = 0
        ai = False  # self.adv_issue
        ais = self.adv_issue_ids
        # ds = self.dates  # FIXME: deprecated
        iis = self.issue_product_ids
        user = self.env['res.users'].browse(self.env.uid)

        # Multi Titles & Multi Editions:
        if self.title_ids and ais:
            titles = self.title_ids.ids
            issue_ids = ais.ids
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', issue_ids)])
            issue_parent_ids = [x.parent_id.id for x in adv_issues]
            for title in titles:
                if not (title in issue_parent_ids):
                    raise UserError(_('Not for every selected Title an Issue is selected.'))

        # consider 1st Issue (as Single Edition) for computation
        if len(ais) == 1:
            ai = self.adv_issue_ids.ids[0]

        # Force assign 1st Issue, always
        if ais:
            self.adv_issue = self.adv_issue_ids.ids[0]
        else:
            self.adv_issue = False

        if ais:
            if len(ais) > 1:
                ml_qty = len(ais)
                ai = False
            else:
                ai = ais.id
                ais = [(6, 0, [])]
                ml_qty = 1
        elif ai:
            ml_qty = 1
        # elif ds:  # FIXME: deprecated
        #     if len(ds) >= 1:
        #         ml_qty = 1
        #         self.product_uom_qty = len(ds)
        elif iis:
            if len(iis) > 1:
                ml_qty = len(iis)
        if ml_qty > 1:
            self.multi_line = True
        else:
            self.multi_line = False
        self.multi_line_number = ml_qty
        # Reset
        if len(self.adv_issue_ids) > 1 and not self.issue_product_ids:
            self.product_template_id = False

        if user.has_group('sale_advertising_order.group_no_deadline_check'):
            return {}
        for adv_issue in self.adv_issue_ids:
            if adv_issue.deadline and fields.Datetime.from_string(adv_issue.deadline) < datetime.now():
                warning = {'title': _('Warning'),
                           'message': _('You are adding an advertising issue after deadline. '
                                        'Are you sure about this?')}
                return {'warning': warning}

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

    @api.constrains('title_ids', 'adv_issue_ids')
    def _validate_AdvIssues(self):
        "Check if Issues for every Titles"
        for case in self:
            if len(case.title_ids.ids) > 0 and len(case.adv_issue_ids.ids) > 0:
                issue_parent_ids = [x.parent_id.id for x in case.adv_issue_ids]
                for title in case.title_ids.ids:
                    if not (title in issue_parent_ids):
                        raise ValidationError(
                            _("Not for every selected Title an Issue is selected.")
                            % (case.name))

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

    def deadline_check(self):
        self.ensure_one()
        user = self.env['res.users'].browse(self.env.uid)
        issue_date = (self.issue_date or self.adv_issue_ids[0].issue_date) \
            if len(self.adv_issue_ids) == 1 else self.issue_date
        if issue_date and fields.Datetime.from_string(issue_date) <= datetime.now():
            return False
        elif not user.has_group('sale_advertising_order.group_no_deadline_check') and self.deadline:
            if fields.Datetime.from_string(self.deadline) < datetime.now():
                raise UserError(_('The deadline %s for this Category/Advertising Issue has passed.') % (
                    self.deadline))
        return True

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        if self.advertising:
            # res['analytic_account_id'] = self.adv_issue.analytic_account_id.id #FIXME
            res['so_line_id'] = self.id
            res['price_unit'] = self.actual_unit_price
            res['ad_number'] = self.ad_number
            res['computed_discount'] = self.computed_discount # FIXME: Need this?
        else:
            res['so_line_id'] = self.id

        return res

    # FIXME:
    # TODO: Create, Write & Unlink ==> Seems unnecessary: Need to check all cases to validate the same

class OrderLineAdvIssuesProducts(models.Model):
    _name = "sale.order.line.issues.products"
    _description = "Advertising Order Line Advertising Issues"
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
    adv_issue_id = fields.Many2one('sale.advertising.issue', 'Issue', ondelete='cascade', index=True, readonly=True,
                                   required=True)
    product_attribute_value_id = fields.Many2one(related='adv_issue_id.parent_id.product_attribute_value_id',
                                                 relation='sale.advertising.issue',
                                                 string='Title', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', ondelete='cascade', index=True, readonly=True)
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0, readonly=True)
    price_edit = fields.Boolean(compute=_compute_price_edit, readonly=True)
    qty = fields.Float(related='order_line_id.product_uom_qty', readonly=True)
    price = fields.Float(compute='_compute_price', string='Price', readonly=True, required=True, digits='Product Price',
                         default=0.0)
    page_reference = fields.Char('Reference of the Page', size=64)
    ad_number = fields.Char('External Reference', size=50)
    url_to_material = fields.Char('URL Material', size=64)

