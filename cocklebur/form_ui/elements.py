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
from cocklebur.form_ui import columns, common, inputs, inputbase, jsmeta
from cocklebur import datetime

_inputs = None
def get_inputs():
    global _inputs
    if _inputs is None:
        inps = []
        for name, attr in vars(inputs).items():
            try:
                if issubclass(attr, inputbase.InputBase) \
                    and name == attr.__name__:
                    inps.append(attr)
            except TypeError:
                pass
        _inputs = inps
    return _inputs

class Question(inputbase.FormBase):
    render = 'Question'
    disabled = False
    help = None
    label = None
    trigger_mode = 'disable'
    triggers = []
    _triggers = []
    ignoreattrs = 'columns', 'label', '_triggers'

    def __init__(self, text, input=None, inputs=None, 
                 help=None, disabled=False, trigger_mode=None, triggers=None):
        self.text = text
        if help:
            self.help = help
        if disabled:
            self.disabled = disabled
        if input and inputs:
            raise common.FormDefError('specify "input" or "inputs", not both')
        if input:
            inputs = [input]
        if inputs is None:
            inputs = []
        for input in inputs:
            if not isinstance(input, inputbase.InputBase):
                raise common.FormDefError('question inputs must be '
                                            'InputBase subclasses')
        self.inputs = inputs
        if trigger_mode is not None:
            self.trigger_mode = trigger_mode
        if triggers is not None:
            self.triggers = triggers
        self.columns = []

    def __iter__(self):
        return iter([])

    def update_labels(self, path=''):
        self.label = path

    def get_inputs(self):
        return self.inputs

    def validate(self, namespace, formerrors):
        for input in self.get_inputs():
            try:
                input.validate(namespace)
            except common.ValidationError, e:
                formerrors.add_error(input, e)

    def _collect_columns(self, columns):
        for element in self.get_inputs():
            element._collect_columns(columns)
        return columns

    def collect_summary(self, namespace):
        summary = []
        for element in self.get_inputs():
            summary.extend(element.collect_summary(namespace))
        return summary

    def update_xlinks(self, _helper=None):
        if _helper is None:
            _helper = columns.XlinkHelper()
        for element in self.get_inputs():
            element.update_xlinks(self, _helper)
        self._triggers = [_helper.get_trigger(name) for name in self.triggers]

    def skiptext(self):
        triggerstext = []
        for condition in self._triggers:
            condition_text = condition.skiptext()
            if condition_text:
                triggerstext.append(condition_text)
        if triggerstext:
            if self.trigger_mode == 'enable':
                triggerstext.insert(0, 'Answer this question if you:')
            else:
                triggerstext.insert(0, 'Skip this question if you:')
        return triggerstext

    def js_meta(self, formerrors, js_meta):
        js_question = js_meta.question(self.label, self.trigger_mode)
        for input in self.get_inputs():
            js_question.add_inputs(input.get_column_names())
            input.js_question(js_question)
            if formerrors.input_has_error(input):
                js_question.has_error = True
        for predicate in self.triggers:
            js_question.trigger(predicate)

    def get_defaults(self, defaults=None):
        if defaults is None:
            defaults = {}
        for input in self.get_inputs():
            input.get_defaults(defaults)
        return defaults


class _ElementContainer(inputbase.FormBase):
    ignoreattrs = 'columns', 'label'

    def __init__(self, text):
        self.text = text
        self.children = []
        self.label = ''

    def append(self, instance):
        self.children.append(instance)
        return instance

    def question(self, text, **kwargs):
        self.append(Question(text, **kwargs))

    def update_labels(self, path=''):
        self.label = path
        for i, child in enumerate(self.children):
            label = '%s' % (i + 1)
            if self.label:
                label = '%s.%s' % (self.label, label)
            child.update_labels(label)

    def __getitem__(self, i):
        element = self.children[i]
        element.label = '%s%s.' % (self.label, i + 1)
        return element

    def __len__(self):
        return len(self.children)

    def validate(self, namespace, formerrors=None):
        if formerrors is None:
            formerrors = columns.FormErrors()
        for element in self:
            element.validate(namespace, formerrors)
        return formerrors

    def _collect_columns(self, columns):
        for element in self:
            element._collect_columns(columns)
        return columns

    def update_columns(self):
        self.columns = columns.Columns()
        self._collect_columns(self.columns)

    def update_xlinks(self, _helper=None):
        if _helper is None:
            _helper = columns.XlinkHelper()
        for element in self:
            element.update_xlinks(_helper)

    def collect_summary(self, namespace):
        summary = []
        for element in self:
            summary.extend(element.collect_summary(namespace))
        return summary

    def js_meta(self, formerrors, js_meta=None):
        if js_meta is None:
            js_meta = jsmeta.JSMeta()
        for element in self:
            element.js_meta(formerrors, js_meta)
        return js_meta

    def get_inputs(self):
        inputs = []
        for element in self:
            inputs.extend(element.get_inputs())
        return inputs

    def get_defaults(self, defaults=None):
        if defaults is None:
            defaults = {}
        for element in self:
            element.get_defaults(defaults)
        return defaults


class SubSection(_ElementContainer):
    render = 'SubSection'

class Section(_ElementContainer):
    render = 'Section'

class Form(_ElementContainer):
    render = 'Form'
    name = None
    version = None
    table = None
    form_type = 'case'
    allow_multiple = False
    update_time = None
    author = None
    username = None
    ignoreattrs = _ElementContainer.ignoreattrs + (
        'name', 'table', 'version', 'update_time',
    )

    def __init__(self, text, table=None, name=None,
                 form_type=None, allow_multiple=False,
                 update_time=None, author=None, username=None):
        _ElementContainer.__init__(self, text)
        if table:
            self.table = table
        if name:
            self.name = name
        if form_type:
            self.form_type = form_type
        if allow_multiple:
            self.allow_multiple = allow_multiple
        if update_time:
            if isinstance(update_time, basestring):
                try:
                    update_time = datetime.mx_parse_datetime(update_time)
                except datetime.Error, e:
                    raise common.FormDefError('update_time: %s' % e)
            self.update_time = update_time
        if author:
            self.author = author
        if username:
            self.username = username

    def extra_column(self, *args, **kwargs):
        # Legacy support for loading old form definitions
        pass

class PagedForm(Form):
    render = 'PagedForm'

    def get_toc(self):
        return [(i, "%s %s" % (self[i].label, self[i].text)) 
                for i in range(len(self))]
