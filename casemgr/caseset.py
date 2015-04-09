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
import cPickle as pickle

from cocklebur import dbobj
from casemgr import globals, cases, caseaccess, cached

import config

class CaseSetBase(object):

    dynamic = False
    caseset_id = None                   # Not saved
    case_ids = ()
    name = ''
    index = 0

    def load(self, credentials):
        pass

    def __len__(self):
        return len(self.case_ids)

    def edit_cur(self, credentials):
        if self.index >= len(self):
            self.index = len(self) - 1
        return cases.edit_case(credentials, self.case_ids[self.index])

    def inrange(self, offset):
        return 0 <= (self.index + offset) < len(self.case_ids)

    def remove(self, case_id):
        try:
            self.case_ids.remove(case_id)
        except ValueError:
            pass
        if self.index >= len(self):
            self.index = len(self) - 1

    def seek(self, offset):
        if self.inrange(offset):
            self.index += offset
        else:
            raise IndexError

    def cur(self):
        try:
            return self.case_ids[self.index]
        except IndexError:
            return None

    def seek_case(self, case_id):
        self.index = self.case_ids.index(case_id)

    def append(self, case_id):
        if not self.dynamic and case_id not in self.case_ids:
            self.case_ids.append(case_id)
            self.index = len(self.case_ids) - 1

    def info(self):
        return 'Record %d of %d' % (self.index + 1, len(self.case_ids))

    def sort_by(self, *cols):
        cur_case_id = self.cur()
        query = globals.db.query('cases', order_by=cols)
        query.join('JOIN persons USING (person_id)')
        query.where_in('case_id', self.case_ids)
        self.case_ids = query.fetchcols('case_id')
        self.seek_case(cur_case_id)


class CaseSet(CaseSetBase):

    def __init__(self, case_ids=[], name=None):
        self.case_ids = case_ids
        if not name:
            name = 'Unnamed'
        self.name = name
        self.index = 0


class PersonCaseSet(CaseSetBase):

    dynamic = True

    def __init__(self, credentials, person_id, syndrome_id=None):
        CaseSetBase.__init__(self)
        self.person_id = person_id
        self.syndrome_id = syndrome_id
        self.load(credentials)

    def getstate(self):
        return self.syndrome_id, self.person_id

    def setstate(self, state):
        self.syndrome_id, self.person_id = state

    def load(self, credentials):
        query = globals.db.query('persons')
        query.where('person_id = %s', self.person_id)
        person = query.fetchone()
        if person is None:
            return
        self.name = 'All cases for %s, %s' %\
            (person.surname, person.given_names)
        query = globals.db.query('cases', order_by='case_id')
        caseaccess.acl_query(query, credentials, deleted=None)
        query.where('person_id = %s', self.person_id)
        if self.syndrome_id is not None:
            query.where('syndrome_id = %s', self.syndrome_id)
        self.case_ids = query.fetchcols('case_id')


class ContactCaseSet(CaseSetBase):

    dynamic = True

    def __init__(self, credentials, case_id):
        CaseSetBase.__init__(self)
        self.case_id = case_id
        self.load(credentials)

    def getstate(self):
        return self.case_id

    def setstate(self, state):
        self.case_id = state

    def load(self, credentials):
        query = globals.db.query('persons')
        query.join('JOIN cases USING (person_id)')
        query.where('case_id = %s', self.case_id)
        person = query.fetchone()
        if person is None:
            return
        self.name = '%ss of %s, %s (ID %s)' %\
            (config.contact_label, person.surname, 
             person.given_names, self.case_id)
        query = globals.db.query('cases', order_by='case_id')
        caseaccess.contact_query(query, self.case_id)
        self.case_ids = query.fetchcols('case_id')


class _CSInfo(object):

    def __init__(self, caseset_id, name, dynamic):
        self.caseset_id = caseset_id
        self.name = name
        self.dynamic = dynamic


