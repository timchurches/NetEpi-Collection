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

from casemgr import globals, paged_search, person, demogfields, \
                    casetags, syndrome

class CaseSummary:
    def __init__(self, row):
        self.row = row

    def summary(self):
        return fields.summary(self.row)


class CaseDupeScan(paged_search.PagedSearch):
    order_by = 'surname', 'given_names', 'person_id', 'notification_datetime'
    case_fields = (
        'case_id', 'local_case_id', 'case_status', 
        'onset_datetime', 'notification_datetime',
    )

    def __init__(self, prefs, syndrome_id, notification_window):
        paged_search.PagedSearch.__init__(self, globals.db, prefs, None)
        self.syndrome_id = syndrome_id
        self.syndrome_name = syndrome.syndromes[syndrome_id].name
        self.notification_window = notification_window
        cases_by_person = {}
        cols = 'person_id', 'case_id'
        query = globals.db.query('cases', order_by=self.order_by)
        query.where('NOT deleted')
        query.join('JOIN persons USING (person_id)')
        query.where('syndrome_id = %s', self.syndrome_id)
        for person_id, case_id in query.fetchcols(cols):
            person_case_ids = cases_by_person.setdefault(person_id, [])
            person_case_ids.append(case_id)
        cases_by_person = [(person_id, cases)
                           for person_id, cases in cases_by_person.iteritems()
                           if len(cases) >= 2]
        if not cases_by_person:
            raise globals.Error('No duplicates found')
        self.cases_by_person = dict(cases_by_person)
        # Put person ids in order
        person_ids = self.cases_by_person.keys()
        query = globals.db.query('persons', order_by='surname, given_names')
        query.where_in('person_id', person_ids)
        self.pkeys = query.fetchcols('person_id')
        # fields
        fields = demogfields.get_demog_fields(globals.db, self.syndrome_id)
        fields = fields.context_fields('result')
        self.fields = []
        for name in self.case_fields:
            try:
                self.fields.append(fields.field_by_name(name))
            except KeyError:
                pass

    def page_rows(self):
        person_ids = self.page_pkeys()
        page_case_ids = set()
        for person_id in person_ids:
            page_case_ids.update(self.cases_by_person[person_id])
        # Fetch persons
        query = globals.db.query('persons')
        query.where_in('person_id', person_ids)
        person_by_id = {}
        for row in query.fetchall():
            person_by_id[row.person_id] = person.person(row)
        # Fetch cases
        query = globals.db.query('cases')
        query.where_in('case_id', page_case_ids)
        query.where('NOT deleted')
        case_by_id = {}
        for row in query.fetchall():
            case_by_id[row.case_id] = CaseSummary(row)
        # Fetch case tags 
        cases_tags = casetags.CasesTags(page_case_ids)
        # Now join them up
        persons = []
        for person_id in person_ids:
            case_ids = self.cases_by_person[person_id]
            try:
                pers = person_by_id[person_id]
            except KeyError:
                continue
            pers.cases = []
            for case_id in case_ids:
                try:
                    pers.cases.append(case_by_id[case_id])
                except KeyError:
                    continue
            if len(pers.cases) < 2:
                continue
            for cs in pers.cases:
                cs.row.tags = cases_tags.get(cs.row.case_id)
            persons.append(pers)
        return persons


