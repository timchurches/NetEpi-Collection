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

import os
import sys
import copy
try:
    set
except NameError:
    from sets import Set as set
from cStringIO import StringIO

from cocklebur import utils
from casemgr import globals, syndrome, demogfields
from casemgr.dataimp import elements, xmlload, xmlsave
from casemgr.dataimp.common import DataImpEditorError as Error

CHOOSE = 'Choose...'

# The Action subclasses correspond to the Import rules in "elements",
# and govern the field editor behaviour
class Action(object):
    def __init__(self, importrule):
        self.initial = isinstance(importrule, self.ctor)
        self.selected = False


class ActionSource(Action):
    action_name = 'source'
    desc = 'Import column'
    ctor = elements.ImportSource
    src = ''

    def __init__(self, importrule):
        Action.__init__(self, importrule)
        if self.initial:
            self.src = importrule.src

    def to_element(self, name):
        if self.src and self.src != CHOOSE:
            return self.ctor(name, self.src)
        else:
            return elements.ImportIgnore(name)


class ActionAgeSource(ActionSource):
    action_name = 'agesource'
    desc = 'DOB and age'
    ctor = elements.ImportAgeSource
    age = ''

    def __init__(self, importrule):
        ActionSource.__init__(self, importrule)
        if self.initial:
            self.age = importrule.age

    def to_element(self, name):
        if self.age == CHOOSE:
            self.age = ''
        if self.src and self.src != CHOOSE:
            return self.ctor(name, self.src, self.age)
        else:
            return elements.ImportIgnore(name)


class ActionMultiValue(ActionSource):
    action_name = 'multivalue'
    desc = 'Multivalue'
    ctor = elements.ImportMultiValue
    delimiter = ''
    delimiter_options = [
        ('/', '/'),
        (' ', 'space'),
        ('\t', 'tab'),
        (',', 'comma'),
    ]

    def __init__(self, importrule):
        ActionSource.__init__(self, importrule)
        if self.initial:
            self.delimiter = importrule.delimiter

    def to_element(self, name):
        if self.src and self.src != CHOOSE:
            return self.ctor(name, self.src, self.delimiter)
        else:
            return elements.ImportIgnore(name)


class ActionFixed(Action):
    action_name = 'fixed'
    desc = 'Set value'
    ctor = elements.ImportFixed
    value = ''

    def __init__(self, importrule):
        Action.__init__(self, importrule)
        if self.initial:
            self.value = importrule.value

    def to_element(self, name):
        return self.ctor(name, self.value)


class ActionIgnore(Action):
    action_name = 'ignore'
    desc = 'Ignore'
    ctor = elements.ImportIgnore

    def __init__(self, importrule):
        Action.__init__(self, importrule)

    def to_element(self, name):
        return self.ctor(name)


class TranslateBase(object):
    type = None
    match = ''
    to = ''
    ignorecase = 'True'

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def from_element(cls, element):
        return cls(match=element.match,
                   to=element.to,
                   ignorecase=str(element.ignorecase))
    from_element = classmethod(from_element)


class Translate(TranslateBase):
    type = 'Translate'

    def to_element(self):
        return elements.Translate(self.match, self.to, 
                                  self.ignorecase == 'True')


class RegExp(TranslateBase):
    type = 'RegExp'

    def to_element(self):
        return elements.RegExp(self.match, self.to, 
                                  self.ignorecase == 'True')


