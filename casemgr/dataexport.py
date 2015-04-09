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

"""
Export row-per-case data.

This is complicated, as a case has multiple associated forms, and
multiple instances of the forms. Form instances can also be associated
with different versions of the form definition.
"""

import time
import csv
import re
try:
    set
except NameError:
    from sets import Set as set
from mx import DateTime
from cocklebur import form_ui, dbobj
from cocklebur.filename_safe import filename_safe
from casemgr import globals, caseaccess, syndrome, casetags

ctrlre = re.compile(r'[\000-\037]+')

ISO_fmt = '%Y-%m-%d %H:%M:%S'

def value_format(value, strip_newlines=False):
    if value is None:
        return ''
    elif type(value) is DateTime.DateTimeType:
        return value.strftime(ISO_fmt)
    elif isinstance(value, bool):
        if value:
            return 't'
        else:
            return ''
    value = str(value)
    if strip_newlines:
        value = ctrlre.sub(' ', value)
    return value


class Forms:

    """
    Fetch a list of forms applicable to a given syndrome.
    """

    def __init__(self, db, names):
        self.forms = []
        if names:
            query = db.query('forms', order_by='forms.name')
            query.where_in('forms.label', names)
            self.forms = query.fetchall()

    def __getitem__(self, i):
        return self.forms[i]

    def __iter__(self):
        return iter(self.forms)

    def __len__(self):
        return len(self.forms)


class FormFormatterBase:

    def __init__(self, form_name, strip_newlines):
        self.form_name = form_name
        self.strip_newlines = strip_newlines
        self.columns = ['form_id', 'form_date']
        self.columns_seen = set(self.ignore)
        self.clear()
        self.table_map = {}
        self.form_count_by_case = {}
        self.form_versions = set()
        self.form_count = None

    def seen_form(self, id, form_version):
        self.form_count_by_case[id] = self.form_count_by_case.get(id, 0) + 1
        self.form_versions.add(form_version)

    def get_form_count(self):
        return max(self.form_count_by_case.values())

    def add_form_columns(self, version):
        form = globals.formlib.load(self.form_name, version)
        self.table_map[version] = form.table
        for col in form.columns:
            if col.name not in self.columns_seen:
                self.columns.append(col.name)
                self.columns_seen.add(col.name)

    def clear(self):
        self.form_by_summ_id = {}

    def preload(self, db, version, summary_ids):
        query = db.query(self.table_map[version])
        query.where_in('summary_id', summary_ids)
        for row in query.fetchdict():
            summary_id = row['summary_id']
            row['form_id'] = form_ui.form_id(summary_id)
            self.form_by_summ_id[summary_id] = row

    def row_format(self, row):
        if row is None:
            return [''] * len(self.columns)
        return [value_format(row.get(col), self.strip_newlines)
                for col in self.columns]


form_row_formatters = {}

class FormFormatterClassic(FormFormatterBase):

    ignore = 'case_id', 'summary_id', 'form_date'

    def col_labels(self):
        self.form_count = self.get_form_count()
        for form_version in self.form_versions:
            self.add_form_columns(form_version)
        if self.form_count == 1:
            return ['%s.%s' % (self.form_name, col) for col in self.columns]
        else:
            return ['%s.%s.%d' % (self.form_name, col, inst) 
                    for inst in range(self.form_count)
                    for col in self.columns]

    def col_values(self, summ_ids):
        values = []
        for i in range(self.form_count):
            row = None
            if i < len(summ_ids):
                row = self.form_by_summ_id.get(summ_ids[i][1])
            values.extend(self.row_format(row))
        return values

form_row_formatters['classic'] = FormFormatterClassic


class FormFormatterDoHA(FormFormatterBase):

    ignore = 'case_id', 'form_date'

    def col_labels(self):
        self.form_count = self.get_form_count()
        for form_version in self.form_versions:
            self.add_form_columns(form_version)
        labels = []
        for i in range(self.form_count):
            labels.extend(['form_label', 'form_version'])
            if self.form_count == 1:
                labels.extend(self.columns)
            else:
                for col in self.columns:
                    labels.append('%s%d' % (col, i))
        return labels

    def col_values(self, summ_ids):
        values = []
        for i in range(self.form_count):
            values.append(self.form_name)
            row = None
            if i < len(summ_ids):
                row = self.form_by_summ_id.get(summ_ids[i][1])
            if row is None:
                values.append('')
            else:
                values.append(summ_ids[i][0])
            values.extend(self.row_format(row))
        return values

form_row_formatters['doha'] = FormFormatterDoHA


