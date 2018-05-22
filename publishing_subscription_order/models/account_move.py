# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    start_date = fields.Date('Start Date', index=True)
    end_date = fields.Date('End Date', index=True)

    @api.multi
    @api.constrains('start_date', 'end_date')
    def _check_start_end_dates(self):
        for moveline in self:
            if moveline.start_date and not moveline.end_date:
                raise ValidationError(
                    _("Missing End Date for move line with Name '%s'.")
                    % (moveline.name))
            if moveline.end_date and not moveline.start_date:
                raise ValidationError(
                    _("Missing Start Date for move line with Name '%s'.")
                    % (moveline.name))
            if moveline.end_date and moveline.start_date and \
                    moveline.start_date > moveline.end_date:
                raise ValidationError(_(
                    "Start Date should be before End Date for move line "
                    "with Name '%s'.")
                    % (moveline.name))