class EditField(object):
    date_formats = [
        'YYYY-MM-DD',
        'YYYY-MM-DD hh:mm:ss',
        'YYYYMMDD',
        'DD/MM/YY',
        'DD/MM/YY hh:mm:ss',
        'DD/MM/YYYY',
        'DD/MM/YYYY hh:mm:ss',
        'MM/DD/YY',
        'MM/DD/YY hh:mm:ss',
        'MM/DD/YYYY',
        'MM/DD/YYYY hh:mm:ss',
    ]
    date_format = ''
    date_format_other = ''
    case_options = [
        ('unchanged', 'Unchanged'),
        ('upper', 'Upper'),
        ('lower', 'Lower'),
        ('title', 'Title'),
        ('capitalize', 'Capitalise'),
    ]
    case = 'unchanged'

    def __init__(self, group, name, label, importrule, 
                 field_options=None,
                 is_datefield=False, is_filterable=True, 
                 is_dob=False, is_set=False, ignore_case=False):
        self.group = group
        self.name = name
        self.label = label
        self.importrule = importrule
        self.is_datefield = is_datefield
        self.is_filterable = is_filterable
        self.is_set = is_set
        self.ignore_case = ignore_case
        if is_dob:
            action_cls = (ActionAgeSource, ActionSource)
        elif is_set:
            action_cls = (ActionMultiValue,)
        else:
            action_cls = (ActionSource,)
        action_cls = action_cls + (ActionFixed, ActionIgnore)
        self.actions = [cls(importrule) for cls in action_cls]
        self.selected = self.actions[0]
        for action in self.actions:
            if isinstance(importrule, action.ctor):
                self.selected = action
        self.selected.selected = True
        self.field_options = field_options
        self.translations = []
        for translation in importrule.translations:
            if isinstance(translation, elements.Date):
                for fmt in self.date_formats:
                    if fmt == translation.format:
                        self.date_format = fmt
                        break
                else:
                    self.date_format_other = translation.format
            elif isinstance(translation, elements.Case) and not self.ignore_case:
                self.case = translation.mode
            elif isinstance(translation, elements.Translate):
                self.translations.append(Translate.from_element(translation))
            elif isinstance(translation, elements.RegExp):
                self.translations.append(RegExp.from_element(translation))

    def demog(cls, demogfield, importrule):
        """
        Ctor from demogfield
        """
        is_datefield = isinstance(demogfield,demogfields.DatetimeBase)
        field_options = None
        if demogfield.optionexpr is not None:
            field_options = demogfield.optionexpr()
        self = cls(None, demogfield.name, demogfield.label, importrule,
                   is_datefield=is_datefield,
                   is_dob=(demogfield.name == 'DOB'),
                   field_options=field_options)
        return self
    demog = classmethod(demog)

    def form(cls, form, input, importrule):
        """
        Ctor from form input
        """
        is_datefield = input.input_group and input.input_group.startswith('Date')
        try:
            get_choices = input.get_choices
        except AttributeError:
            field_options = None
        else:
            field_options = [v for v in get_choices() if v[0]]
        self = cls(form, input.column, input.label or input.column, importrule,
                   is_datefield=is_datefield,
                   is_set=input.type_name.startswith('Checkboxes'),
                   ignore_case=input.type_name.startswith('Checkboxes'),
                   field_options=field_options)
        return self
    form = classmethod(form)

    def src_fields(self, dataimp_src):
        fields = list(dataimp_src.preview.col_names)
        fields.sort()
        fields.insert(0, CHOOSE)
        return fields

    def colvalues(self, dataimp_src):
        if not self.selected.src:
            return None
        delimiter = getattr(self.selected, 'delimiter', None)
        values = dataimp_src.preview.colvalues(self.selected.src)
        if values:
            have = set()
            element = self.to_element()
            for value in values:
                if delimiter:
                    for value in value.split(delimiter):
                        if value:
                            have.add(value)
                elif value:
                    have.add(value)
            values = list(have)
            values.sort()
        return values

    def preview(self, dataimp_src):
        src_col = getattr(self.selected, 'src', None)
        if not src_col:
            return []
        preview = (dataimp_src.preview.colvalues(src_col)
                   or dataimp_src.preview.colpreview(src_col))
        if preview:
            preview = preview[:15]
        return preview

    def get_missing_field_options(self, colvalues=None):
        want = set()
        for value, label in self.field_options:
            if self.ignore_case:
                value = value.lower()
            want.add(value)
        have = set()
        if colvalues:
            element = self.to_element()
            for value in colvalues:
                value = element.translate(value)
                if value:
                    if isinstance(value, set):
                        have.update(value)
                    else:
                        have.add(value)
        else:
            for translation in self.translations:
                if translation.match:
                    have.add(translation.match)
        if self.ignore_case:
            have = set([value.lower() for value in have])
        #print >> sys.stderr, 'HERE', colvalues, have, want
        return have - want

    def get_field_options_sorted(self, colvalues=None):
        options = list(self.get_missing_field_options(colvalues))
        options.sort()
        return options

    def add_field_opts(self, colvalues=None):
        inp = [(-len(o), o) 
                   for o in self.get_missing_field_options(colvalues)]
        inp.sort()
        for l, inp in inp:
            to = ''
            for opt, label in self.field_options:
                if opt.lower() == inp.lower():
                    to = opt
            self.translations.append(Translate(match=inp, to=to))

    def set_action(self, action_name):
        for action in self.actions:
            action.selected = (action.action_name == action_name)
            if action.selected:
                self.selected = action

    def add_translate(self, regexp=False):
        cls = Translate
        if regexp:
            cls = RegExp
        if self.translations:
            proto = self.translations[-1]
            translate = cls(ignorecase=proto.ignorecase)
        else:
            translate = cls()
        self.translations.append(translate)

    def del_translate(self, n):
        del self.translations[n]

    def to_element(self):
        element = self.selected.to_element(self.name)
        for translation in self.translations:
            if translation.match and translation.to != CHOOSE:
                element.translation(translation.to_element())
        if self.case != 'unchanged':
            element.translation(elements.Case(self.case))
        if self.date_format_other:
            element.translation(elements.Date(self.date_format_other))
        elif self.date_format:
            element.translation(elements.Date(self.date_format))
        return element

    def trial_translate(self, dataimp_src):
        values = self.preview(dataimp_src)
        element = self.to_element()
        for value in values:
            element.translate(value)


