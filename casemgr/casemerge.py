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

import copy
from cocklebur import dbobj, datetime
from casemgr import globals, caseaccess, demogfields, syndrome, person, casetags
import config

class MergeError(globals.Error): pass
class CaseHasChanged(MergeError): pass

class NS: pass


class CaseField:

    def __init__(self, merge, field):
        self.merge = merge
        self.name = field.name
        self.label = field.label
        self.field = field.name

    def outtrans(self, ns):
        return self.merge.demogfield(self.name).outtrans(ns) or ''

    def format(self):
        return self.merge.demogfield(self.name).format()


class MergeField:

    def __init__(self, merge, field):
        self.merge = merge
        self.name = field.name
        self.field = 'casemerge.case.%s' % field.name
        self.render = getattr(field, 'render_case', None) or field.render
        self.disabled = False

    def optionexpr(self):
        return self.merge.demogfield(self.name).optionexpr()

    def format(self):
        return self.merge.demogfield(self.name).format()


class MergeCol:

    field_cls = MergeField

    def __init__(self, merge, field, index):
        self.merge = merge
        self.name = field.name
        self.label = field.label
        value_a = getattr(merge.case_a, self.name)
        value_b = getattr(merge.case_b, self.name)
        self.conflict = (value_a and value_b and value_a != value_b)
        self.field = None
        if self.field_cls is not None:
            self.field = self.field_cls(merge, field)
        if not value_a and not value_b:
            self.source = 'd'
        elif value_b and not value_a:
            self.source = 'b'
        else:
            self.source = 'a'
        self.source_field = 'casemerge.fields[%d].source' % index
        self.show_radio = (self.name != 'tags')

    def outtrans(self, ns):
        return self.merge.demogfield(self.name).outtrans(ns) or ''

    def desc_edit(self):
        value_a = getattr(self.merge.case_a, self.name)
        value_b = getattr(self.merge.case_b, self.name)
        value_e = getattr(self.merge.case, self.name, None)
        if value_e:
            op = 'Edit'
            hilite = value_e != value_a or value_e != value_b
            ns = self.merge.case
        elif self.source == 'a' and value_a != value_b:
            op = 'A'
            hilite = True
            ns = self.merge.case_a
        elif self.source == 'b' and value_a != value_b:
            op = 'B'
            hilite = True
            ns = self.merge.case_b
        elif self.source == 'd' and (value_a or value_b):
            op = 'DELETE'
            hilite = True
            if value_a:
                ns = self.merge.case_a
            else:
                ns = self.merge.case_b
        else:
            return None
        return self.label, op, self.outtrans(ns), hilite

    def apply(self, case_a, case_b):
        value_a = getattr(case_a, self.name)
        value_b = getattr(case_b, self.name)
        initial_a = getattr(self.merge.case_a, self.name)
        initial_b = getattr(self.merge.case_b, self.name)
        if initial_a != value_a or initial_b != value_b:
            raise CaseHasChanged
        value_e = getattr(self.merge.case, self.name)
        if value_e:
            assert self.field is not None
            value = value_e
        elif self.source == 'a':
            value = value_a
        elif self.source == 'b':
            value = value_b
        elif self.source == 'd':
            assert self.field is not None
            value = None
        setattr(case_a, self.name, value)
        setattr(case_b, self.name, value)
        return value_a != value, value_b != value


