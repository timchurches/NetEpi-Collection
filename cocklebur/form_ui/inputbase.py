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
from cocklebur import utils
from cocklebur.form_ui import common, columns

class FormBase:
    ignoreattrs = ()

    def __eq__(self, other):
        # Ugly, but it should only be used for testing purposes.
        if self.__class__ is not other.__class__:
            return False
        a=dict(vars(self)) 
        b=dict(vars(other))
        for attr in self.ignoreattrs:
            a.pop(attr, None)
            b.pop(attr, None)
        return a == b

    def __ne__(a, b):
        return not a == b

    def __repr__(self):
        attrs = vars(self).keys()
        attrs.sort()
        attrs = ['%s=%r' % (a, getattr(self, a)) 
                 for a in attrs if a not in self.ignoreattrs]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(attrs))


class Skip(FormBase):
    """
    An "input" can have one or more "skips" defined. The skip has a name,
    and a set of conditions under which triggers. When triggered, the
    skip may disable subsequent inputs in the current question, and/or
    be referred to by later questions (via a trigger) which results in
    all inputs in that question being skipped or enabled.
    """
    not_selected = False
    show_msg = True
    skip_remaining = True
    ignoreattrs = 'input', 'enable_targets', 'disable_targets'

    def __init__(self, name, values, not_selected=None, show_msg=None,
                 skip_remaining=None):
        self.name = name
        self.values = values
        if not_selected is not None and not_selected != self.not_selected:
            self.not_selected = not_selected
        if show_msg is not None and show_msg != self.show_msg:
            self.show_msg = show_msg
        if skip_remaining is not None and skip_remaining != self.skip_remaining:
            self.skip_remaining = skip_remaining
        self.input = None

class InputBase(FormBase):
    render = 'TextInput'
    label = None
    required = False
    summarise = False
    default = None
    pre_text = None
    post_text = None
    locked_column = None        # If set, specifies an overriding column name
    input_group = None          # Specifies UI grouping
    skips = []
    default_options = [
        ('None', 'None'),
        ('value', 'Value'),
    ]

    def __init__(self, column, **kwargs):
        if len(column) > common.max_identifier_len:
            raise common.FormDefError('%s input column name %r too long (%d, max %d)' %\
                        (self.__class__.__name__, column, 
                         len(column), common.max_identifier_len))
        if self.locked_column:
            column = self.locked_column
        self.column = column
        if 'label' not in kwargs and 'summary' in kwargs:
            kwargs['label'] = kwargs.pop('summary')
        self.__dict__.update(kwargs)
        for skip in self.skips:
            if not isinstance(skip, Skip):
                raise common.FormDefError('%s input %r, skips must be a Skip instance, not %r' % (self.__class__.__name__, self.column, skip))
            skip.input = self

    def get_column_name(self):
        return self.column.lower()

    def get_column_names(self):
        return [self.get_column_name()]

    def get_value(self, ns):
        return getattr(ns, self.get_column_name(), None)

    def set_value(self, ns, value):
        setattr(ns, self.get_column_name(), value)

    def get_default(self):
        return self.default

    def validate(self, ns):
        value = self.get_value(ns)
        if not value and self.required:
            raise common.ValidationError('this field must be answered')
        return value

    def nscopy(self, src, dst):
        for name in self.get_column_names():
            setattr(dst, name, getattr(src, name, None))

    def get_defaults(self, defaults):
        value = self.get_default()
        if value is not None:
            defaults[self.get_column_name()] = value

    def _collect_columns(self, columns):
        columns.add_column(self, self.column, self.dbobj_type)

    def update_xlinks(self, question, _helper=None):
        if _helper is None:
            _helper = columns.XlinkHelper()
        for skip in self.skips:
            _helper.add_condition(skip, question)

    def outtrans(self, ns):
        try:
            value = self.get_value(ns)
        except common.ValidationError:
            value = '*ERR*'
        if value is not None:
            return str(value)

    def collect_summary(self, ns):
        if self.summarise:
            label = self.label or self.column
            value = self.outtrans(ns)
            if value is None:
                value = 'n/a'
            if '*' not in label:
                label = '*%s*' % label
            return ['%s: %s' % (label, value)]
        else:
            return []

    def js_question(self, js_question):
        pass

    def format(self):
        return None

    def get_pre_text(self):
        return self.pre_text

    def get_post_text(self):
        return self.post_text


