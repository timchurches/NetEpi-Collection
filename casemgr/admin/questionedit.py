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
import re
import inspect
try:
    set
except NameError:
    from sets import Set as set
from cocklebur import form_ui, dbobj
from cocklebur import introspect
from cocklebur.tuplestruct import TupleStruct
from cocklebur.safehtml import safehtml


class QuestionNameError(Exception): pass

def _boolfix(v):
    return str(v) == 'True'

class Choice(TupleStruct):
    __slots__ = 'key', 'label'

class Default:
    def __init__(self):
        self.type = 'None'
        self.value = ''
        self.input_type = None

    def to_form(self, kwargs):
        if self.type == 'value':
            kwargs['default'] = self.value
        elif self.type == 'None':
            pass
        else:
            kwargs['default'] = self.type

    def init_value(self, value):
        if value is not None:
            for tag, label in self.get_options():
                if tag == value:
                    self.type = tag
                    break
            else:
                self.type = 'value'
                self.value = value

    def set_input_type(self, input_type):
        self.input_type = input_type

    def get_options(self):
        cls = input_classes.get(self.input_type, None)
        if cls is None:
            return []
        else:
            return cls.default_options


class _FS(TupleStruct):
    __slots__ = 'label', 'name', 'pytype', 'has_meth'
    def has(self, inst):
        return not self.has_meth or getattr(inst, self.has_meth)()

class Skip(object):
    def __init__(self, skip=None):
        self.not_selected = ''
        self.show_msg = 'True'
        self.skip_remaining = 'True'
        if skip is None:
            self.initial_name = self.name = ''
            self.values = []
        else:
            self.initial_name = self.name = skip.name
            if skip.not_selected:
                self.not_selected = 'True'
            if not skip.show_msg:
                self.show_msg = ''
            if not skip.skip_remaining:
                self.skip_remaining = ''
            self.values = skip.values

    def to_form(self):
        return form_ui.Skip(self.name, self.values, 
                            self.not_selected == 'True',
                            self.show_msg == 'True',
                            self.skip_remaining == 'True')

