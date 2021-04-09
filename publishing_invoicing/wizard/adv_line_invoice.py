from odoo import api, fields, models, _

class AdOrderLineMakeInvoice(models.TransientModel):
    _inherit = "ad.order.line.make.invoice"
    _description = "Advertising Order Line Make_invoice"

    def modify_key(self, key, keydict, line):
        key, keydict = super(AdOrderLineMakeInvoice, self).modify_key(key, keydict, line)
        key = list(key)
        if line.order_id.invoicing_property_id.group_by_order:
            key.append(line.order_id)
        key = tuple(key)
        keydict['customer_contact_id'] = line.order_id.customer_contact
        return key, keydict