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

from cocklebur import dbobj, utils, datetime, checkdigit
from casemgr import paged_search, person, fuzzyperson, caseaccess, \
                    demogfields, globals, resultpersons, casetags
import config

class SearchError(dbobj.DatabaseError): pass

class ResultForm:
    result_type = 'form'

    def __init__(self, summary_id):
        self.summary_id = summary_id


class SearchOrderMixin:

    orders  = [
        'surname,given_names',
        'given_names,surname',
        'onset_datetime,surname,given_names',
        'notification_datetime,surname,given_names',
        'case_id',
        'local_case_id,surname,given_names',
        'postcode,surname,given_names',
        'DOB,surname,given_names',
        'locality,surname,given_names',
    ]
    default_order = orders[0]

    def get_order_options(self):
        fields = demogfields.get_demog_fields(globals.db, self.syndrome_id)
        options = []
        for order in self.orders:
            names = order.split(',')
            try:
                field = fields.field_by_name(names[0])
            except LookupError:
                continue
            options.append((order, field.label))
        return options

    def order_by_cols(self):
        fields = demogfields.get_demog_fields(globals.db, self.syndrome_id)
        cols = []
        for name in self.order_by.split(','):
            try:
                field = fields.field_by_name(name)
            except LookupError:
                continue
            cols.append(field.name)
        return cols


class Search(SearchOrderMixin):

    persons_per_page_options = [10, 25, 50]
    saved = None

    def __init__(self, search_ops):
        self.search_ops = search_ops
        # Note that syndrome_id can be None, in which case a cross-syndrome
        # search is performed. The user can still (potentially) restrict the
        # syndrome via the search parameters (search_syndrome_id).
        self.syndrome_id = self.search_ops.syndrome_id
        self.search_syndrome_id = self.syndrome_id
        self.description = None
        self.get_prefs()
        self.tabs = self.get_demog_fields().tabs()
        self.reset()

    def get_prefs(self):
        self.fuzzy = self.search_ops.prefs.get('phonetic_search')
        self.persons_per_page = self.search_ops.prefs.get('persons_per_page')
        self.order_by = self.search_ops.prefs.get('persons_order')
        if self.order_by is None:
            self.order_by = self.default_order

    def save_prefs(self):
        prefs = self.search_ops.prefs
        prefs.set_from_str('persons_per_page', self.persons_per_page)
        prefs.set('phonetic_search', str(self.fuzzy) == 'True')
        prefs.set('persons_order', self.order_by)

    def reset(self):
        self.person = person.person()
        self.quicksearch = self.local_case_id = self.notifier_name = ''
        self.reverse = False
        self.case_status = ''
        self.case_assignment = ''
        self.tags = ''
        self.deleted = 'n'
        self.description = None
        self.result = None

    case_id_re = re.compile('\d+$')
    form_id_re = re.compile('F\d+$')

    def _search_quick(self, query, ns):
        caseaccess.acl_query(query, self.search_ops.cred, deleted=None)
        or_expr = query.sub_expr('OR')
        for substr in utils.commasplit(self.quicksearch):
            if self.case_id_re.match(substr):
                or_expr.where('case_id = %s', int(substr))
            elif dbobj.is_wild(substr):
                substr = dbobj.wild(substr)
                or_expr.where("(given_names||' '||surname) ILIKE %s", substr)
            else:
                and_expr = or_expr.sub_expr('AND')
                and_expr.where('not deleted')
                fuzzyperson.find(and_expr, *substr.split())
            or_expr.where('local_case_id ILIKE %s', substr)
        return 'Quick search: %s' % self.quicksearch

    def _search_detail(self, query, ns):
        caseaccess.acl_query(query, self.search_ops.cred, deleted=self.deleted)
        if self.case_status:
            if self.case_status == '!':
                query.where('cases.case_status IS null')
            else:
                query.where('cases.case_status = %s', self.case_status)
        if self.case_assignment:
            if self.case_assignment == '!':
                query.where('cases.case_assignment IS null')
            else:
                query.where('cases.case_assignment = %s', self.case_assignment)
        if self.local_case_id:
            query.where('cases.local_case_id ILIKE %s', 
                        dbobj.wild(self.local_case_id))
        if self.notifier_name:
            query.where('cases.notifier_name ILIKE %s', 
                        dbobj.wild(self.notifier_name))
        if self.tags:
            for tag in casetags.tags_from_str(self.tags):
                subq = query.in_select('case_id', 'case_tags')
                subq.join('JOIN tags USING (tag_id)')
                subq.where('tag = %s', tag)
        try:
            self.person.to_query(globals.db, query, self.fuzzy)
        except person.Error, e:
            raise SearchError(str(e))
        description = ''
        if ns is not None:
            summary = self.get_demog_fields().summary(ns)
            if summary:
               description = 'Terms: %s' % summary
        return description

    def search(self, ns=None):
        """
        First we build a set of candidate persons by searching
        cases and contacts, then we run the person search terms
        across that.
        """
        if self.quicksearch and self.form_id_re.match(self.quicksearch):
            id_okay, id = checkdigit.check_checkdigit(self.quicksearch[1:])
            if not id_okay:
                raise SearchError('Invalid form ID: %s', self.quicksearch)
            self.result = ResultForm(id)
            return
        order_by = self.order_by_cols()
        if self.reverse:
            order_by = [col + ' DESC' for col in order_by]
        order_by.append('notification_datetime')
        query = globals.db.query('persons', order_by=order_by)
        query.join('JOIN cases USING (person_id)')
        if (self.search_syndrome_id is not None and 
                not self.search_ops.all_syndrome_result and
                self.search_syndrome_id != 'Any'):
            query.where('syndrome_id = %s', int(self.syndrome_id))
        if self.quicksearch:
            description = self._search_quick(query, ns)
        else:
            description = self._search_detail(query, ns)
        self.result = resultpersons.ResultPersons(
            self.search_ops, query,
            initial_cols=self.order_by_cols(),
            description=description)

    def get_demog_fields(self):
        fields = demogfields.get_demog_fields(globals.db, self.syndrome_id)
        return fields.context_fields(self.search_ops.context)

    def field_label(self, name):
        fields = demogfields.get_demog_fields(globals.db, self.syndrome_id)
        return fields.field_by_name(name).label