class Input(object):

    fields = [
        _FS('Pre-text', 'pre_text', str, 'has_pre_text'),
        _FS('Post-text', 'post_text', str, 'has_post_text'),
        _FS('Maximum Size', 'maxsize', int, 'has_maxsize'),
        _FS('Minimum Value', 'minimum', float, 'has_minmax'),
        _FS('Maximum Value', 'maximum', float, 'has_minmax'),
    ]
    unknown_seq = 0
    with_time = False

    def __init__(self, element, edit_info):
        self.edit_info = edit_info
        self.column = ''
        self.input_type = self.want_type = 'None'
        self.required = 'False'
        self.summarise = 'False'
        self.edit_choices = []
        self.direction = 'auto'
        self.choice_order = ''
        self.input_groups = input_groups
        self.default = Default()
        self.skips = []
        self.clear_err()
        attrs = (
            'pre_text', 'post_text', 'label', 'maxsize',
            'minimum', 'maximum'
        )
        if element:
            self.column = element.column
            self.set_type(element.__class__.__name__)
            if hasattr(element, 'default'):
                self.default.init_value(element.default)
            if self.has_direction():
                self.direction = element.direction
            if hasattr(element, 'choices'):
                self.edit_choices = [Choice(name, label) 
                                     for name, label in element.choices]
                self.skips = [Skip(skip) for skip in element.skips]
            if element.required:
                self.required = 'True'
            if element.summarise:
                self.summarise = 'True'
            for attr in attrs:
                setattr(self, attr, getattr(element, attr, None))
        else:
            for attr in attrs:
                setattr(self, attr, '')

    def get_choices(self):
        return [(c.key, c.label) 
                for i, c in enumerate(self.edit_choices)]
    choices = property(get_choices)

    def get_pre_text(self):
        return self.pre_text

    def get_post_text(self):
        return self.post_text

    describe_skip = form_ui.ChoicesBase.describe_skip.im_func
    skiptext = form_ui.ChoicesBase.skiptext.im_func

    def choicevalues(self):
        return [c.key for c in self.edit_choices]

    def clear_err(self):
        self.error = ''

    def get_class(self):
        return input_classes.get(self.input_type)

    def to_form(self):
        def add_attr(attr, attr_type, value=None):
            cls_attr = introspect.getclassattr(cls, attr)
            if value is None:
                value = getattr(self, attr)
            if value == '':
                value = None
            if value is not None:
                try:
                    value = attr_type(value)
                except (TypeError, ValueError):
                    value = attr_type()
            if value is not None and cls_attr != value:
                kwargs[attr] = value
        cls = self.get_class()
        kwargs = {}
        self.default.to_form(kwargs)
        add_attr('required', bool, _boolfix(self.required))
        add_attr('summarise', bool, _boolfix(self.summarise))
        add_attr('label', str, self.label)
        if self.has_direction():
            add_attr('direction', str, self.direction)
        for fs in self.fields:
            if fs.has(self):
                add_attr(fs.name, fs.pytype)
        if self.has_choices():
            if introspect.getclassattr(cls, 'choices') is None:
                kwargs['choices'] = self.choices
            if self.skips:
                kwargs['skips'] = [skip.to_form() for skip in self.skips]
        return cls(self.column, **kwargs)

    def commit(self):
        for skip in self.skips:
            if skip.initial_name and skip.initial_name != skip.name:
                self.edit_info.condition_rename(skip.initial_name, skip.name)

    def render_horizontal(self):
        if self.has_direction():
            if self.direction == 'auto':
                # Logic copied from cocklebur.form_ui.inputbase
                fieldlens = [len(c.label) + 2 
                            for c in self.edit_choices
                            if c.label]
                return sum(fieldlens) < 45;
            else:
                return self.direction == 'horizontal'
        return False

    def check(self):
        if self.input_type not in input_classes:
            return 'select an input type'
        if not self.column or not self.column.strip():
            return 'a column name is required'
        # XXX for checkbox inputs, we need to iterate over the possible names
        try:
            self.edit_info.check_column_name(self.column)
        except QuestionNameError, e:
            return str(e)
        locked_column = self.locked_column()
        if locked_column:
            self.column = locked_column
        if self.column == 'form_date' and not self.is_date():
            return 'form_date must be a Date/Time Input'
        if self.has_choices():
            badch_re = re.compile('[^a-z0-9_]', re.IGNORECASE)
            for choice in self.edit_choices:
                # A null key is used for the "not answered" case? AM 070327
                if choice.key is None:
                    choice.key = ''
                else:
                    choice.key = badch_re.sub('_', choice.key)
            for skip in self.skips:
                if not skip.name:
                    return 'skips must have a name'
                if not skip.values:
                    return 'skips must have values selected'
                try:
                    self.edit_info.check_condition_name(skip.name)
                except QuestionNameError, e:
                    return str(e)
        for fs in self.fields:
            if fs.has(self):
                value = getattr(self, fs.name, None)
                if value is not None and value is not '':
                    try:
                        setattr(self, fs.name, fs.pytype(value))
                    except (TypeError, ValueError), e:
                        return '%s: %s' % (fs.label, e)
        if self.has_maxsize() and self.maxsize and self.maxsize <= 0:
            return 'Maximum size must be greater than zero'
        try:
            self.to_form()
        except form_ui.FormError, e:
            return str(e)
        return ''

    def get_column_name(self):
        name = self.column
        try:
            dbobj.valid_identifier(self.column)
        except dbobj.DatabaseError:
            name = None
        if not name:
            name = 'unknown_%d' % self.unknown_seq
            Input.unknown_seq += 1
        return name

    def format(self):
        return ''

    def get_renderer(self):
        return getattr(self.get_class(), 'render', '')

    def locked_column(self):
        return getattr(self.get_class(), 'locked_column', '')

    def has_pre_text(self):
        return True
#        return self.get_renderer() in ('TextInput',)

    def has_post_text(self):
        return True
#        return self.get_renderer() in ('TextInput',)

    def has_choices(self):
        return self.get_renderer() in ('RadioList', 'DropList', 'CheckBoxes')

    def has_direction(self):
        return self.get_renderer() in ('RadioList', 'CheckBoxes')

    def has_maxsize(self):
        return self.get_renderer() in ('TextInput', 'TextArea', 'DropList', 'RadioList')

    def is_numeric(self):
        cls = self.get_class()
        return cls is not None and issubclass(cls, form_ui.NumberInputBase)

    def is_date(self):
        return self.input_type in ('DateInput', 'DatetimeInput', 'FormDateInput')

    def has_minmax(self):
        return self.is_numeric()

    def set_type(self, input_type=None):
        if input_type is None:
            input_type = self.want_type
        if input_type == self.input_type:
            return
        self.want_type = self.input_type = input_type
        cls = self.get_class()
        if cls is not None:
            cls_choices = introspect.getclassattr(cls, 'choices')
            if cls_choices is not None:
                self.edit_choices = [Choice(name, label) 
                                     for name, label in cls_choices]
            for fs in self.fields:
                if fs.has(self):
                    value = introspect.getclassattr(cls, fs.name)
                    if value is not None:
                        setattr(self, fs.name, value)
        self.default.set_input_type(self.input_type)

    def apply_choice_order(self):
        if self.choice_order:
            new_choices = []
            for index in self.choice_order.split(','):
                new_choices.append(self.edit_choices[int(index)])
            self.edit_choices = new_choices

    def page_process(self):
        self.set_type()
        self.apply_choice_order()

    def instance_choice_fixup(self):
        # An attempt to mutate an input type with immutable choices has been
        # made - search parent classes for a more appropriate input type.
        for cls in inspect.getmro(self.get_class()):
            if not hasattr(cls, 'choices'):
                self.set_type(cls.__name__)
                break

    def choice_move_up(self, i):
        self.instance_choice_fixup()
        if i > 0:
            self.edit_choices[i], self.edit_choices[i-1] = \
                self.edit_choices[i-1], self.edit_choices[i]

    def choice_move_dn(self, i):
        self.instance_choice_fixup()
        if i < len(self.edit_choices) - 1:
            self.edit_choices[i], self.edit_choices[i+1] = \
                self.edit_choices[i+1], self.edit_choices[i]

    def choice_add(self):
        self.instance_choice_fixup()
        self.edit_choices.append(Choice('',''))

    def choice_del(self, i):
        self.instance_choice_fixup()
        del self.edit_choices[i]

    def cond_add(self):
        skip = Skip()
        if not self.skips:
            skip.name = self.column
        self.skips.append(skip)

    def cond_del(self, i):
        del self.skips[i]



