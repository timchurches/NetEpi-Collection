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

import sys
import re
try:
    set
except NameError:
    from sets import Set as set

from casemgr import globals
from casemgr import casetags
from casemgr.reports.common import *


class NS: pass


class Preload(dict):

    def __init__(self, colnames, query, keycol, values):
        keyindex = colnames.index(keycol)
        query.where_in(keycol, values)
        for row in query.fetchcols(colnames):
            ns = NS()
            for colname, value in zip(colnames, row):
                setattr(ns, colname, value)
            key = row[keyindex]
            self[row[keyindex]] = ns


class DemogInfo(object):

    def __init__(self, out_group):
        self.name = None
        columns = set(out_group.shared_columns)
        try:
            columns.remove('tags')
        except KeyError:
            self.load_tags = False
        else:
            self.load_tags = True
        self.columns = list(columns)
        self.instance_count = 1

    def preload(self, case_ids):
        query = globals.db.query('cases')
        query.join('JOIN persons USING (person_id)')
        preload = Preload(self.columns, query, 'case_id', case_ids)
        if self.load_tags:
            cases_tags = casetags.CasesTags(case_ids)
            for ns in preload.itervalues():
                tags = cases_tags.get(ns.case_id)
                if tags:
                    ns.tags = str(tags)
        return preload


class FormInfo(object):
    # This object holds per-form info on:
    #  * per-case summary_id lists
    #  * max per-case instance counts

    def __init__(self, out_group):
        self.name = out_group.form_name
        self.version = out_group.form_version
        self.table = out_group.table
        self.columns = list(out_group.shared_columns)
        self.instance_count = 0
        self.summ_by_case = {}

    def add_summary(self, case_id, summary_id, version):
        if self.version != version:
            return        # XXX Error out? Ignore?
        try:
            case_form_summ = self.summ_by_case[case_id]
        except KeyError:
            case_form_summ = self.summ_by_case[case_id] = [summary_id]
        else:
            case_form_summ.append(summary_id)
        if len(case_form_summ) > self.instance_count:
            self.instance_count = len(case_form_summ)

    def summ_for_cases(self, case_ids):
        summ_for_cases = []
        for case_id in case_ids:
            try:
                summ_for_cases.extend(self.summ_by_case[case_id])
            except KeyError:
                continue
        return summ_for_cases

    def preload(self, case_ids):
        summ_ids = []
        for case_id in case_ids:
            case_summ = self.summ_by_case.get(case_id)
            if case_summ is not None:
                summ_ids.extend(case_summ)
        query = globals.db.query(self.table)
        return Preload(self.columns, query, 'summary_id', summ_ids)


class ReportExportBase(object):

    chunk_size = 500

    def __init__(self, params, case_ids, 
                       field_labels=True, strip_newlines=True):
        self.params = params
        self.case_ids = case_ids
        self.field_labels = field_labels
        self.strip_newlines = strip_newlines
        self.init()
        if self.forms:
            self.scan_summaries()

    def init(self):
        self.out_groups = self.params.get_output_rows()
        self.info_by_form = {}
        self.info_by_form[None] = DemogInfo(self.out_groups[0])
        self.forms = set()
        for out_group in self.out_groups:
            if not out_group.form_name:
                continue
            self.forms.add(out_group.form_name)
            try:
                form_info = self.info_by_form[out_group.form_name]
                assert out_group.form_version == form_info.version
            except KeyError:
                self.info_by_form[out_group.form_name] = FormInfo(out_group)

    def scan_summaries(self):
        query = globals.db.query('case_form_summary',
                                 order_by='form_date, summary_id')
        query.where('NOT deleted')
        query.where_in('form_label', self.forms)
        query.where_in('case_id', self.case_ids)
        cols = 'case_id', 'summary_id', 'form_label', 'form_version'
        for case_id, summ_id, form_name, form_version in query.fetchcols(cols):
            form_info = self.info_by_form[form_name]
            form_info.add_summary(case_id, summ_id, form_version)

    def outgroup_labels(self, out_group):
        if self.field_labels:
            return out_group.labels()
        elif out_group.form_name:
            return ['%s.%s' % (out_group.form_name, column)
                    for column in out_group.columns]
        else:
            return out_group.columns

    def yield_chunks(self):
        for offs in range(0, len(self.case_ids), self.chunk_size):
            yield self.case_ids[offs:offs+self.chunk_size]

    def preload(self, case_ids):
        preloads = {}
        for info in self.info_by_form.values():
            preloads[info.name] = info.preload(case_ids)
        return preloads

    ctrlre = re.compile(r'[\000-\037]+')

    def render(self, out_group, ns):
        if ns is None:
            fields = [None] * len(out_group.fields)
        else:
            fields = out_group.as_list(ns)
            if self.strip_newlines:
                fields = [self.ctrlre.sub(' ', f) for f in fields]
        return fields


class ExportForms(ReportExportBase):

    def init(self):
        super(ExportForms, self).init()
        self.summ_by_case = {}
        if self.forms:
            if len(self.forms) != 1:
                raise Error('By-form export requires at most one form')
            form_name, = self.forms
            self.summ_by_case = self.info_by_form[form_name].summ_by_case

    def header(self):
        header = []
        for out_group in self.out_groups:
            header.extend(self.outgroup_labels(out_group))
        return header

    def __iter__(self):
        yield self.header()
        missing_form = [None]
        for case_ids in self.yield_chunks():
            preloads = self.preload(case_ids)
            for case_id in case_ids:
                summary_ids = self.summ_by_case.get(case_id, missing_form)
                for summary_id in summary_ids:
                    row = []
                    for out_group in self.out_groups:
                        if out_group.form_name:
                            key = summary_id
                        else:
                            key = case_id
                        ns = preloads[out_group.form_name].get(key)
                        if ns is None:
                            fields = [None] * len(out_group.fields)
                        else:
                            fields = out_group.as_list(ns)
                        row.extend(fields)
                    yield row


class ExportCases(ReportExportBase):

    def header(self):
        header = []
        if self.field_labels:
            fmt = '%s (%s)'
        else:
            fmt = '%s.%s'
        for out_group in self.out_groups:
            labels = self.outgroup_labels(out_group)
            inst_cnt = self.info_by_form[out_group.form_name].instance_count
            if inst_cnt > 1:
                for n in range(1, inst_cnt+1):
                    for label in labels:
                        header.append(fmt % (label, n))
            else:
                header.extend(labels)
        return header

    def __iter__(self):
        yield self.header()
        for case_ids in self.yield_chunks():
            preloads = self.preload(case_ids)
            for case_id in case_ids:
                row = []
                for out_group in self.out_groups:
                    info = self.info_by_form[out_group.form_name]
                    if info.name:
                        keys = info.summ_by_case.get(case_id, ())
                    else:
                        keys = [case_id]
                    for index in range(info.instance_count):
                        try:
                            key = keys[index]
                        except IndexError:
                            ns = None
                        else:
                            ns = preloads[info.name].get(key)
                        if ns is None:
                            fields = [None] * len(out_group.fields)
                        else:
                            fields = out_group.as_list(ns)
                        row.extend(fields)
                yield row
