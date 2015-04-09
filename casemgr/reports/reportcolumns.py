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

from cocklebur import agelib
from casemgr import globals
from casemgr.reports.common import *

import config

class LineOutGenBase:

    def __init__(self, outgroup):
        self.label = outgroup.label
        self.form_name = None
        self.table = None
        self.columns = []
        self.fields = []

    def get_table_columns(self):
        return self.table, self.columns

    def labels(self):
        return [label for label, column, outtrans in self.fields]

    def as_text(self, ns):
        result = []
        for label, column, outtrans in self.fields:
            value = outtrans(ns)
            if value is not None:
                result.append('%s: %s' % (label, value))
        return ', '.join(result)

    def as_list(self, ns):
        return [outtrans(ns) for label, column, outtrans in self.fields]


class DemogLineOut(LineOutGenBase):

    def __init__(self, outgroup):
        LineOutGenBase.__init__(self, outgroup)
        self.table = 'caseperson'
        field_by_name = outgroup.params.demog_fields().field_by_name
        for og in outgroup:
            if og.name == 'DOB_only':
                def DOB_outtrans(ns):
                    return agelib.dob_if_dob(ns.DOB, ns.DOB_prec)
                self.columns.extend(['DOB', 'DOB_prec'])
                self.fields.append((og.label, None, DOB_outtrans))
            elif og.name == 'age':
                def Age_outtrans(ns):
                    return agelib.agestr(ns.DOB)
                self.columns.extend(['DOB', 'DOB_prec'])
                self.fields.append((og.label, None, Age_outtrans))
            else:
                demog_field = field_by_name(og.name)
                column = demog_field.field_result
                self.columns.append(column)
                if demog_field.name == 'DOB':
                    self.columns.append('DOB_prec')
                self.fields.append((og.label, column, demog_field.outtrans))


class FormLineOut(LineOutGenBase):

    def __init__(self, outgroup):
        LineOutGenBase.__init__(self, outgroup)
        info = outgroup.form_info()
        self.form_name = info.name
        self.form_version = info.version
        info.load()
        self.table = info.tablename()
        form = info.load()
        for og in outgroup:
            input = form.columns.find_input(og.name)
            columns = input.get_column_names()
            self.columns.extend(columns)
            if len(columns) == 1:
                columns = columns[0]
            else:
                columns = tuple(columns)
            self.fields.append((og.label, columns, input.outtrans))


class OutputRows(list):

    def __init__(self, reportparams):
        self.cols_by_table = {
            'caseperson': set(['case_id'])
        }
        for outgroup in reportparams.outgroups:
            lineout = outgroup.get_outgen()
            self.append(lineout)
            table, cols = lineout.get_table_columns()
            try:
                table_cols = self.cols_by_table[table]
            except KeyError:
                table_cols = self.cols_by_table[table] = set(['summary_id'])
            table_cols.update(cols)
            lineout.shared_columns = table_cols

    def tablecols(self, table):
        return self.cols_by_table[table]


class ReportCol:

    def __init__(self, report_columns, name, label=None):
        self.report_columns = report_columns
        self.name = name
        if label is None:
            label = self.canonical_label()
        self.label = label

    def canonical_label(self):
        return self.report_columns.canonical_label(self.name)

    def to_xml(self, xmlgen):
        e = xmlgen.push('column')
        e.attr('name', self.name)
        e.attr('label', self.label)
        xmlgen.pop()


class ReportColsBase(list):

    addcol = None
    form_name = None
    is_caseperson = False
    is_form = False

    def __init__(self, params, label):
        self.params = params
        self.label = label
        self.initial_label = label

    def colop(self, op, index=None):
        if op == 'up':
            if index > 0:
                self[index], self[index - 1] = self[index - 1], self[index]
        elif op == 'dn':
            if index < len(self) - 1:
                self[index], self[index + 1] = self[index + 1], self[index]
        elif op == 'del':
            del self[index]
        elif op == 'clear':
            del self[:]

    def add(self, name, label=None):
        self.append(ReportCol(self, name, label))

    def cols_update(self):
        if self.addcol:
            if self.addcol.startswith('!'):
                name = self.addcol[1:]
                meth = getattr(self, 'add_' + name, None)
                if meth is not None:
                    meth()
            else:
                for name in self.addcol.split(','):
                    self.add(name)
            self.addcol = None

    def names(self):
        return [c.name for c in self]

    def labels(self):
        return [c.label for c in self]

    def _check(self, msgs):
        pass


class DemogCols(ReportColsBase):

    combos = [
        ('surname,given_names', 'Surname and given names'),
        ('home_phone,work_phone,mobile_phone', 'Phone numbers'),
        ('street_address,locality,state,postcode', 'Primary address'),
        ('alt_street_address,alt_locality,alt_state,alt_postcode', 
            'Secondary address'),
    ]
    is_caseperson = True

    def canonical_label(self, name):
        if name == 'DOB_only':
            return 'Date of birth'
        elif name == 'age':
            return 'Age'
        return self.params.demog_fields().field_by_name(name).label

    def available_cols(self): 
        used = set(self.names())
        used.add('case_definition')
        avail = set()
        for f in self.params.demog_fields('report'):
            if getattr(f, 'field_result', None):
                avail.add(f.name)
        avail_cols = [('', '- Choose a field -')]
        for cols, label in self.combos:
            fields = [f for f in cols.split(',') if f in avail]
            if fields:
                for col in fields:
                    if col in used:
                        break
                else:
                    avail_cols.append((','.join(fields), label))
        other_cols = []
        if 'DOB' in avail:
            other_cols.append(('Date of birth', 'DOB_only'))
            other_cols.append(('Age', 'age'))
        for f in self.params.demog_fields('report'):
            if f.name not in used and getattr(f, 'field_result', None):
                other_cols.append((f.label, f.name))
        other_cols.sort()
        for l, n in other_cols:
            avail_cols.append((n, l))
        return avail_cols

    def get_outgen(self):
        return DemogLineOut(self)

    def to_xml(self, xmlgen):
        e = xmlgen.push('group')
        e.attr('type', 'demog')
        e.attr('label', self.label)
        for c in self:
            c.to_xml(xmlgen)
        xmlgen.pop()


