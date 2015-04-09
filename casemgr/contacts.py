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

from cocklebur import datetime, utils, dbobj
from casemgr import globals, paged_search, person, search, casestatus, syndrome

def contact_type_count_query():
    return query

class ContactTypeEdit:

    def __init__(self, contact_type_id):
        self.contact_type_id = contact_type_id
        row = self._fetch()
        self.name = row.contact_type
        self.new_name = self.name

    def _fetch(self, contact_type_id=None, for_update=False):
        if contact_type_id is None:
            contact_type_id = self.contact_type_id
        query = globals.db.query('contact_types', for_update=for_update)
        query.where('contact_type_id = %s', contact_type_id)
        return query.fetchone()

    def refresh(self):
        query = globals.db.query('case_contacts')
        query.where('contact_type_id = %s', self.contact_type_id)
        query.where('case_id < contact_id')
        self.count = query.aggregate('count(*)')
        query = globals.db.query('contact_types', 
                                 order_by='lower(contact_type)')
        self.contact_types = query.fetchcols(('contact_type_id', 'contact_type'))
        self.contact_type_map = dict(self.contact_types)

    def type_label(self, id):
        return self.contact_type_map.get(int(id), '???')

    def merge_types(self):
        types =  [(id, name) for id, name in self.contact_types
                  if id != self.contact_type_id]
        types.insert(0, ('', '(select a contact type)'))
        return types

    def rename(self):
        if self.new_name and self.new_name.strip():
            row = self._fetch(for_update=True)
            row.contact_type = self.new_name.strip()
            row.db_update()

    def merge(self):
        this_row = self._fetch(for_update=True)
        other_row = self._fetch(self.merge_to_id, for_update=True)
        if (this_row is None or other_row is None or 
            this_row.contact_type_id == other_row.contact_type_id):
            raise globals.Error('Unable to merge')
        curs = globals.db.cursor()
        try:
            dbobj.execute(curs,
                          'UPDATE case_contacts SET contact_type_id=%s'
                          ' WHERE contact_type_id=%s', 
                          (other_row.contact_type_id, this_row.contact_type_id))
            self.count = curs.rowcount / 2
        finally:
            curs.close()
        this_row.db_delete()

    def delete(self):
        this_row = self._fetch(for_update=True)
        curs = globals.db.cursor()
        try:
            dbobj.execute(curs, 
                        'DELETE FROM case_contacts WHERE contact_type_id=%s', 
                         (this_row.contact_type_id,))
            self.count = curs.rowcount / 2
        finally:
            curs.close()
        this_row.db_delete()


class ContactTypeAdmin:

    cols = 'contact_type_id', 'contact_type', 'count'

    def __init__(self, row):
        for col, value in zip(self.cols, row):
            setattr(self, col, value)

        
class ContactTypesAdmin(list):

    def __init__(self):
        cols = ('contact_types.contact_type_id', 'contact_type',
                '(select count(*) from case_contacts'
                ' where case_contacts.contact_type_id'
                '  = contact_types.contact_type_id'
                ' and case_id > contact_id)')
        query = globals.db.query('contact_types',order_by='lower(contact_type)')
        for row in query.fetchcols(cols):
            self.append(ContactTypeAdmin(row))


def new_contact_type(contact_type):
    if contact_type:
        row = globals.db.new_row('contact_types')
        row.contact_type = contact_type
        row.db_update()
        return row.contact_type_id


def dissociate_contact(id_a, id_b):
    query = globals.db.query('case_contacts')
    query.where('(case_id = %s AND contact_id = %s)', id_a, id_b)
    query.delete()
    query = globals.db.query('case_contacts')
    query.where('(contact_id = %s AND case_id = %s)', id_a, id_b)
    query.delete()


def dissociate_contacts(case_id, contacts):
    query = globals.db.query('case_contacts')
    query.where('case_id = %s', case_id)
    query.where_in('contact_id', contacts)
    query.delete()
    query = globals.db.query('case_contacts')
    query.where('contact_id = %s', case_id)
    query.where_in('case_id', contacts)
    query.delete()


def associate_contact(id_a, id_b, contact_type_id, contact_date):
    def _update(case_id, contact_id, contact_type_id, contact_date):
        query = globals.db.query('case_contacts', for_update=True)
        query.where('(case_id = %s AND contact_id = %s)', case_id, contact_id)
        row = query.fetchone()
        if row is None:
            row = globals.db.new_row('case_contacts')
        row.case_id = case_id
        row.contact_id = contact_id
        row.contact_type_id = contact_type_id
        row.contact_date = contact_date
        row.db_update(refetch=False)

    if id_a == id_b:
        return
    _update(id_a, id_b, contact_type_id, contact_date)
    _update(id_b, id_a, contact_type_id, contact_date)


