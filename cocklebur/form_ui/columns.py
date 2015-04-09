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
from cocklebur.form_ui import common

class _Column(object):
    __slots__ = 'input', 'name', 'type', 'kwargs'

    def __init__(self, input, name, type, kwargs):
        self.input = input
        self.name = name
        self.type = type
        self.kwargs = kwargs

    def __getstate__(self):
        return self.input, self.name, self.type, self.kwargs

    def __setstate__(self, state):
        self.input, self.name, self.type, self.kwargs = state

class Columns:
    """
    A repository for column definitions
    """
    def __init__(self):
        self.columns = []
        self.col_dict = {}
        self.input_by_name = {}

    def __iter__(self):
        return iter(self.columns)

    def add_column(self, input, col_name, col_type, **col_kwargs):
        self.input_by_name[input.column.lower()] = input
        col_name = col_name.lower()
        if col_name in self.col_dict:
            raise common.FormDefError('column "%s" is used more than once' %
                                      (col_name,))
        column = _Column(input, col_name, col_type, col_kwargs)
        self.col_dict[col_name] = column
        self.columns.append(column)

    def find_input(self, name):
        return self.input_by_name[name.lower()]

    def register_table(self, db, table):
        table_desc = db.new_table(table)
        for column in self.columns:
            table_desc.column(column.name, column.type, **column.kwargs)

class ConditionXlink:
    def __init__(self, name):
        self.name = name
        self.skip = None

    def skiptext(self):
        if self.skip is None:
            return None
        input = self.skip.input
        cond = input.describe_skip(self.skip)
        if not cond:
            return None
        text = []
        text.append(cond)
        text.append(' in question %s' % self.question.label)
        if len(self.question.inputs) > 1:
            pre_text = getattr(input, 'pre_text', None)
            text.append(' (')
            text.append(input.label or pre_text or input.column.replace('_', ' '))
            text.append(')')
        text.append('.')
        return ''.join(text)

class XlinkHelper:
    def __init__(self):
        self.conditions_by_name = {}
        self.xlinks_pending = {}

    def add_condition(self, skip, question):
        if skip.name in self.conditions_by_name:
            raise common.FormDefError('skip name "%s" is used more than once' %
                                      (skip.name,))
        self.conditions_by_name[skip.name] = skip, question
        try:
            xlinks_pending = self.xlinks_pending.pop(skip.name)
        except KeyError:
            pass
        else:
            for xlink in xlinks_pending:
                xlink.skip = skip

    def get_trigger(self, name):
        xlink = ConditionXlink(name)
        try:
            skip, question = self.conditions_by_name[name]
        except KeyError:
            self.xlinks_pending.setdefault(name, []).append(xlink)
        else:
            xlink.skip = skip
            xlink.question = question
        return xlink


class FormErrors:
    def __init__(self):
        self.by_input = {}
        self.in_order = []

    def add_error(self, input, e):
        self.by_input[input.column] = str(e)
        self.in_order.append('%s: %s' % (input.label or input.column, e))

    def __len__(self):
        return len(self.by_input)

    def input_has_error(self, input):
        return input.column in self.by_input

    def input_error(self, input):
        return self.by_input.get(input.column, '')
