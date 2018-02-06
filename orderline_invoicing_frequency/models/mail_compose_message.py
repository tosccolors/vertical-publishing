# -*- coding: utf-8 -*-
from odoo import _, api, fields, models, SUPERUSER_ID, tools
from datetime import date

class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        res = super(MailComposer, self).send_mail()
        ctx = self.env.context.copy()
        if 'invoice_mass_mail' in ctx and ctx['invoice_mass_mail'] == True:
            inv_ids = []
            if 'active_model' in ctx and ctx['active_model'] == 'account.invoice':
                for invoice_obj in self.env['account.invoice'].browse(ctx['active_ids']):
                    if invoice_obj.transmit_method_code:
                        transmit_code = invoice_obj.transmit_method_code.strip().lower()
                        if transmit_code == 'mail':
                            invoice_obj.partner_id.last_invoice_sent_date = date.today()
        return res

