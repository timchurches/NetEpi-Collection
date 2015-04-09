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

from cocklebur import datetime
from cocklebur.form_ui.inputbase import OneChoiceBase

from casemgr import globals, syndrome, demogfields
from casemgr.reports.common import *

import config

TOTAL = '!TOTAL!'
HEAD = '!HEAD!'

class Axis(object):

    def __init__(self, table, col, label, options):
        assert table
        assert col
        self.table = table
        self.col = col
        self.tabcol = '%s.%s' % (table, col)
        self.label = label
        self.options = list(options)

    def filter(self, query, val):
        if val is None:
            query.where('%s is null' % self.tabcol)
        else:
            query.where('%s = %%s' % self.tabcol, val)


class DemogAxis(Axis):

    form_name = None


class FormAxis(Axis):

    def __init__(self, form_name, form_version, table, col, label, options):
        Axis.__init__(self, table, col, label, options)
        self.form_name = form_name
        self.form_version = form_version


class DummyAxis(Axis):
    
    def __init__(self):
        self.table = None
        self.form_name = None
        self.col = None
        self.tabcol = 'null'
        self.label = None
        self.options = [(TOTAL, None)]


class Tally(dict):

    def add(self, count, *key):
        self[key] = self.get(key, 0) + count


class CrossTabCount:

    render = 'crosstab'

    def __init__(self, params, syndrome_id, title, row, column, page,
                 empty_rowsncols=True,
                 empty_pages=True):
        self.params = params
        self.syndrome_id = syndrome_id
        self.title = title
        self.row = row
        self.col = column
        self.page = page
        self.empty_rowsncols = empty_rowsncols
        self.empty_pages = empty_pages
        self.form_name = None
        self.form_table = None
        self.cols = []
        for axis in (self.row, self.col, self.page):
            if axis.form_name:
                if self.form_name and self.form_name != axis.form_name:
                    raise Error('Crosstab between different forms is not '
                                'supported')
                self.form_name = axis.form_name
                self.form_table = axis.table
            if axis.table:
                self.cols.append(axis.tabcol)
                axis.options.append((None, 'Missing'))
                axis.options.append((TOTAL, 'TOTAL'))
        self.date = datetime.now()

    def get_query(self, **kwargs):
        query = globals.db.query('cases', **kwargs)
        query.join('JOIN persons USING (person_id)')
        if self.form_name:
            query.join('LEFT JOIN case_form_summary'
                       ' ON (cases.case_id=case_form_summary.case_id'
                       ' AND form_label=%s)', self.form_name)
            query.join('LEFT JOIN %s USING (summary_id)' % self.form_table)
            query.where('NOT case_form_summary.deleted')
        query.where('NOT cases.deleted')
        query.where('cases.syndrome_id = %s', self.syndrome_id)
        self.params.filter_query(query)
        return query

    def run(self):
        query = self.get_query(group_by=','.join(self.cols))
        cols = ['count(*)'] + self.cols
        data = query.fetchcols(cols)
        tally = Tally()
        if self.page.table:
            for count, row_val, col_val, page_val in data:
                tally.add(count, row_val, col_val, page_val)
                tally.add(count, row_val, TOTAL, page_val)
                tally.add(count, TOTAL, col_val, page_val)
                tally.add(count, TOTAL, TOTAL, page_val)
                tally.add(count, row_val, col_val, TOTAL)
                tally.add(count, row_val, TOTAL, TOTAL)
                tally.add(count, TOTAL, col_val, TOTAL)
                tally.add(count, TOTAL, TOTAL, TOTAL)
            if not self.empty_pages:
                self.page.options = [(val, label)
                                     for val, label in self.page.options
                                     if tally.get((TOTAL, TOTAL, val))]
        else:
            for count, row_val, col_val in data:
                tally.add(count, row_val, col_val, TOTAL)
                tally.add(count, row_val, TOTAL, TOTAL)
                tally.add(count, TOTAL, col_val, TOTAL)
                tally.add(count, TOTAL, TOTAL, TOTAL)
        if not self.empty_rowsncols:
            self.row.options = [(val, label)
                                for val, label in self.row.options
                                if tally.get((val, TOTAL, TOTAL))]
            self.col.options = [(val, label)
                                for val, label in self.col.options
                                if tally.get((TOTAL, val, TOTAL))]
        self.tally = tally

    def style(self, row, col):
        style = []
        if row == TOTAL:
            style.append('t')
        elif row == HEAD:
            style.append('b')
        if col == TOTAL:
            style.append('l')
        elif col == HEAD:
            style.append('r')
        return ' '.join(style)

    def get_key_case_ids(self, *coords):
        query = self.get_query(distinct=True)
        for axis, index in zip((self.row, self.col, self.page), coords):
            val = axis.options[int(index)][0]
            if val != TOTAL:
                axis.filter(query, val)
        return query.fetchcols('cases.case_id')

    def desc_key(self, *coords):
        desc = []
        for axis, index in zip((self.row, self.col, self.page), coords):
            index = int(index)
            if axis.options[index][0] != TOTAL:
                desc.append('%s: %s' % (axis.label, axis.options[index][1]))
        return ', '.join(desc)


class CrosstabNoneAxisParamsMeths:

    def col_options(self, form_name):
        return []

    def check(self, form_name, msgs):
        return

    def get_axis(self, form_name):
        return None

    col_options = staticmethod(col_options)
    check = staticmethod(check)
    get_axis = staticmethod(get_axis)


