#
#   The contents of this file are subject to the HACOS License Version 1.2
#   (the "License"); you may not use this file except in compliance with
#   the License.  Software distributed under the License is distributed
#   on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
#   implied. See the LICENSE file for the specific language governing
#   rights and limitations under the License.  The Original Software
#   is "NetEpi Collection". The Initial Developer of the Original
#   Software is the Health Administration Corporation, incorporated in
#   the State of New South Wales, Australia.
#
#   Copyright (C) 2004-2011 Health Administration Corporation, Australian
#   Government Department of Health and Ageing, and others.
#   All Rights Reserved.
#
#   Contributors: See the CONTRIBUTORS file for details of contributions.
#
try:
    set
except NameError:
    from sets import Set as set
from cocklebur import dbobj
from cocklebur.form_ui import common, inputbase

class TextInput(inputbase.TextInputBase):
    type_name = 'Text Input'
    maxsize = 60


class IntInput(inputbase.NumberInputBase):
    type_name = 'Integer Input'
    dbobj_type = dbobj.IntColumn

    def validate(self, ns):
        value = inputbase.NumberInputBase.validate(self, ns)
        if isinstance(value, basestring):
            try:
                if not value.strip():
                    return None
                value = float(value)                            # Accept float
                int_value = int(round(value))
                if int_value != value:
                    value = int_value
                    self.set_value(ns, value)                   # But truncate
            except ValueError:
                raise common.ValidationError('value must be a number')
        self._checkrange(value)
        return value


class FloatInput(inputbase.NumberInputBase):
    type_name = 'Decimal Input'
    dbobj_type = dbobj.FloatColumn

    def validate(self, ns):
        value = inputbase.NumberInputBase.validate(self, ns)
        if isinstance(value, basestring):
            if not value.strip():
                return None
            try:
                value = float(value)
            except ValueError:
                raise common.ValidationError('value must be a number')
        self._checkrange(value)
        return value


class TextArea(inputbase.TextInputBase):
    type_name = 'Text Area Input'
    render = 'TextArea'
    maxsize = 300


class DropList(inputbase.OneChoiceBase):
    type_name = 'Drop List Input'
    render = 'DropList'

class RadioList(inputbase.OneChoiceBase):
    type_name = 'Radio Button List Input'
    render = 'RadioList'

class YesNo(RadioList):
    type_name = 'Yes/No Input'
    choices = [
        ('True', 'Yes'), 
        ('False', 'No'),
        ('Unknown', 'Unknown'),
        ('None', 'Not answered'),
    ]

class CheckBoxes(inputbase.ChoicesBase):
    type_name = 'Checkboxes Input'
    render = 'CheckBoxes'
    dbobj_type = dbobj.BooleanColumn

    def __init__(self, column, **kwargs):
        inputbase.ChoicesBase.__init__(self, column, **kwargs)
        for value, label in self.choices:
            if (len(self.column) + len(value)) > common.max_identifier_len:
                raise common.FormDefError('column %r choice %r combined are too long (max %d)' % (self.column, value, common.max_identifier_len))

    def get_column_names(self):
        return [(self.column + name).lower() for name, label in self.choices]

    def js_question(self, js_question):
        for skip in self.skips:
            inputs = [(self.column + name).lower() for name in skip.values]
            js_question.inputs_skip(skip.name, inputs, 
                                    skip.not_selected, skip.skip_remaining)

    def _collect_columns(self, columns):
        for col_name, col_text in self.choices:
            columns.add_column(self, (self.column + col_name).lower(), 
                               self.dbobj_type, default='False')

    def get_value(self, ns):
        values = []
        for col_name, col_text in self.choices:
            value = getattr(ns, (self.column + col_name).lower(), None)
            if value:
                values.append(col_name)
        return values

    def get_defaults(self, defaults):
        values = set([value.lower() for value, label in self.choices])
        if self.default:
            for value in self.default.split(','):
                value = value.strip().lower()
                if value in values:
                    defaults[self.column + value] = True

    def outtrans(self, ns):
        values = self.get_value(ns)
        if values:
            result = []
            for value, label in self.choices:
                if value in values:
                    result.append(label)
            return '/'.join(result)