class SavedCasesetList(list, cached.Cached):

    def __init__(self, cred):
        self.cred = cred

    def load(self):
        query = globals.db.query('casesets', order_by='LOWER(name)')
        subq = query.sub_expr('OR')
        subq.where('user_id = %s', self.cred.user.user_id)
        subq.where('unit_id = %s', self.cred.unit.unit_id)
        subq.where('(unit_id IS NULL AND user_id IS NULL)')
        cols = 'caseset_id', 'name', 'dynamic'
        self[:] = [_CSInfo(*row) for row in query.fetchcols(cols)]


class CaseSets(object):
    """
    Dummy at this stage - ultimately it should be backed by casesets tables

    The intention is to implement two collections of case sets:

     * A FIFO of "Recent" (transient) case sets

     * A library of named case sets. These can be private, shared with your
       role, or public.
    """
    NRECENT = 8
    sort_options = [
        ('onset_datetime:surname', 'Onset date'),
        ('notification_datetime:surname', 'Notification date'),
        ('surname:given_names:case_id', 'Surname'),
        ('given_names:surname:case_id', 'Given names'),
        ('case_id', 'ID'),
        ('dob desc:surname', 'Age'),
    ]

    def __init__(self, cred):
        self.cred = cred
        self.saved_casesets = SavedCasesetList(self.cred)
        self.recent_casesets = []
        self.new_name = None

    def save(self, cs):
        row = None
        if cs.caseset_id:
            query = globals.db.query('casesets')
            query.where('caseset_id = %s', cs.caseset_id)
            row = query.fetchone()
        if row is None:
            row = globals.db.new_row('casesets')
            row.user_id = self.cred.user.user_id
        row.name = cs.name
        row.dynamic = cs.dynamic
        row.pickle = pickle.dumps(cs, -1)
        row.db_update()
        try:
            self.recent_casesets.remove(cs)
        except ValueError:
            pass
        cs.caseset_id = row.caseset_id
        self.saved_casesets.cache_invalidate()

    def load(self, id):
        query = globals.db.query('casesets')
        query.where('caseset_id = %s', id)
        row = query.fetchone()
        if row is not None:
            cs = pickle.loads(str(row.pickle))
            cs.caseset_id = id
            return cs

    def rename(self, cs, new_name):
        if new_name:
            cs.name = new_name
            if cs.caseset_id is not None:
                self.save(cs)

    def delete(self, cs):
        if cs.caseset_id is not None:
            query = globals.db.query('casesets')
            query.where('caseset_id = %s', cs.caseset_id)
            query.delete()
            cs.caseset_id = None
            if cs:
                self.add_recent(cs)
            self.saved_casesets.cache_invalidate()

    def add_recent(self, cs):
        self.recent_casesets.insert(0, cs)
        del self.recent_casesets[self.NRECENT:]

    def use(self, credentials, cs):
        cs.load(credentials)
        if cs.caseset_id is None:
            try:
                self.recent_casesets.remove(cs)
            except ValueError:
                pass
            self.add_recent(cs)
        return cs

    def actionoptions(self, cur_cs):
        """
        Return an optionexpr list of case set actions
        """
        self.saved_casesets.refresh()
        options = [
            ('', cur_cs.name),
        ]
        if cur_cs is not None:
            options.append(('report', 'Open as report'))
            if not cur_cs.dynamic:
                options.append(('rename', 'Rename this case set'))
            if cur_cs.caseset_id is None:
                options.append(('save', 'Save this case set'))
            else:
                options.append(('delete', 'Delete case set'))
            for sortcol, label in self.sort_options:
                options.append(('sort:' + sortcol, 'Sort by ' + label))
        for csi in self.saved_casesets:
            if cur_cs is None or cur_cs.caseset_id != csi.caseset_id:
                options.append(('load:%s' % csi.caseset_id, 
                                'Load: ' + csi.name))
        return options

    def caseoptions(self, cur_cs):
        self.saved_casesets.refresh()
        options = [('caseset_add:', 'New case set')]
        for csi in self.saved_casesets:
            if not csi.dynamic and (cur_cs is None 
                                 or cur_cs.caseset_id != csi.caseset_id):
                name = csi.name
                if len(name) > 30:
                    name = '%s ...' % name[:40]
                options.append(('caseset_add:%s' % csi.caseset_id, 
                                'Add to: ' + name))
        return options
