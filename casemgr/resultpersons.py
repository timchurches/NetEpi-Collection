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
Code to support a person-oriented view of cases, as used by the search
result pages.
"""

try:
    set
except NameError:
    from sets import Set as set

from casemgr import globals, paged_search, person, caseaccess, \
                    demogfields, casetags

class CaseSummary:
    """
    A wrapper around a case row object that presents a controllable
    summary of the row.
    """

    def __init__(self, rp, case_row):
        self.rp = rp
        self.case_row = case_row
        self.case_id = case_row.case_id
        self.syndrome_id = case_row.syndrome_id

    def summary(self):
        fields = demogfields.get_demog_fields(globals.db, self.syndrome_id)
        fields = fields.reordered_context_fields(self.rp.initial_cols, 'result')
        return fields.summary(self.case_row)

    def button(self, edit_case):
        return self.rp.search_ops.button_case(self.case_id, self.syndrome_id)


class Person(person.Person):

    def __init__(self, rp, seed_person):
        self.from_person(seed_person)
        self.rp = rp
        self.cases = []

    def summary(self):
        return person.Person.summary(self, self.rp.initial_cols)

    def button(self, case):
        return self.rp.search_ops.button_person(self.person_id)


class ResultPersons(paged_search.PagedSearch):
    result_type = 'person'

    def __init__(self, search_ops, query, initial_cols=None, description=None):
        paged_search.PagedSearch.__init__(self, globals.db, search_ops.prefs, 
                                          'persons')
        self.search_ops = search_ops
        self.initial_cols = initial_cols
        self.description = description
        self.results_per_page = self.search_ops.prefs.get('persons_per_page')
        self.fetch_pkeys(query)
        # Can't use page_search.PagerSelect logic, because we're interested in
        # case_ids, not person_ids.
        self.selected = set()
        self.page_case_ids = set()
        self.page_selected = []

    def single_case(self):
        """
        If search returned only one case, return the case_id
        """
        if len(self.pkeys) == 1:
            person_id, case_ids = self.pkeys[0]
            if len(case_ids) == 1:
                return case_ids[0]

    def fetch_pkeys(self, query):
        keys = []
        persons_keys = {}
        for person_id, case_id in query.fetchcols(('person_id', 'case_id')):
            person_keys = persons_keys.get(person_id)
            if person_keys is None:
                person_keys = persons_keys[person_id] = [case_id]
                keys.append((person_id, person_keys))
            else:
                person_keys.append(case_id)
        self.pkeys = keys

    def new_button(self):
        return self.search_ops.button_new()

    def edit_button(self):
        return self.search_ops.button_edit()

    def _page_to_selected(self):
        self.selected.difference_update(self.page_case_ids)
        for key in self.page_selected:
            self.selected.add(int(key))

    def _selected_to_page(self):
        self.page_selected = list(self.page_case_ids & self.selected)

    def select(self, select):
        self.selected = set(select)
        self._selected_to_page()

    def select_all(self):
        case_ids = set()
        for person_id, person_case_ids in self.pkeys:
            case_ids.update(person_case_ids)
        self.select(case_ids)

    def get_selected(self):
        # Yield selected cases in search order
        self._page_to_selected()
        selected = []
        for person_id, person_case_ids in self.pkeys:
            for case_id in person_case_ids:
                if case_id in self.selected:
                    selected.append(case_id)
        return selected

    def page_rows(self):
        if not self.pkeys:
            return []
        # Collect ordering and linking information
        self._page_to_selected()
        person_ids = []
        self.page_case_ids = set()
        for person_id, person_case_ids in self.page_pkeys():
            person_ids.append(person_id)
            self.page_case_ids.update(person_case_ids)
        self._selected_to_page()
        # Fetch persons
        person_map = {}
        query = globals.db.query('persons')
        query.where_in('person_id', person_ids)
        for row in query.fetchall():
            person_map[row.person_id] = Person(self, row)
        # Fetch cases
        case_map = {}
        query = globals.db.query('cases')
        query.where_in('case_id', self.page_case_ids)
        for row in query.fetchall():
            case_map[row.case_id] = CaseSummary(self, row)
        # Fetch case tags 
        cases_tags = casetags.CasesTags(self.page_case_ids)
        # Now collate
        result = []
        for person_id, person_case_ids in self.page_pkeys():
            try:
                person = person_map[person_id]
            except KeyError:
                pass
            else:
                result.append(person)
                for case_id in person_case_ids:
                    try:
                        case_summary = case_map[case_id]
                    except KeyError:
                        pass
                    else:
                        person.cases.append(case_summary)
                        case_summary.case_row.tags = \
                            cases_tags.get(case_summary.case_id)
        return result