class QuestionTrigger:
    def __init__(self, name=''):
        self.name = name

    def to_form(self):
        return self.name

    def __str__(self):
        return self.name


class QuestionEdit:

    node_type = 'question'

    def __init__(self, edit_info):
        self.edit_info = edit_info
        element = self.edit_info.element
        self.text = ''
        self.help = ''
        self.disabled = ''
        self.inputs = []
        self.triggers = []
        self.trigger_mode = 'disable'
        if element is not None:
            self.text = element.text
            self.help = element.help
            if element.disabled:
                self.disabled = 'True'
            self.trigger_mode = element.trigger_mode
            for name in element.triggers:
                trigger = QuestionTrigger(name)
                if trigger.name in self.edit_info.other_condition_names:
                    self.triggers.append(trigger)
            self.inputs = [Input(inp, self.edit_info) for inp in element.inputs]
        self.clear_changed()
        self.clear_err()

    def clear_changed(self):
        self.changed = False

    def has_changed(self):
        return self.changed

    def input_add(self, i):
        self.inputs.insert(i, Input(None, self.edit_info))
        return i

    def trigger_add(self):
        self.triggers.append(QuestionTrigger())

    def trigger_del(self, i):
        del self.triggers[i]

    def check(self):
        self.edit_info.reset_question_names()
        okay = True
        if self.text:
            self.text = safehtml(self.text)
        if self.help:
            self.help = safehtml(self.help)
        first_error = None
        for index, input in enumerate(self.inputs):
            input.error = input.check()
            if input.error and first_error is None:
                first_error = index
        return first_error

    def clear_err(self):
        self.error = ''
        for input in self.inputs:
            input.clear_err()

    def to_form(self):
        args = {}
        args['inputs'] = [input.to_form() for input in self.inputs]
        if self.triggers:
            args['trigger_mode'] = self.trigger_mode
            args['triggers'] = [trigger.to_form() 
                                for trigger in self.triggers if trigger.name]
        if self.help:
            args['help'] = self.help
        if self.disabled:
            args['disabled'] = True
        return form_ui.Question(self.text, **args)

    def rollback(self):
        pass

    def commit(self):
        form = self.to_form()
        for input in self.inputs:
            input.commit()
        return self.edit_info.commit(form)

    def op(self, target, op, index=None, subindex=None):
        if index is not None:
            index = int(index)
        obj = None
        args = ()
        if target in ('input', 'trigger'):
            obj = self
            if index is not None:
                args = (index,)
        elif target in ('cond', 'choice'):
            obj = self.inputs[index]
            args = ()
            if subindex is not None:
                args = (int(subindex),)
        if obj:
            fn = getattr(obj, '%s_%s' % (target, op))
            return fn(*args)

    def describe_triggers(self):
        triggers = [str(trigger) for trigger in self.triggers]
        if len(triggers) == 1:
            return '%s if %s triggers.' % (self.trigger_mode, triggers[0])
        elif triggers:
            return '%s if any of %s triggers.' % (self.trigger_mode, 
                                               ', '.join(triggers))
        else:
            return 'none'

    def copy(self, indexes):
        return [self.inputs[i].to_form() for i in indexes]

    def cut(self, indexes):
        indexes.sort()
        cutbuf = [self.inputs[i].to_form() for i in indexes]
        for i in indexes[::-1]:
            del self.inputs[i]
        return cutbuf

    def paste(self, index, cutbuf):
        self.inputs[index:index] = [Input(inp, self.edit_info) 
                                    for inp in cutbuf]


def collect_inputs():
    classes = {}
    groups = {}
    for input in form_ui.get_inputs():
        classes[input.__name__] = input
        group = groups.setdefault(input.input_group or 'Miscellaneous', [])
        group.append((input.__name__, input.type_name))
    for group in groups.values():
        group.sort(lambda a, b: cmp(a[1], b[1]))
    groups = groups.items()
    groups.sort()
    groups.insert(0, ('None', '(Select an input type)'))
    return classes, groups

input_classes, input_groups = collect_inputs()