class FormCols(ReportColsBase):

    is_form = True
    common_avail = [
        ('', '- Choose a field -'),
        ('!all', '- All fields -'),
        ('!summary', '- Summary fields -'),
    ]

    def __init__(self, params, label, form_name):
        ReportColsBase.__init__(self, params, label)
        self.form_name = form_name

    def form_info(self):
        return self.params.form_info(self.form_name)

    def getinput(self, name):
        return self.form_info().load().columns.find_input(name)

    def canonical_label(self, name):
        input = self.getinput(name)
        return input.label or input.column

    def available_cols(self): 
        used = set(self.names())
        avail_cols = list(self.common_avail)
        other_cols = []
        for input in self.form_info().load().get_inputs():
            name = input.column.lower()
            if name not in used:
                other_cols.append((input.label or input.column, name))
        other_cols.sort()
        for l, n in other_cols:
            avail_cols.append((n, l))
        return avail_cols

    def add_all(self): 
        used = set(self.names())
        for input in self.form_info().load().get_inputs():
            name = input.column.lower()
            if name not in used:
                self.add(name, input.label or input.column)

    def add_summary(self): 
        used = set(self.names())
        for input in self.form_info().load().get_inputs():
            name = input.column.lower()
            if name not in used and input.label:
                self.add(name, input.label)

    def get_outgen(self):
        return FormLineOut(self)

    def _check(self, msgs):
        form = self.form_info().load()
        new_cols = []
        for c in self:
            try:
                form.columns.find_input(c.name)
            except KeyError:
                msgs.msg('err', 'Form %r has been updated, report field %r has '
                                'been deleted' % (form.label, c.label))
            else:
                c.name = c.name.lower()
                new_cols.append(c)
        if self != new_cols:
            self[:] = new_cols

    def to_xml(self, xmlgen):
        e = xmlgen.push('group')
        e.attr('type', 'form')
        e.attr('form', self.form_name)
        e.attr('label', self.label)
        for c in self:
            c.to_xml(xmlgen)
        xmlgen.pop()


class OutcolsParamsMixin:

    show_columns = True

    def init(self):
        self.outgroups = []

    def _defaults(self, msgs):
        if not self.outgroups:
            stoplist = set(('case_definition', 'deleted'))
            cols = DemogCols(self, 'Columns')
            for field in self.demog_fields('report'):
                if field.show_result and field.name not in stoplist:
                    cols.add(field.name)
            self.outgroups.append(cols)
            self.outgroups.append(DemogCols(self, 'Additional information'))

    def has_up(self, i):
        return (i > 1 
                and self.outgroups[i-1].is_form == self.outgroups[i].is_form)

    def has_dn(self, i):
        return (i > 0 and i < (len(self.outgroups) - 1)
                and self.outgroups[i+1].is_form == self.outgroups[i].is_form)

    def colop(self, op, group_idx, col_idx=None):
        if op == 'gup':
            if self.has_up(group_idx):
                self.outgroups[group_idx], self.outgroups[group_idx - 1] =\
                    self.outgroups[group_idx - 1], self.outgroups[group_idx]
        elif op == 'gdn':
            if self.has_dn(group_idx):
                self.outgroups[group_idx], self.outgroups[group_idx + 1] =\
                    self.outgroups[group_idx + 1], self.outgroups[group_idx]
        elif op == 'gdel':
            if group_idx > 0:
                del self.outgroups[group_idx]
        else:
            return self.outgroups[group_idx].colop(op, col_idx)

    def _cols_update(self):
        for outgroup in self.outgroups:
            outgroup.cols_update()

    def available_col_forms(self):
        if not config.form_rollforward:
            return []
        available = [('', '- Choose a form -')]
        for info in self.all_form_info():
            available.append((info.name, info.label))
        return available

    def add_caseperson(self):
        cols = DemogCols(self, 'Additional information')
        for i, outgroup in enumerate(self.outgroups):
            if outgroup.is_form:
                self.outgroups.insert(i, cols)
                break
        else:
            self.outgroups.append(cols)

    def add_form(self, add_name):
        info = self.form_info(add_name)
        if info is not None:
            self.outgroups.append(FormCols(self, info.label, info.name))

    def add_group(self, type, label, form=None):
        if type == 'demog':
            group = DemogCols(self, label)
        elif type == 'form':
            group = FormCols(self, label, form)
        else:
            raise Error('Unknown report group type %r' % type)
        self.outgroups.append(group)
        return group

    def get_output_rows(self):
        return OutputRows(self)

    def _check(self, msgs):
        new_outgroups = []
        for og in self.outgroups:
            if og.form_name:
                if self.form_info(og.form_name) is None:
                    continue
                og._check(msgs)
            new_outgroups.append(og)
        self.outgroups = new_outgroups

    def _forms_used(self, used):
        for outgroup in self.outgroups:
            if outgroup.form_name:
                used.add(outgroup.form_name)

    def _to_xml(self, xmlgen, curnode):
        xmlgen.push('groups')
        for outgroup in self.outgroups:
            outgroup.to_xml(xmlgen)
        xmlgen.pop()
