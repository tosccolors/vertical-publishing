# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date, timedelta

class TimeDependentThread(models.AbstractModel):
    _name = 'time.dependent.thread'

    dependent_ids = fields.One2many(
        'time.dependent', 'res_id', string='Time Faced',
        domain=lambda self: [('model', '=', self._name)], auto_join=True)
    validity_date = fields.Date(string='Valid On', index=True)

    @api.constrains('validity_date')
    def _check_validity_date(self):
        for rec in self.filtered('validity_date'):
            if rec.validity_date < str(datetime.now().date()):
                raise ValidationError(_("'Valid On' can't be past date!"))

    @api.onchange('validity_date')
    def _date_validation(self):
        if not self._origin.validity_date and not self.validity_date:
            return {}
        msg = ''
        vals, warning = {}, {}
        if self._origin.validity_date :
            vals['validity_date'] = self._origin.validity_date
            if not self.validity_date:
                msg= "'Valid On' can't be Null!"
            elif self._origin.validity_date > self.validity_date:
                msg = "'Valid On' can't be later than previous 'Valid On'!"
        elif not self._origin.validity_date and self.validity_date < str(datetime.now().date()):
            vals['validity_date'] = datetime.now().date()
            msg = "'Valid On' can't be past date!"
        if msg:
            warning = {'title': _('Warning'),'message':msg}
        return {'value': vals,  'warning': warning}

    @api.multi
    def _can_track(self, values):
        canTrack = True
        config, filter_field, filter_value = self.env['time.dependent.config'].check_dependent_config(self._name)
        mapFields = []
        if config:
            if filter_field:
                res_value = values.get(filter_field.name, False) if filter_field.name in values else \
                self.mapped(filter_field.name)[0]
                canTrack = True if res_value == filter_value else False
            if canTrack:
                if not self.env['time.dependent'].search([('model','=',self._name),('res_id','=',self.id)]):
                    mapFields = [field for field in config.field_ids]
                    for field in mapFields:
                        if field.name not in values:
                            values[field.name] = self.mapped(field.name)[0] or False
                else:
                    mapFields = filter(lambda f: f.name in values, [field for field in config.field_ids])
                if not mapFields:
                    canTrack = False
        return canTrack, config, mapFields, values

    @api.multi
    def _prepare_record_lines(self, dependentObj, values, mapFields):
        dependentRecord = self.env['time.dependent.record']
        RecordObj = dependentRecord.search([('dependent_id', '=', dependentObj.id)])
        Reclines = []
        for field in mapFields:
            value = values.get(field.name, False)
            field_type = field.ttype
            if not value and field_type in ('boolean', 'integer'):
                # convert boolean False to string False
                if field_type == 'boolean':
                    value = 'False' if not value else True
                else:
                    value = '0' #interger 0 set to character '0'
            elif not value and field_type != 'selection':
                continue
            found = RecordObj.filtered(lambda r: r.field_id.id == field.id)
            if found:
                if field_type == 'selection' and not value:
                    Reclines.append([2, found.id, {'name': value}])#unlink selection record with False value
                else:
                    Reclines.append([1,found.id,{'name': value}])
            else:
                Reclines.append([0,0,{'field_id': field.id, 'name': value, 'dependent_id': dependentObj.id}])
        return Reclines

    @api.multi
    def post_values(self, values):
        canTrack, config, mapFields, values = self._can_track(values)
        timeDependent = self.env['time.dependent']
        
        def _set_ValidTo(self, validity_date):
            current_date = datetime.now().date()
            old_date = datetime.strptime(validity_date, "%Y-%m-%d").date()
            new_date = old_date + timedelta(days=-1)
            timeDependentObj = timeDependent.search([('model', '=', self._name), ('res_id', '=', self.id), ('validity_to', '>', current_date)], order='id desc', limit=1)
            timeDependentObj.write({'validity_to': new_date})

        if canTrack and config:
            validity_date = values.get('validity_date') or datetime.now().date() if 'validity_date' in values else self.validity_date or datetime.now().date()
            dependentObj = timeDependent.search([('model','=',self._name),('res_id','=',self.id),('validity_from','=',validity_date)], limit=1)
            Reclines = self._prepare_record_lines(dependentObj, values, mapFields)

            if Reclines:
                data = {}
                data['record_ids'] = Reclines
                if dependentObj:
                    dependentObj.write(data)
                else:
                    _set_ValidTo(self,str(validity_date))
                    data['model'] = self._name
                    data['res_id'] = self.id
                    data['validity_from'] = validity_date
                    data['validity_to'] = '9999/12/31'
                    timeDependent.create(data)
            values = self.env['time.dependent.config'].filter_values(self, values, mapFields)
        return values

    @api.model
    def create(self, values):
        res_id = super(TimeDependentThread, self).create(values)
        res_id.post_values(values)
        return res_id

    @api.multi
    def write(self, values):
        if 'timeFaceCronUpdate' in self.env.context:
            return super(TimeDependentThread, self).write(values)
        for rec in self:
            values = rec.post_values(values)
        return super(TimeDependentThread, self).write(values)

    @api.multi
    def unlink(self):
        for rec in self:
            dependentObj = rec.env['time.dependent'].search([('model', '=', rec._name),('res_id', '=', rec.id)])
            dependentObj.unlink()
        return super(TimeDependentThread, self).unlink()


