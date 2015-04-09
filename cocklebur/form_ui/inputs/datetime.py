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
from cocklebur import dbobj, datetime
from cocklebur.form_ui import common
from cocklebur.form_ui.inputbase import InputBase


class _DateTimeInputBase(InputBase):
    default_options = InputBase.default_options + [
        ('now', 'Current Time/Date'),
    ]
    input_group = 'Date & time'

    def __init__(self, columns, **kwargs):
        InputBase.__init__(self, columns, **kwargs)

    def validate(self, ns):
        value = InputBase.validate(self, ns)
        if not value:
            return None
        try:
            return self.parser(value)
        except datetime.Error, e:
            raise common.ValidationError(str(e))

    def get_default(self):
        if self.default == 'now':
            return datetime.now()
        else:
            return self.default

    def get_post_text(self):
        if self.post_text:
            return self.post_text
        else:
            return self.parser.help

    def format(self):
        return self.parser.format

    def outtrans(self, ns):
        try:
            value = self.validate(ns)
        except common.ValidationError:
            return '*ERR*'
        if value is not None:
            return value.strftime(self.format())


class DateInput(_DateTimeInputBase):
    type_name = 'Date Input'
    render = 'DateInput'
    dbobj_type = dbobj.DateColumn
    parser = datetime.mx_parse_date


class TimeInput(_DateTimeInputBase):
    type_name = 'Time Input'
    dbobj_type = dbobj.TimeColumn
    parser = datetime.mx_parse_time


class DatetimeInput(_DateTimeInputBase):
    type_name = 'Date/Time Input'
    render = 'DateInput'
    dbobj_type = dbobj.DatetimeColumn
    parser = datetime.mx_parse_datetime

class FormDateInput(DatetimeInput):
    type_name = 'Primary Form Date'
    locked_column = 'form_date'