class CaseMerge:

    def __init__(self, id_a, id_b):
        self.id_a = id_a
        self.id_b = id_b
        self.fields = None
        self.case = NS()
        self.init_fields(*self._fetch_cases())
        self.keep = 'a'

    def _fetch_cases(self, for_update=False):
        query = globals.db.query('cases', for_update=for_update)
        query.where_in('case_id', (self.id_a, self.id_b))
        try:
            a, b = query.fetchall()
        except ValueError:
            raise MergeError('Error fetching records (incorrect count)')
        cases_tags = casetags.CasesTags((a.case_id, b.case_id))
        a.tags = cases_tags.get(a.case_id)
        b.tags = cases_tags.get(b.case_id)
        if a.case_id == self.id_a and b.case_id == self.id_b:
            return a, b
        elif a.case_id == self.id_b and b.case_id == self.id_a:
            return b, a
        else:
            raise MergeError('Error fetching records (incorrect records)')

    def syndrome(self):
        return syndrome.syndromes[self.syndrome_id]

    def demogfields(self):
        return demogfields.get_demog_fields(globals.db, self.syndrome_id)

    # AM 20091007 - not used? 
    #def casefields(self):
    #    return [CaseField(self, field) 
    #            for field in self.demogfields().context_fields('case')
    #            if field.field.startswith('case.case_row')]

    def demogfield(self, name):
        return self.demogfields().field_by_name(name)

    def add_field(self, merge_cls, field):
        self.fields.append(merge_cls(self, field, len(self.fields)))

    def init_fields(self, case_a, case_b):
        if case_a.syndrome_id != case_b.syndrome_id:
            raise MergeError('Error fetching records (syndrome mismatch)')
        self.syndrome_id = case_a.syndrome_id
        if case_a.deleted and not case_b.deleted:
            self.keep = 'b'
        self.css_a = self.css_b = ''
        if case_a.deleted:
            self.css_a = 'gray'
        if case_b.deleted:
            self.css_b = 'gray'
        self.case_a = NS()
        self.case_b = NS()
        self.fields = []
        ignore_fields = ('case_id', 'deleted',
                         'delete_reason', 'delete_timestamp')
        for field in self.demogfields():
            try:
                value_a = getattr(case_a, field.name)
                value_b = getattr(case_b, field.name)
            except AttributeError:
                continue
            setattr(self.case_a, field.name, value_a)
            setattr(self.case_b, field.name, value_b)
            if field.name not in ignore_fields:
                self.add_field(MergeCol, field)
        if not getattr(self.case, 'tags', None):
            self.case.tags = casetags.Tags()
            if self.case_a.tags:
                self.case.tags.update(self.case_a.tags)
            if self.case_b.tags:
                self.case.tags.update(self.case_b.tags)

    def desc_edit(self):
        edits = []
        for mc in self.fields:
            desc = mc.desc_edit()
            if desc:
                edits.append(desc)
        return edits

    def merge(self, credentials):
        # lock the relevent cases
        case_a, case_b = self._fetch_cases(for_update=True)
        # Safety checks:
        not_same_person = (case_a.person_id != case_b.person_id)
        syndrome_mismatch = (case_a.syndrome_id != case_b.syndrome_id)
        if not_same_person or syndrome_mismatch:
            raise MergeError('Unable to merge - consistency check failed')
        for mc in self.fields:
            try:
                mc.apply(case_a, case_b)
            except CaseHasChanged:
                case_a.db_revert()
                case_b.db_revert()
                self.init_fields(case_a, case_b)
                raise
        # Which direction to merge?
        if self.keep == 'a':
            update_case, delete_case = case_a, case_b
        else:
            update_case, delete_case = case_b, case_a
        update_desc = update_case.db_desc()
        delete_desc = delete_case.db_desc()
        # XXX Describe tag changes - how?
        if not update_desc:
            update_desc = 'no edits required'
        if not delete_desc:
            delete_desc = 'no edits required'
        if update_case.deleted and not delete_case.deleted:
            update_case.deleted = False
            update_case.delete_reason = None
            update_case.delete_timestamp = None
        delete_case.deleted = True
        delete_case.delete_reason = 'Merged to %s' % update_case.case_id
        delete_case.delete_timestamp = datetime.now()
        curs = globals.db.cursor()
        try:
            # merge contacts
            dbobj.execute(curs, 'UPDATE case_contacts SET contact_id=%s'
                                ' WHERE contact_id=%s'
                                '  AND case_id != %s'
                                '  AND case_id NOT IN'
                                '   (SELECT case_id FROM case_contacts'
                                '     WHERE contact_id=%s)',
                            (update_case.case_id, delete_case.case_id,
                             update_case.case_id, update_case.case_id))
            dbobj.execute(curs, 'UPDATE case_contacts SET case_id=%s'
                                ' WHERE case_id=%s'
                                '  AND contact_id != %s'
                                '  AND contact_id NOT IN'
                                '   (SELECT contact_id FROM case_contacts'
                                '     WHERE case_id=%s)',
                            (update_case.case_id, delete_case.case_id,
                             update_case.case_id, update_case.case_id))
            dbobj.execute(curs, 'DELETE FROM case_contacts'
                                ' WHERE case_id=%s OR contact_id=%s',
                            (delete_case.case_id, delete_case.case_id))

            # case_form_summary
            dbobj.execute(curs, 'UPDATE case_form_summary SET case_id=%s'
                                ' WHERE case_id=%s',
                          (update_case.case_id, delete_case.case_id))
            # case_acl
            dbobj.execute(curs, 'UPDATE case_acl SET case_id=%s'
                                ' WHERE case_id=%s',
                          (update_case.case_id, delete_case.case_id))
            # tasks
            dbobj.execute(curs, 'UPDATE tasks SET case_id=%s'
                                ' WHERE case_id=%s',
                          (update_case.case_id, delete_case.case_id))
            dbobj.execute(curs, 'UPDATE tasks SET case_id=%s'
                                ' WHERE case_id=%s',
                          (update_case.case_id, delete_case.case_id))
            dbobj.execute(curs, 'UPDATE user_log SET case_id=%s'
                                ' WHERE case_id=%s',
                          (update_case.case_id, delete_case.case_id))
            dbobj.execute(curs, 'UPDATE user_log SET case_id=%s'
                                ' WHERE case_id=%s',
                          (update_case.case_id, delete_case.case_id))
        finally:
            curs.close()
        update_case.db_update()
        tag_desc = casetags.set_case_tags(update_case.case_id, update_case.tags)
        delete_case.db_update()
        desc = 'Merge System ID %s into %s, UPDATED %s %s, DELETED %s' %\
                    (delete_case.case_id, update_case.case_id, 
                     update_desc, tag_desc, delete_desc)
        credentials.user_log(globals.db, desc, case_id=update_case.case_id)
        return update_case, delete_case