class TimeDependentConfig(models.Model):
    _name = 'time.dependent.config'
    _rec_name = 'model_id'

    model_id = fields.Many2one('ir.model', string='Model', ondelete='cascade', required=True, index=True)
    field_ids = fields.Many2many('ir.model.fields', column1='dependent_config_id', column2='field_id', string='Fields', required=True, index=True)
    filter_field_id = fields.Many2one('ir.model.fields', string='Field to Filter', help="Boolean fields to filter based on time faced tracking is done.")
    value = fields.Boolean(string="Value", default=True, help="Value for selected boolean field to filter based on time faced tracking is done.")

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.field_ids = []
        self.field_id = False
        self.value = False

    @api.constrains('model_id')
    def _check_model_sequence(self):
        if self.search_count([('model_id', '=', self.model_id.id)]) > 1:
            raise ValidationError(_("Model already exists in time dependent."))

    @api.multi
    def unlink(self):
        for rec in self:
            dependentObj = rec.env['time.dependent'].search([('model', '=', rec.model_id.model)])
            dependentObj.unlink()
        return super(TimeDependentConfig, self).unlink()

    def check_dependent_config(self, model):
        config = self.search([('model_id.model', '=', model)])
        filter_field = False
        filter_value = False
        if config.filtered('filter_field_id'):
            filter_field = config.filter_field_id
            filter_value = config.value
        return config, filter_field, filter_value

    def filter_values(self, rec, values, mapFields):
        domain = [
            ('model', '=', rec._name),
            ('res_id', '=', rec.id),
            ('validity_from', '<=', datetime.now().date()),
            ('validity_to', '>=', datetime.now().date()),
        ]
        dependent_obj = self.env['time.dependent'].search(domain, order='id desc', limit=1)
        if not dependent_obj:
            return values
        for field in mapFields:
            record_obj = dependent_obj.record_ids.filtered(lambda r: r.field_id.id == field.id)
            if not record_obj:
                continue
            val = record_obj.name
            #convert False string to boolean False
            val = False if field.ttype == 'boolean'and val == 'False' else record_obj.name
            values[field.name] = val

        return values

    def update_dependent_values(self):
        for config_obj in self.search([]):
            refModel = config_obj.model_id.model
            config, filter_field, filter_value = self.check_dependent_config(config_obj.model_id.model)
            mapFields = filter(lambda f: f.name, [field for field in config.field_ids])
            domain = [(str(filter_field.name),'=',filter_value)] if filter_field else []
            refModelObjs = self.env[refModel].search(domain)
            for recordobj in refModelObjs:
                values = {}
                values = self.filter_values(recordobj, values, mapFields)
                if not values:
                    continue
                recordobj.with_context({'timeFaceCronUpdate':True}).write(values)
        return True

class TimeDependent(models.Model):
    _name = 'time.dependent'
    _rec_name = 'model'

    model = fields.Char('Related Model', index=True)
    res_id = fields.Integer('Related Ref# ID', index=True)
    validity_from = fields.Date('Valid From')
    validity_to = fields.Date('Valid To')
    record_ids = fields.One2many('time.dependent.record', 'dependent_id', string='Record Ref#')


class TimeDependentRecord(models.Model):
    _name = 'time.dependent.record'

    field_id = fields.Many2one('ir.model.fields', string='Field',)
    name = fields.Char(string="Values")
    dependent_id = fields.Many2one('time.dependent', string='Time Dependent', ondelete='cascade')