class CaseContact:
    cols = (
        'person_id', 'cases.case_id', 'syndrome_id', 'case_status', 
        'onset_datetime', 'deleted', 'contact_date', 'contact_type',
    )

    def __init__(self, case_row, person_loader):
        for col, value in zip(self.cols, case_row):
            col = col.split('.')[-1]
            setattr(self, col, value)
        self.person = person_loader.get(self.person_id)
        self.contact_date = datetime.mx_parse_datetime(self.contact_date)
        if self.contact_type is None:
            self.contact_type = 'Unknown'
        self.case_status = casestatus.get_label(self.syndrome_id, 
                                                self.case_status)
        self.syndrome_name = syndrome.syndromes[self.syndrome_id].name



class ContactRowsMixin:

    def contact_rows(self, case_ids):
        query = globals.db.query('cases')
        query.join('LEFT JOIN case_contacts ON (contact_id = %s'
                    ' AND cases.case_id=case_contacts.case_id)', self.case_id)
        query.join('LEFT JOIN contact_types USING (contact_type_id)')
        query.where_in('cases.case_id', case_ids)
        case_rows = {}
        person_loader = person.DelayLoadPersons()
        for row in query.fetchcols(CaseContact.cols):
            case_row = CaseContact(row, person_loader)
            case_rows[case_row.case_id] = case_row
        not_found = person_loader.load(globals.db)
        page_rows = []
        for case_id in case_ids:
            try:
                page_rows.append(case_rows[case_id])
            except KeyError:
                pass
        return page_rows


class MostCommon(dict):

    def add(self, value):
        self[value] = self.get(value, 0) + 1  

    def most_common(self):
        if self:
            items = [(count, value) for value, count in self.iteritems()]
            items.sort()
            return items[-1][1]


class AssocContacts(paged_search.PagedSearch, ContactRowsMixin): 

    def __init__(self, prefs, case_id, assoc_ids):
        paged_search.PagedSearch.__init__(self, globals.db, prefs, None)
        self.case_id = case_id
        self.pkeys = assoc_ids
        self.contact_type = None
        self.datetime_fmt = datetime.mx_parse_datetime.format
        self.guess_type_and_date()

    def guess_type_and_date(self):
        ct = MostCommon()
        cd = MostCommon()
        query = globals.db.query('case_contacts')
        query.where('contact_id = %s', self.case_id)
        query.where_in('case_id', self.pkeys)
        cols = 'contact_type_id', 'contact_date'
        for contact_type_id, contact_date in query.fetchcols(cols):
            ct.add(contact_type_id)
            cd.add(contact_date)
        self.contact_type_id = ct.most_common()
        self.contact_date = cd.most_common()
        if self.contact_date is not None:
            self.contact_date = self.contact_date.strftime(self.datetime_fmt)

    def contact_types(self):
        query = globals.db.query('contact_types', 
                                 order_by='lower(contact_type)')
        return query.fetchcols(('contact_type_id', 'contact_type'))

    def new_contact_type(self, contact_type):
        self.contact_type_id = new_contact_type(contact_type)

    def page_rows(self):
        return self.contact_rows(self.page_pkeys())

    def associate(self):
        for contact_id in self.pkeys:
            associate_contact(self.case_id, contact_id, 
                              self.contact_type_id, self.contact_date)

    def log_msg(self):
        return 'Associated contact ID(s) %s' % utils.commalist(self.pkeys, 'and')
        


class ContactSearch(paged_search.SortablePagedSearch, 
                    paged_search.PagerSelect,
                    search.SearchOrderMixin,
                    ContactRowsMixin):

    syndrome_id = None

# Wont work - contact_type is not a demogfield
#    orders = SearchOrderMixin.orders + [
#        'contact_type,surname,given_names',
#    ]

    def __init__(self, prefs, case_id, deleted):
        self.deleted = deleted
        self.case_id = case_id
        self.order_by = self.default_order
        paged_search.PagerSelect.__init__(self)
        paged_search.SortablePagedSearch.__init__(self, globals.db, prefs)

    def new_search(self):
        paged_search.SortablePagedSearch.new_search(self)
        self.query = globals.db.query('cases', order_by=self.order_by)
        self.query.join('JOIN case_contacts USING (case_id)')
        self.query.join('JOIN persons USING (person_id)')
        self.query.join('LEFT JOIN contact_types USING (contact_type_id)')
        self.query.where('contact_id = %s', self.case_id)
        if not self.deleted:
            self.query.where('NOT deleted')

    def fetch_pkeys(self, query):
        paged_search.SortablePagedSearch.fetch_pkeys(self, query)
        self.case_ids = set([keys[0] for keys in self.pkeys])

    def __len__(self):
        if self.pkeys is None:
            self.fetch_pkeys(self.query)
        return len(self.pkeys)

    def page_rows(self):
        if self.pkeys is None:
            self.fetch_pkeys(self.query)
        self.order = self.order_by_cols()
        case_ids = [keys[0] for keys in self.page_pkeys()]
        return self.contact_rows(case_ids)

    def is_contact(self, case_id):
        return case_id in self.case_ids

    def selected_case_ids(self):
        return [k[0] for k in self.selected]

#    def get_demog_fields(self):
#        # Multiple contact syndromes could be involved - just return the common
#        return demogfields.get_demog_fields(globals.db, None)

