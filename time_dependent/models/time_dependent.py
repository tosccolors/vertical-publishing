# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta

class TimeDependent(models.AbstractModel):
    _name = 'time.dependent'

    @api.multi
    def write(self, values):
        for rec in self:
            time_dependent_model_rec = rec.env['time.dependent.model'].search([('model_id.model', '=', rec._name)])
            if time_dependent_model_rec:
                #Check validation period
                validation_from = values.get('date_start', False)
                validation_to = values.get('date_end', False)
                if not validation_from and not values.has_key('date_start'):
                    validation_from = rec.env[rec._name].browse(rec.id).date_start
                if not validation_to and not values.has_key('date_end'):
                    validation_to = rec.env[rec._name].browse(rec.id).date_end
                if not ((validation_to and datetime.strptime(validation_to, "%Y-%m-%d").date() < date.today()) or (validation_from and datetime.strptime(validation_from, "%Y-%m-%d").date() > date.today()) or (not validation_from and not validation_to)):
                    tracking_vals = []
                    for field in time_dependent_model_rec.field_ids:
                        #Capture changes if selected field's value is changed.
                        if values.has_key(field.name):
                            field_dict = rec.read([field.name])[0]
                            if field.ttype == 'boolean':
                                old_value = field_dict.get(field.name, False)
                                new_value = values.get(field.name, False)
                            elif field.ttype == 'integer' or field.ttype == 'float':
                                old_value = field_dict.get(field.name) if field_dict.get(field.name, False) else "0"
                                new_value = values.get(field.name) if values.get(field.name, False) else "0"
                            else:
                                old_value = field_dict.get(field.name) if field_dict.get(field.name, False) else "NA"
                                new_value = values.get(field.name) if values.get(field.name, False) else "NA"
                            tracking_vals.append((0, 0, {'field_name': field.field_description, 'old_value': old_value, 'new_value': new_value}))
                    if tracking_vals:
                        values['date_start'] = date.today() #Update Validity From with today's date
                        validity_periods_tracking_vals = [(0, 0, {'validity_from': date.today(), 'validity_to': validation_to, 'tracking_ids': tracking_vals})]
                        record = rec.env['time.dependent.record'].search([('rec_id', '=', rec.id), ('model_id', '=', time_dependent_model_rec.id)], limit=1)
                        #Create new record with Validity Periods and Tracking Values.
                        if not record: time_dependent_model_rec.record_ids = [(0, 0, {'rec_id': rec.id, 'model_id': time_dependent_model_rec.id, 'validity_period_ids': validity_periods_tracking_vals})]
                        #Update record with Validity Periods and Tracking Values.
                        elif record:
                            validity_period_rec = self.env['time.validity.period'].search([('record_id', '=', record.id)], order='id desc', limit=1)
                            if not validity_period_rec:
                                record.validity_period_ids = validity_periods_tracking_vals
                            elif validity_period_rec:
                                if validity_period_rec.validity_from == date.today().strftime("%Y-%m-%d"):
                                    validity_period_rec.tracking_ids = tracking_vals
                                    validity_period_rec.validity_to = validation_to
                                elif validity_period_rec.validity_from != date.today().strftime("%Y-%m-%d"):
                                    validity_period_rec.validity_to = date.today() - timedelta(days=1)
                                    record.validity_period_ids = validity_periods_tracking_vals
        return super(TimeDependent, self).write(values)

    @api.multi
    def unlink(self):
        for rec in self:
            time_dependent_model_rec = rec.env['time.dependent.model'].search([('model_id.model', '=', rec._name)])
            if time_dependent_model_rec:
                record = rec.env['time.dependent.record'].search([('rec_id', '=', rec.id), ('model_id', '=', time_dependent_model_rec.id)], limit=1)
                if record: record.unlink()
        return super(TimeDependent, self).unlink()


class TimeDependentModel(models.Model):
    _name = 'time.dependent.model'
    _rec_name = 'model_id'

    model_id = fields.Many2one('ir.model', string='Model', ondelete='cascade', required=True, index=True)
    field_ids = fields.Many2many('ir.model.fields', column1='dependent_id', column2='field_id', string='Fields', required=True, index=True, domain = [('ttype','in',['boolean', 'char', 'text', 'integer', 'float', 'date', 'datetime'])])
    record_ids = fields.One2many('time.dependent.record', 'model_id', string='Record Ref#')

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.field_ids = []
        if self.model_id:
            return {'domain': {'field_ids': [('id', 'in', self.model_id.field_id.ids)]}}
        else:
            return {'domain': {'field_ids': [('id', 'in', [])]}}

    @api.constrains('model_id')
    def _check_model_sequence(self):
        if self.search_count([('model_id', '=', self.model_id.id)]) > 1:
            raise ValidationError(_("Model already exists in time dependent."))


class TimeDependentRecord(models.Model):
    _name = 'time.dependent.record'

    rec_id = fields.Integer(string='Record ID')
    name = fields.Char(string="Record Ref#", compute='_get_record_reference')
    validity_period_ids = fields.One2many('time.validity.period', 'record_id', string='Validity Periods')
    model_id = fields.Many2one('time.dependent.model', string='Model', ondelete='cascade')

    def _get_record_reference(self):
        for record in self:
            model = record.model_id.model_id.model
            refObj =  self.env[model].browse(record.rec_id)
            record.name = refObj.name_get()[0][1] or ''

    @api.multi
    def action_view_reference_record(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window'].search([('res_model','=',self.model_id.model_id.model)], order='id', limit=1)
        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type': 'form',
            'view_mode': 'form',
            'target': action.target,
            'res_id': self.rec_id or False,
            'res_model': action.res_model,
            'domain': [('id', '=', self.rec_id)],
        }


class TimeValidityPeriod(models.Model):
    _name = 'time.validity.period'

    validity_from = fields.Date('Validity From')
    validity_to = fields.Date('Validity To')
    record_id = fields.Many2one('time.dependent.record', string='Record', ondelete='cascade')
    tracking_ids = fields.One2many('time.tracking.values', 'validity_period_id', string="Tracking Values")


class TimeTrackingValues(models.Model):
    _name = 'time.tracking.values'
    _rec_name = 'field_name'

    field_name = fields.Char('Field')
    old_value = fields.Char('Old Value')
    new_value = fields.Char('New Value')
    validity_period_id = fields.Many2one('time.validity.period', string='History', ondelete='cascade')