class FieldView(object):
    def __init__(self, name, label, importrule):
        self.name = name
        self.label = label
        if importrule is None:
            self.action_desc = 'Not defined'
        else:
            self.action_desc = ', '.join(importrule.desc())


class GroupView(list):
    def __init__(self, name, label):
        self.name = name
        self.label = label
        self.add_options = [('', CHOOSE)]

    def add_option(self, name, label):
        self.add_options.append(('%s.%s' % (self.name, name), label))

    def add_field(self, name, label, importrule):
        self.append(FieldView(name, label, importrule))


class RulesView(list):
    skip_fields = set(('case_definition', 'case_id', 'deleted'))

    def __init__(self, importrules, demogfields, syndrome, dataimp_src=None):
        self.add_options = []           # Available forms
        unused_cols = set()             # Unused source fields

        if dataimp_src and dataimp_src.preview:
            unused_cols.update(dataimp_src.preview.col_names)

        def add_field(node, group, name, label):
            importrule = node.get(name)
            if (importrule is None 
                    or isinstance(importrule, elements.ImportIgnore)):
                group.add_option(name, label)
            else:
                group.add_field(name, label, importrule)
                col = getattr(importrule, 'src', None)
                if col:
                    unused_cols.discard(col)
                    col = getattr(importrule, 'age', None)
                    if col:
                        unused_cols.discard(col)

        fields = []
        for field in demogfields:
            if (field.name in self.skip_fields
                or not (field.show_case or field.show_person 
                        or field.show_search or field.show_result)):
                continue
            fields.append((field.label, field.name))
        fields.sort()
        group = GroupView('', 'Demographic fields')
        for label, name in fields:
            add_field(importrules, group, name, label)
        self.append(group)

        for info in syndrome.all_form_info():
            try:
                form_rules = importrules.get_form(info.name)
            except KeyError:
                self.add_options.append((info.name, info.label))
            else:
                form = info.load()
                fields = []
                for input in form.get_inputs():
                    fields.append((input.label or input.column, input.column))
                fields.sort()
                group = GroupView(info.name, info.label or info.name)
                for label, name in fields:
                    add_field(form_rules, group, name, label)
                self.append(group)

        self.unused_cols = list(unused_cols)
        self.unused_cols.sort()

        # only allow one form?
        #if importrules.has_forms():
        #    self.add_options = []
        if self.add_options:
            self.add_options.insert(0, ('', CHOOSE))