class CrosstabDemogAxisParamsMeths:


    def col_options(self, form_name):
        excl = ('deleted', 'tags')
        available_cols = []
        for f in self.params.demog_fields('report'):
            if f.name and f.optionexpr is not None and f.name not in excl:
                available_cols.append((f.name, f.label))
        return available_cols

    def check(self, form_name, msgs):
        if self.field:
            try:
                field = self.params.demog_fields().field_by_name(self.field)
            except KeyError:
                msgs.msg('err', '%r input no longer available' % self.field)
                self.field = ''

    def get_axis(self, form_name):
        try:
            field = self.params.demog_fields().field_by_name(self.field)
        except KeyError:
            raise Error('demographic field %r not found' % self.field)
        return DemogAxis(field.table, field.name, 
                            field.label, field.optionexpr())

    col_options = staticmethod(col_options)
    check = staticmethod(check)
    get_axis = staticmethod(get_axis)


class CrosstabFormAxisParamsMeths:

    def col_options(self, form_name):
        available_cols = []
        form = self.params.form_info(form_name).load()
        if form is not None:
            for input in form.get_inputs():
                if isinstance(input, OneChoiceBase):
                    name = input.column.lower()
                    available_cols.append((name, input.label or input.column))
        return available_cols

    def check(self, form_name, msgs):
        if self.field:
            form = self.params.form_info(form_name).load()
            try:
                input = form.columns.find_input(self.field)
            except KeyError:
                msgs.msg('err', '"%s" form "%s" input no longer available' % 
                            (form.label, self.field))
                self.field = ''
                return

    def get_axis(self, form_name):
        form = self.params.form_info(form_name).load()
        if form is None:
            raise Error('Form %r not found' % form_name)
        try:
            input = form.columns.find_input(self.field)
        except KeyError:
            raise Error('field %r on form %r not found' % 
                        (self.field, form_name))
        return FormAxis(form.name, form.version, form.table,
                        self.field, input.label, input.get_choices())

    col_options = staticmethod(col_options)
    check = staticmethod(check)
    get_axis = staticmethod(get_axis)


class CrosstabAxisParams:

    meths = {
        'none': CrosstabNoneAxisParamsMeths,
        'demog': CrosstabDemogAxisParamsMeths,
        'form': CrosstabFormAxisParamsMeths,
    }

    def __init__(self, params):
        self.params = params
        self.form_name = 'none:'
        self.field = ''

    def form_options(self):
        available = []
        available.append(('none:', 'None'))
        available.append(('demog:', 'Demographic fields'))
        for info in self.params.all_form_info():
            available.append(('form:' + info.name, info.label))
        return available

    def show_fields(self):
        return self.form_name != 'none:'

    def col_options(self):
        mode, form_name = self.form_name.split(':')
        return self.meths[mode].col_options(self, form_name)

    def get_axis(self):
        mode, form_name = self.form_name.split(':')
        return self.meths[mode].get_axis(self, form_name)

    def check(self, msgs):
        mode, form_name = self.form_name.split(':')
        self.meths[mode].check(self, form_name, msgs)

    def to_xml(self, xmlgen, name):
        mode, form_name = self.form_name.split(':')
        if mode != 'none':
            e = xmlgen.push('axis')
            e.attr('name', name)
            e.attr('type', mode)
            if mode == 'form':
                e.attr('form', form_name)
            e.attr('field', self.field)
            xmlgen.pop()


class CrosstabParams:

    show_axes = True
    empty_rowsncols = 'False'
    empty_pages = 'False'

    def init(self):
        self.row = CrosstabAxisParams(self)
        self.col = CrosstabAxisParams(self)
        self.page = CrosstabAxisParams(self)

    def set_axis(self, name, type, field='', form=''):
        if name == 'row':
            axis = self.row
        elif name == 'column':
            axis = self.col
        elif name == 'page':
            axis = self.page
        else:
            raise Error('Bad cross-tab axis name: %r' % name)
        if type not in ('none', 'demog', 'form'):
            raise Error('Bad cross-tab axis type: %r' % type)
        axis.form_name = '%s:%s' % (type, form)
        axis.field = field

    def _check(self, msgs):
        for axis in (self.row, self.col, self.page):
            axis.check(msgs)

    def report(self, cred, msgs):
        self.check(msgs)
        if msgs.have_errors():
            return
        row = self.row.get_axis()
        if row is None:
            raise Error('A row field must be selected')
        col = self.col.get_axis()
        if col is None:
            raise Error('A column field must be selected')
        page = self.page.get_axis()
        if page is None:
            page = DummyAxis()
        report = CrossTabCount(self, self.syndrome_id, self.title(cred),
                               row, col, page, 
                               empty_rowsncols=(self.empty_rowsncols == 'True'),
                               empty_pages=(self.empty_pages == 'True'))
        report.run()
        return report

    def _forms_used(self, used):
        for axis in (self.row, self.col, self.page):
            type, name = axis.form_name.split(':')
            if type == 'form':
                used.add(name)

    def _to_xml(self, xmlgen, curnode):
        e = xmlgen.push('crosstab')
        if boolstr(self.empty_rowsncols):
            e.attr('include_empty_rowsncols', 'yes')
        if boolstr(self.empty_pages):
            e.attr('include_empty_pages', 'yes')
        self.row.to_xml(xmlgen, 'row')
        self.col.to_xml(xmlgen, 'column')
        self.page.to_xml(xmlgen, 'page')
        xmlgen.pop()
