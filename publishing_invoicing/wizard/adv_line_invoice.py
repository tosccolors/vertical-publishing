from odoo import api, fields, models, _
# from odoo.addons.queue_job.job import job, related_action
from odoo.addons.queue_job.exception import FailedJobError
from odoo.exceptions import UserError, ValidationError

class AdOrderLineMakeInvoice(models.TransientModel):
    _inherit = "ad.order.line.make.invoice"
    _description = "Advertising Order Line Make_invoice"

    def modify_key(self, key, keydict, line):
        key, keydict = super(AdOrderLineMakeInvoice, self).modify_key(key, keydict, line)
        key = list(key)
        if line.order_id.invoicing_property_id.group_by_order:
            key.append(line.order_id)
        key = tuple(key)
        return key, keydict

    # @job
    def make_invoices_job_queue(self, inv_date, post_date, chunk):
        """"Filter out lines with invoicing properties pay in terms or invoice as package deal"""
        ctx = self._context
        dropids = []
        if not ctx.get('invoice_from_order'):
            for line in chunk:
                if line.invoicing_property_id.inv_package_deal or line.invoicing_property_id.pay_in_terms \
                        or line.invoicing_property_id.inv_manually:
                    dropids.append(line.id)
        chunk = chunk.filtered(lambda r: r.id not in dropids)
        if not chunk:
            raise UserError(_('Only order lines are selected which should be invoiced at order level.'))
        return super(AdOrderLineMakeInvoice, self).make_invoices_job_queue(inv_date, post_date, chunk)

class AdOrderMakeInvoice(models.TransientModel):
    _inherit = "ad.order.make.invoice"

    def make_invoices_from_ad_orders(self):
        ctx = self._context.copy()
        ctx.update({'invoice_from_order': True})
        self = self.with_context(ctx)
        return super(AdOrderMakeInvoice, self).make_invoices_from_ad_orders()