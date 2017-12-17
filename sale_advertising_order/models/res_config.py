# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2015 Magnus 
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp


class Partner(models.Model):
    _inherit = 'res.partner'

    agency_discount = fields.Float('Agency Discount (%)', digits=(16, 2), default=0.0)
    is_ad_agency = fields.Boolean('Agency', default=False)
    coc_nr = fields.Char('Chamber of Commerce id', size=64, help="Customer CoC number" )



class Company(models.Model):
    _inherit = 'res.company'

    verify_order_setting = fields.Float('Order Amount bigger than', digits=dp.get_precision('Account'))
    verify_discount_setting = fields.Float('Discount (%) bigger than', digits=(16, 2))


    @api.multi
    def write(self, vals):
        res = super(Company, self).write(vals)

        # -- deep
        # Functionality for updating "Verification Treshold" in SO are split b/w Company & Sale Object

        if 'verify_order_setting' in vals or 'verify_discount_setting' in vals:
            for case in self:
                treshold = case.verify_order_setting
                maxdiscount = case.verify_discount_setting
                self._cr.execute("""
                         UPDATE sale_order
                         SET ver_tr_exc=True
                         WHERE (amount_untaxed > %s
                         OR max_discount > %s)
                         AND company_id= %s
                         AND advertising=True
                         AND state!='done';
            
                         UPDATE sale_order
                         SET ver_tr_exc=False
                         WHERE amount_untaxed <= %s
                         AND company_id= %s
                         AND advertising=True
                         AND max_discount <= %s
                         AND state!='done'
                         """, (treshold, maxdiscount, case.id,  treshold, case.id, maxdiscount )
                )


        return res




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
