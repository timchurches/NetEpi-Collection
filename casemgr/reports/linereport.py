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
import sys
from itertools import izip

from cocklebur import form_ui

from casemgr import globals, casetags
from casemgr.reports.common import *

debug = 0

def get_formdata_by_case(output_rows, case_ids):
    forms = []
    summids_by_form = {}
    for og in output_rows:
        if og.form_name:
            summids_by_form[(og.form_name, og.form_version)] = []
            forms.append(og.form_name)
    if not case_ids or not summids_by_form:
        return {}
    query = globals.db.query('case_form_summary', order_by='form_date')
    query.where('NOT deleted')
    query.where_in('form_label', forms)
    query.where_in('case_id', case_ids)
    formdata_by_summid = {}
    summids_by_case_by_form = {}
    for case_id in case_ids:
        summids_by_case_by_form[case_id] = {}
    # Fetch summary_id for cases
    cols = 'case_id', 'form_label', 'form_version', 'summary_id'
    for case_id, name, version, summary_id in query.fetchcols(cols):
        case_form_summids = summids_by_case_by_form[case_id]
        try:
            summids_by_form[(name, version)].append(summary_id)
        except KeyError:
            formdata_by_summid[summary_id] = 'Omitted data from incompatible form %r, version %s' % (name, version)
        case_form_summids.setdefault(name, []).append(summary_id)
    # Now fetch form data by form
    for (form_name, form_version), summids in summids_by_form.iteritems():
        if summids:
            table = globals.formlib.tablename(form_name, form_version)
            cols = output_rows.tablecols(table)
            query = globals.db.query(table)
            query.where_in('summary_id', summids)
            for formdata in query.fetchcols(cols):
                formdata = dict(izip(cols, formdata))
                formdata_by_summid[formdata['summary_id']] = formdata
    if debug: print >> sys.stderr, '%d cases, %d forms, %d summaries' % (len(case_ids), len(summids_by_form), len(formdata_by_summid))
    # Now collate form data by cases
    formdata_by_case_by_form = {}
    for case_id in case_ids:
        case_formdata = formdata_by_case_by_form.setdefault(case_id, {})
        case_form_summids = summids_by_case_by_form[case_id]
        for og in output_rows:
            if og.form_name:
                form_formdata = case_formdata.setdefault(og.form_name, [])
                form_summids = case_form_summids.get(og.form_name, [])
                for summid in form_summids:
                    try:
                        form_formdata.append(formdata_by_summid[summid])
                    except KeyError:
                        pass
    return formdata_by_case_by_form


class GenCase:
    def __init__(self, id):
        self.id = id
        self.columns = None
        self.freetext = []

    def addtext(self, label, text, key=''):
        if text:
            self.freetext.append((key, label, text))

class NS:
    def __init__(self, vars):
        self.__dict__ = vars

class ReportChunks:
    render = 'table'
    chunk_size = 100

    def __init__(self, reportparams, case_ids):
        self.init(reportparams, case_ids)

    def init(self, reportparams, case_ids):
        self.params = reportparams
        self.case_ids = case_ids
        self.__preload = None
        self.__preload_offset = 0
        self.output_rows = reportparams.get_output_rows()
        self.n_cols = len(self.output_rows[0].labels())
        self.caseperson_cols = list(self.output_rows.tablecols('caseperson'))
        self.load_tags = 'tags' in self.caseperson_cols
        if self.load_tags:
            self.caseperson_cols.remove('tags')

    def __getstate__(self):
        return self.params, self.case_ids

    def __setstate__(self, state):
        self.init(*state)

    def __len__(self):
        return len(self.case_ids)

    def headings(self):
        return self.output_rows[0].labels()

    def load_chunk(self, offset):
        window = self.case_ids[offset:offset+self.chunk_size]
        if not window:
            raise IndexError
        formdata = get_formdata_by_case(self.output_rows, window)
        query = globals.db.query('cases')
        query.join('JOIN persons USING (person_id)')
        query.where_in('case_id', window)
        self.__preload = {}
        self.__preload_offset = offset
        if self.load_tags:
            cases_tags = casetags.CasesTags(window)
        for caseperson in query.fetchcols(self.caseperson_cols):
            caseperson = dict(izip(self.caseperson_cols, caseperson))
            case_id = caseperson['case_id']
            if self.load_tags:
                tags = cases_tags.get(case_id)
                if tags:
                    caseperson['tags'] = str(tags)
            gencase = self.__preload[case_id] = GenCase(case_id)
            gencase.columns = self.output_rows[0].as_list(NS(caseperson))
            for og in self.output_rows[1:]:
                if not og.form_name:
                    gencase.addtext(og.label, og.as_text(NS(caseperson)),
                                    case_id)
                else:
                    for values in formdata[case_id][og.form_name]:
                        if isinstance(values, basestring):
                            gencase.addtext(None, values)
                        else:
                            form_id = form_ui.form_id(values['summary_id'])
                            gencase.addtext('%s %s' % (og.label, form_id), 
                                            og.as_text(NS(values)), form_id)

    def __getitem__(self, i):
        if (self.__preload is None or i < self.__preload_offset 
                or i >= self.__preload_offset + self.chunk_size):
            self.load_chunk(i)
        try:
            return self.__preload[self.case_ids[i]]
        except KeyError:
            # This should not happen
            res = GenCase(self.case_ids[i])
            res.addtext(None, 'System Case ID %s not found' % self.case_ids[i])
            return res