class FormFormatterForm(FormFormatterBase):
    ignore = ()

    def col_labels(self):
        self.form_count = self.get_form_count()
        for form_version in self.form_versions:
            self.add_form_columns(form_version)
        return ['%s.%s' % (self.form_name, col) for col in self.columns]

    def col_values(self, summ_ids):
        for form_version, summ_id in summ_ids:
            yield self.row_format(self.form_by_summ_id.get(summ_id))

form_row_formatters['form'] = FormFormatterForm


class RowFormatterBase(object):

    def __init__(self, format, strip_newlines=False):
        self.forms_by_name = {}
        self.include_forms = None
        self.case_cols = None
        self.fetch_cols = ('cases.*', 'persons.*')
        self.form_formatter = form_row_formatters[format]
        self.strip_newlines = strip_newlines

    def seen_form(self, id, form_name, form_version):
        try:
            form = self.forms_by_name[form_name]
        except KeyError:
            form = self.form_formatter(form_name, self.strip_newlines)
            self.forms_by_name[form_name] = form
        form.seen_form(id, form_version)

    def _get_case_cols(self, db):
        if self.case_cols is None:
            query = db.query('cases', limit=0)
            query.join('JOIN persons USING (person_id)')
            curs = db.cursor()
            try:
                query.execute(curs, self.fetch_cols)
                self.case_cols = dbobj.cursor_cols(curs)
            finally:
                curs.close()
            # Remove duplicate person_id (cases refs persons).
            self.case_cols.remove('person_id')
            # Remove duplicate update_time (on cases, and on persons)
            self.case_cols.remove('last_update')
            self.case_cols.remove('last_update')

    def set_include_forms(self, include_forms):
        self.include_forms = include_forms

    def preload(self, db, cases):
        id_idx = self.case_cols.index('case_id')
        query = db.query('cases')
        query.join('JOIN persons USING (person_id)')
        query.where_in('case_id', [case.id for case in cases])
        self.cases = {}
        for row in query.fetchcols(self.case_cols):
            self.cases[row[id_idx]] = row
        self.cases_tags = casetags.CasesTags(self.cases.keys())
        for name in self.include_forms:
            self.forms_by_name[name].clear()
        formvers_summids = ExportCase.summid_by_form_version(cases, 
                                                             self.include_forms)
        for (form_name, form_version), summ_ids in formvers_summids:
            form = self.forms_by_name[form_name]
            form.preload(db, form_version, summ_ids)

    def col_labels(self, db):
        self._get_case_cols(db)
        labels = list(self.case_cols)
        labels.append('tags')
        for name in self.include_forms:
            labels.extend(self.forms_by_name[name].col_labels())
        return labels


row_formatters = {}

class RowPerCaseFormatter(RowFormatterBase):

    def rows(self, cases):
        for case in cases:
            values = [value_format(value, self.strip_newlines)
                      for value in self.cases[case.id]]
            values.append(str(self.cases_tags.get(case.id, '')))
            summid_by_form = case.summid_by_form()
            for name in self.include_forms:
                form_fmt = self.forms_by_name[name]
                summids = summid_by_form.get(form_fmt.form_name, [])
                values.extend(form_fmt.col_values(summids))
            yield values



row_formatters['classic'] = RowPerCaseFormatter
row_formatters['doha'] = RowPerCaseFormatter


class RowPerFormFormatter(RowFormatterBase):

    def set_include_forms(self, include_forms):
        if len(include_forms) != 1:
            raise globals.Error('Must select one (and only one) form')
        self.include_forms = include_forms

    def rows(self, cases):
        assert len(self.include_forms) == 1
        form_fmt = self.forms_by_name[self.include_forms[0]]
        for case in cases:
            case_cols = [value_format(value, self.strip_newlines)
                         for value in self.cases[case.id]]
            case_cols.append(str(self.cases_tags.get(case.id, '')))
            summid_by_form = case.summid_by_form()
            summids = summid_by_form.get(form_fmt.form_name, [])
            for form_cols in form_fmt.col_values(summids):
                yield case_cols + form_cols

row_formatters['form'] = RowPerFormFormatter


class ExportCase:
    """
    Represents a case to be exported, recording information about form
    instances associated with the case.
    """
    def __init__(self, id):
        self.id = id
        self.forms = []

    def add_summ_id(self, summary_id, form_name, form_version):
        self.forms.append((summary_id, form_name, form_version))

    def summid_by_form(self):
        summids = {}
        for summary_id, form_name, form_version in self.forms:
            form_summids = summids.setdefault(form_name, [])
            form_summids.append((form_version, summary_id))
        return summids

    def summid_by_form_version(cases, include_forms):
        summid_by = {}
        for case in cases:
            for summary_id, form_name, form_version in case.forms:
                if form_name in include_forms:
                    key = form_name, form_version
                    summid_by.setdefault(key, []).append(summary_id)
        return summid_by.items()
    summid_by_form_version = staticmethod(summid_by_form_version)