class Editor(object):
    encodings = (
        'ascii',
        'utf-8',
        'utf-16',
        'latin1',
        'iso-8859-1',
        'iso-8859-2',
        'iso-8859-3',
        'iso-8859-4',
        'iso-8859-5',
        'iso-8859-6',
        'iso-8859-7',
        'iso-8859-8',
        'iso-8859-9',
        'iso-8859-10',
        'iso-8859-11',
        'iso-8859-12',
        'iso-8859-13',
        'iso-8859-14',
        'iso-8859-15',
        'unknown',
    )
    fieldseps = ('comma', 'tab', 'vertical bar', 'unknown')
    from_fieldsep = {
        '\t': 'tab',
        ',': 'comma',
        '|': 'vertical bar',
    }
    to_fieldsep = {
        'tab': '\t',
        'comma': ',',
        'vertical bar': '|',
    }

    def __init__(self, syndrome_id, def_id, importrules):
        self.syndrome_id = syndrome_id
        self.def_id = def_id
        self.orig_importrules = importrules
        self.set_rules(importrules)

    def set_rules(self, importrules):
        self.importrules = copy.deepcopy(importrules)
        self.encoding = self.importrules.encoding
        if self.encoding not in self.encodings:
            self.encoding = 'unknown'
        self.fieldsep = self.from_fieldsep.get(self.importrules.fieldsep, 
                                               'unknown')

    def load_check(self, msgs):
        for form in self.importrules.forms():
            info = self.syndrome().form_info(form.name)
            if info is None:
                msgs.msg('err', 'Form %r no longer associated with this %s'%
                         (form.name, config.syndrome_label))
            elif info.version != form.version:
                msgs.msg('warn', 'Form %r definition has been updated - '
                                 'check import rules' % info.label)
                form.version = info.version

    def update_rules(self):
        if self.encoding != 'unknown':
            self.importrules.encoding = self.encoding
        if self.fieldsep != 'unknown':
            self.importrules.fieldsep = self.to_fieldsep[self.fieldsep]

    def syndrome(self):
        return syndrome.syndromes[self.syndrome_id]

    def demogfields(self):
        return demogfields.get_demog_fields(globals.db, self.syndrome_id)

    def view(self, dataimp_src=None):
        return RulesView(self.importrules, self.demogfields(),
                         self.syndrome(), dataimp_src)

    def add_field(self, field, src=None):
        group, field = field.split('.', 1)
        if group:
            rules = self.importrules.get_form(group)
        else:
            rules = self.importrules
        rules.add(elements.ImportSource(field, src))
        return group, field

    def add_form(self, name):
        info = self.syndrome().form_info(name)
        self.importrules.new_form(info.name, info.version)

    def del_form(self, name):
        self.importrules.del_form(name)

    def edit_field(self, group, name):
        if group:
            form_rules = self.importrules.get_form(group)
            form = self.syndrome().form_info(group).load()
            input = form.columns.find_input(name)
            return EditField.form(group, input, form_rules[name])
        else:
            demogfield = self.demogfields().field_by_name(name)
            return EditField.demog(demogfield, self.importrules[name])

    def save_edit_field(self, edit_field):
        if edit_field.group:
            rules = self.importrules.get_form(edit_field.group)
        else:
            rules = self.importrules
        rules.add(edit_field.to_element())

    def has_changed(self):
        self.update_rules()
        return self.orig_importrules != self.importrules

    def revert(self):
        self.set_rules(self.orig_importrules)

    def rules_xml(self):
        f = StringIO()
        xmlsave.xmlsave(f, self.importrules)
        return f.getvalue()

    def save(self):
        self.update_rules()
        if self.def_id is None:
            row = None
        else:
            query = globals.db.query('import_defs', for_update=True)
            query.where('syndrome_id = %s', self.syndrome_id)
            query.where('import_defs_id = %s', self.def_id)
            row = query.fetchone()
        # New (or missing)?
        if row is None:
            row = globals.db.new_row('import_defs')
            row.syndrome_id = self.syndrome_id
        # Check there isn't a name conflict
        query = globals.db.query('import_defs', for_update=True)
        query.where('syndrome_id = %s', self.syndrome_id)
        if self.def_id is not None:
            query.where('import_defs_id != %s', self.def_id)
        query.where('name = %s', self.importrules.name)
        if query.fetchcols('import_defs_id'):
            raise Error('Name %r already used' % self.importrules.name)
        # Update
        row.xmldef = self.rules_xml()
        row.name = self.importrules.name
        row.db_update()
        self.def_id = row.import_defs_id
        self.orig_importrules = copy.deepcopy(self.importrules)

    def delete(self):
        if self.def_id is not None:
            query = globals.db.query('import_defs')
            query.where('syndrome_id = %s', self.syndrome_id)
            query.where('import_defs_id = %s', self.def_id)
            query.delete()
            self.def_id = None

    def available(self):
        query = globals.db.query('import_defs', order_by='name')
        query.where('syndrome_id = %s', self.syndrome_id)
        return query.fetchcols(('import_defs_id', 'name'))


def new(syndrome_id):
    return Editor(syndrome_id, None, elements.ImportRules(''))


def load_file(msgs, syndrome_id, def_id, f):
    try:
        editor = Editor(syndrome_id, def_id, xmlload.xmlload(f))
    except xmlload.ParseError, e:
        raise Error('Unable to load import rules: %s' % e)
    else:
        editor.load_check(msgs)
        return editor


def load(msgs, syndrome_id, def_id):
    query = globals.db.query('import_defs')
    query.where('syndrome_id = %s', syndrome_id)
    query.where('import_defs_id = %s', def_id)
    row = query.fetchone()
    if row is None:
        raise Error('Import definition not found')
    return load_file(msgs, syndrome_id, def_id, StringIO(row.xmldef))