class SyndromeCaseMergeSet(list):

    def __init__(self, syndrome_id):
        self.syndrome_id = syndrome_id
        self.name = syndrome.syndromes[syndrome_id].name

    def __cmp__(self, other):
        return cmp(self.name, other.name)


class SelCaseMerge:

    def __init__(self, credentials, syndrome_id, query, person):
        self.syndrome_id = syndrome_id
        self.query = query
        self.person = person
#        self.update()

    def update(self):
        cases = self.query.fetchall()
        case_ids = [case.case_id for case in cases]
        cases_tags = casetags.CasesTags(case_ids)
        syndsets = {}
        for case in cases:
            case.tags = cases_tags.get(case.case_id)
            syndset = syndsets.get(case.syndrome_id)
            if syndset is None:
                syndset = SyndromeCaseMergeSet(case.syndrome_id)
                syndsets[case.syndrome_id] = syndset
            syndset.append(case)
        self.syndsets = [syndset for syndset in syndsets.values()
                         if len(syndset) > 1]
        self.syndsets.sort()
        self.index_a = '0,0'
        self.index_b = '0,1'

    def __nonzero__(self):
        return bool(self.syndsets)

    def personfields_rows_and_cols(self):
        personfields = []
        for field in self.demogfields().context_fields('form'):
            if field.field.startswith('case.person'):
                field = copy.copy(field)
                field.field = field.field.replace('case.person', 
                                                  'selcasemerge.person')
                personfields.append(field)
        return demogfields.rows_and_cols(personfields)

    def demogfields(self):
        return demogfields.get_demog_fields(globals.db, self.syndrome_id)

    def casefields(self):
        return [CaseField(self, field) 
                for field in self.demogfields().context_fields('case')
                if (field.field.startswith('case.case_row') 
                    or field.name == 'tags')]

    def demogfield(self, name):
        return self.demogfields().field_by_name(name)

    def get_casemerge(self):
        try:
            if not self.index_a or not self.index_b:
                raise ValueError
            set_a_idx, case_a_idx = self.index_a.split(',')
            set_b_idx, case_b_idx = self.index_b.split(',')
            if set_a_idx != set_b_idx:
                raise MergeError('Select A and B records from the same %s' %
                                 config.syndrome_label)
            syndset = self.syndsets[int(set_a_idx)]
            case_a = syndset[int(case_a_idx)]
            case_b = syndset[int(case_b_idx)]
            if case_a is case_b: raise ValueError
        except (IndexError, ValueError, TypeError):
            raise MergeError('Select the two records you wish to merge')
        return CaseMerge(case_a.case_id, case_b.case_id)


def by_person(credentials, person_row):
    query = globals.db.query('cases', order_by='case_id')
    caseaccess.acl_query(query, credentials, deleted=None)
    query.where('person_id = %s', person_row.person_id)
    return SelCaseMerge(credentials, None, query, person.edit_row(person_row))


def by_person_id(credentials, syndrome_id, person_id):
    query = globals.db.query('cases', order_by='case_id')
    caseaccess.acl_query(query, credentials, deleted=None)
    query.where('syndrome_id = %s', syndrome_id)
    query.where('person_id = %s', person_id)
    return SelCaseMerge(credentials, None, query, person.edit_id(person_id))


def by_case(credentials, case, person):
    query = globals.db.query('cases', order_by='case_id')
    caseaccess.acl_query(query, credentials, deleted=None)
    query.where('person_id = %s', case.person_id)
    query.where('syndrome_id = %s', case.syndrome_id)
    return SelCaseMerge(credentials, case.syndrome_id, query, person)