class ExportCases:
    """
    This class records info about relevent cases, and returns them in
    bite-sized chunks.
    """
    def __init__(self):
        self.cases_in_order = []
        self.cases_by_id = {}

    def add_summ_id(self, id, summary_id, form_name, form_version):
        try:
            export_case = self.cases_by_id[id]
        except KeyError:
            export_case = ExportCase(id)
            self.cases_by_id[id] = export_case
            self.cases_in_order.append(export_case)
        if summary_id is not None:
            export_case.add_summ_id(summary_id, form_name, form_version)

    def yield_chunks(self, chunksize=1000):
        i = 0
        while i < len(self.cases_in_order):
            yield self.cases_in_order[i:i+chunksize]
            i += chunksize

    def __len__(self):
        return len(self.cases_in_order)


class CaseExporter:

    def __init__(self, credentials, syndrome_id,
                 format='classic',
                 deleted='n',
                 strip_newlines=False):
        self.credentials = credentials
        self.syndrome_id = syndrome_id
        self.format = format
        self.strip_newlines = strip_newlines
        # Collect names of all forms *in use* for this syndrome
        # as well as summary_ids, etc
        query = globals.db.query('cases', distinct=True)
        query.join('LEFT JOIN case_form_summary USING (case_id)')
        query.where('syndrome_id = %s', syndrome_id)
        if deleted != 'n':
            query.where('NOT case_form_summary.deleted')
        caseaccess.acl_query(query, self.credentials, deleted=deleted)
        forms_used = set()
        self.export_cases = ExportCases()
        row_formatter_cls = row_formatters[self.format]
        self.row_formatter = row_formatter_cls(self.format, self.strip_newlines)
        rows = query.fetchcols(('cases.case_id', 
                                'summary_id', 'form_label', 'form_version'))
        for case_id, summary_id, form_name, form_version in rows:
            self.export_cases.add_summ_id(case_id, summary_id,
                                          form_name, form_version)
            if summary_id is not None:
                self.row_formatter.seen_form(case_id, form_name, form_version)
                forms_used.add(form_name)
        self.forms = Forms(globals.db, forms_used)

    def entity_info(self):
        count = len(self.export_cases)
        if count == 0:
            return 'are no records'
        elif count == 1:
            return 'is 1 record'
        else:
            return 'are %s records' % count

    def filename(self):
        syndrome_name = filename_safe(syndrome.syndromes[self.syndrome_id].name)
        return 'nec-%s-%s.csv' % (syndrome_name,
                                 time.strftime('%Y%m%d-%H%M'))

    def row_gen(self, include_forms):
        self.row_formatter.set_include_forms(include_forms)
        yield self.row_formatter.col_labels(globals.db)
        for cases in self.export_cases.yield_chunks():
            self.row_formatter.preload(globals.db, cases)
            for row in self.row_formatter.rows(cases):
                yield row

    def csv_write(self, include_forms, f):
        csv.writer(f).writerows(self.row_gen(include_forms))


class ContactExporter:

    forms = None

    def __init__(self, credentials, syndrome_id,
                 format='classic',
                 deleted='n',
                 strip_newlines=False):
        self.syndrome_id = syndrome_id
        self.credentials = credentials
        self.format = format
        self.strip_newlines = strip_newlines
        self.deleted = deleted

    def filename(self):
        syndrome_name = filename_safe(syndrome.syndromes[self.syndrome_id].name)
        return 'nec-contacts-%s-%s.csv' % (syndrome_name,
                                 time.strftime('%Y%m%d-%H%M'))

    def row_gen(self, include_forms):
        yield 'id_a', 'id_b', 'contact_type', 'contact_date'
        query = globals.db.query('case_contacts')
        query.join('JOIN cases USING (case_id)')
        query.join('LEFT JOIN contact_types USING (contact_type_id)')
        query.where('case_id < contact_id')
        caseaccess.acl_query(query, self.credentials, deleted=self.deleted)
        cols = 'case_id', 'contact_id', 'contact_type', 'contact_date'
        for row in query.fetchcols(cols):
            if row[-1]:
                row = row[:-1] + (row[-1].strftime(ISO_fmt),)
            yield row

    def csv_write(self, include_forms, f):
        csv.writer(f).writerows(self.row_gen(include_forms))