class TextInputBase(InputBase):
    dbobj_type = dbobj.StringColumn
    maxsize = None
    input_group = 'Text'

    def validate(self, ns):
        value = InputBase.validate(self, ns)
        if value is not None:
            if self.maxsize and len(value) > self.maxsize:
                raise common.ValidationError('field must be %d characters or less' % self.maxsize)
        return value

    def _collect_columns(self, columns):
        columns.add_column(self, self.column, self.dbobj_type, 
                           size=self.maxsize)


class NumberInputBase(InputBase):
    minimum = None
    maximum = None
    input_group = 'Numeric'

    def _checkrange(self, value):
        if value is not None:
            if self.minimum is not None and value < self.minimum:
                raise common.ValidationError('must greater than or equal to %s' % self.minimum)
            if self.maximum is not None and value > self.maximum:
                raise common.ValidationError('must less than or equal to %s' % self.maximum)


class ChoicesBase(InputBase):
    direction = 'auto'
    input_group = 'Discrete'

    def __init__(self, column, **kwargs):
        # Legacy
        if 'horizontal' in kwargs:
            if kwargs['horizontal']:
                kwargs['direction'] = 'horizontal'
            else:
                kwargs['direction'] = 'vertical'
        if getattr(self, 'choices', None) is None: 
            self.choices = []
        InputBase.__init__(self, column, **kwargs)

    def get_choices(self):
        return self.choices
# Albatross is not idempotent in it's handling of None when used with al-input
# or al-select. This poses unresolvable problems here. Give up for now.
#        for value, label in self.choices:
#            if str(value) == 'None':
#                value = ''
#            choices.append((value, label))
#        return choices

    def describe_skip(self, skip):
        if not skip.show_msg:
            return
        labels = []
        for value, label in self.choices:
            if value in skip.values:
                labels.append(label)
        if labels:
            op = 'selected'
            if skip.not_selected:
                op = 'did not select'
            return '%s %s' % (op, utils.commalist(labels))

    def skiptext(self):
        skipstext = []
        for skip in self.skips:
            if skip.skip_remaining:
                skiptext = self.describe_skip(skip)
                if skiptext:
                    skipstext.append('If you %s, skip the remaining parts of '
                                     'this question' % (skiptext))
        return skipstext

    def js_question(self, js_question):
        for skip in self.skips:
            js_question.input_skip(skip.name, self.get_column_name(), 
                                   skip.values, skip.not_selected, 
                                   skip.skip_remaining)

    def render_horizontal(self):
        if self.direction == 'auto':
            fieldlens = [len(c[1]) + 2 
                         for c in self.choices
                         if c[1]]
            return sum(fieldlens) < 45;
        else:
            return self.direction == 'horizontal'

class OneChoiceBase(ChoicesBase):
    maxsize = None
    dbobj_type = dbobj.StringColumn

    def __init__(self, column, **kwargs):
        ChoicesBase.__init__(self, column, **kwargs)
        if self.maxsize:
            for value, label in self.choices:
                if len(value) > self.maxsize:
                    raise common.FormDefError('Length of %r choice exceeds maximum field size (%s)' % (value, self.maxsize))

    def _collect_columns(self, columns):
        columns.add_column(self, self.column, self.dbobj_type, 
                           size=self.maxsize)

    def outtrans(self, ns):
        value = ChoicesBase.outtrans(self, ns)
        for choice_value, label in self.choices:
            if choice_value == value:
                return label
        return value
