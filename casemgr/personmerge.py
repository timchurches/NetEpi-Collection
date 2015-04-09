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
from cocklebur import dbobj, utils
from casemgr import globals, demogfields, person, fuzzyperson, persondupe, \
                    syndrome

class PersonMergeError(globals.Error): pass
class PersonHasChanged(PersonMergeError): pass
Error = PersonMergeError

class MergeValue:
    # A cut down version of a DemogField - to substitute our own field name
    def __init__(self, merge, field):
        self.merge = merge
        self.name = field.name
        self.render = getattr(field, 'render_case', None) or field.render
        self.field = 'personmerge.person.' + field.name
        self.disabled = False

    def optionexpr(self):
        return self.merge.demogfield(self.name).optionexpr()

    def format(self):
        return self.merge.demogfield(self.name).format()

    def age_if_dob(self, ns):
        return self.merge.demogfield(self.name).age_if_dob(ns)


class MergeCol:
    def __init__(self, merge, field, index):
        self.merge = merge
        self.name = field.name
        self.label = field.label
        self.field = MergeValue(merge, field)
        value_a = getattr(merge.person_a, self.name)
        value_b = getattr(merge.person_b, self.name)
        self.show_a = bool(value_a)
        self.show_b = bool(value_b)
        self.conflict = (value_a and value_b and value_a != value_b)
        if self.name == 'data_src':
            self.source = 'd'
        elif not value_a and not value_b:
            self.source = 'd'
        elif value_b and not value_a:
            self.source = 'b'
        else:
            self.source = 'a'
        self.source_field = 'personmerge.fields[%d].source' % index

    def outtrans(self, ns):
        return self.merge.demogfield(self.name).outtrans(ns) or ''

    def desc_edit(self):
        value_a = getattr(self.merge.person_a, self.name)
        value_b = getattr(self.merge.person_b, self.name)
        value_e = getattr(self.merge.person, self.name, None)
        if value_e:
            op = 'Edit'
            hilite = value_e != value_a or value_e != value_b
            ns = self.merge.person
        elif self.source == 'a' and value_a != value_b:
            op = 'A'
            hilite = True
            ns = self.merge.person_a
        elif self.source == 'b' and value_a != value_b:
            op = 'B'
            hilite = True
            ns = self.merge.person_b
        elif self.source == 'd' and (value_a or value_b):
            op = 'DELETE'
            hilite = True
            if value_a:
                ns = self.merge.person_a
            else:
                ns = self.merge.person_b
        else:
            return None
        return self.label, op, self.outtrans(ns), hilite

    def apply(self, person_a, person_b):
        value_a = getattr(person_a, self.name)
        value_b = getattr(person_b, self.name)
        initial_a = getattr(self.merge.person_a, self.name)
        initial_b = getattr(self.merge.person_b, self.name)
        if initial_a != value_a or initial_b != value_b:
            raise PersonHasChanged
        value_e = getattr(self.merge.person, self.name)
        if value_e:
            value = value_e
        elif self.source == 'a':
            value = value_a
        elif self.source == 'b':
            value = value_b
        elif self.source == 'd':
            value = None
        setattr(person_a, self.name, value)
        setattr(person_b, self.name, value)
        return value_a != value, value_b != value


class DOBMergeCol(MergeCol):

    def __init__(self, merge, field, index):
        MergeCol.__init__(self, merge, field, index)
        a_exact = merge.person_a.DOB and not merge.person_a.DOB_prec
        b_exact = merge.person_b.DOB and not merge.person_b.DOB_prec
        if a_exact and not b_exact:
            self.source = 'a'
        elif b_exact and not a_exact:
            self.source = 'b'

    def apply(self, person_a, person_b):
        def ne(a, b):
            return a.DOB != b.DOB or a.DOB_prec != b.DOB_prec
        def set(dst, src):
            dst.DOB, dst.DOB_prec = src.DOB, src.DOB_prec
        class NullDOB:
            DOB = None
            DOB_prec = None
        if (ne(self.merge.person_a, person_a) 
            or ne(self.merge.person_b, person_b)):
            raise PersonHasChanged
        if self.merge.person.DOB:
            src = self.merge.person
        elif self.source == 'a':
            src = person_a
        elif self.source == 'b':
            src = person_b
        elif self.source == 'd':
            src = NullDOB
        changed = ne(person_a, src), ne(person_b, src)
        set(person_a, src)
        set(person_b, src)
        return changed

class PMCaseDesc:
    def __init__(self, case_id, syndrome_id, deleted):
        self.case_id = case_id
        self.syndrome_id = syndrome_id
        self.syndrome = syndrome.syndromes[syndrome_id].name
        self.deleted = deleted
        self.style = ''
        if self.deleted:
            self.style = 'gray'

class Merge:
    def __init__(self, person_id_a, person_id_b):
        self.id_a = person_id_a
        self.id_b = person_id_b
        self._demogfields = None
        self.person = person.person()
        self.init_fields(*self._fetch_persons())

    def __getstate__(self):
        attrs = dict(vars(self))
        attrs['_demogfields'] = None
        return attrs

    def _fetch_persons(self, for_update=False):
        query = globals.db.query('persons', for_update=for_update)
        query.where_in('person_id', (self.id_a, self.id_b))
        try:
            x, y = query.fetchall()
        except ValueError:
            raise Error('Error fetching persons (incorrect number of rows)')
        if x.person_id == self.id_a and y.person_id == self.id_b:
            return x, y
        elif x.person_id == self.id_b and y.person_id == self.id_a:
            return y, x
        else:
            raise Error('Error fetching persons (wrong rows)')

    def demogfield(self, name):
        if self._demogfields is None:
            self._demogfields = {}
            for field in demogfields.get_demog_fields(globals.db, None):
                self._demogfields[field.name] = field
        return self._demogfields[name]

    def init_fields(self, person_a, person_b):
        self.person_a = person_a
        self.person_b = person_b
        self.fields = []
        for field in demogfields.get_demog_fields(globals.db, None):
            if hasattr(person_a, field.name) and hasattr(person_b, field.name):
                if field.name == 'DOB':
                    mc = DOBMergeCol(self, field, len(self.fields))
                else:
                    mc = MergeCol(self, field, len(self.fields))
                self.fields.append(mc)
        self.status, self.exclude_reason =\
            persondupe.get_status(self.id_a, self.id_b, for_update=True)

    def normalise(self):
        self.person.normalise()

    def desc_edit(self):
        edits = []
        for mc in self.fields:
            desc = mc.desc_edit()
            if desc:
                edits.append(desc)
        return edits

    def exclude(self):
        """
        This pair has been falsely identified as a duplicate - record
        the fact.
        """
        persondupe.exclude(self.id_a, self.id_b, self.exclude_reason)
        globals.db.commit()
        self.status = persondupe.STATUS_EXCLUDED

    def include(self):
        persondupe.clear_exclude(self.id_a, self.id_b)
        globals.db.commit()
        self.status = persondupe.STATUS_NEW

    def cases(self):
        query = globals.db.query('cases', order_by='case_id')
        query.where_in('person_id', (self.id_a, self.id_b))
        return query.fetchcols('case_id')

    def desc_cases(self):
        query = globals.db.query('cases', order_by='case_id')
        query.where_in('person_id', (self.id_a, self.id_b))
        cases = { False: [], True: [] }
        for case_id, deleted in query.fetchcols(('case_id', 'deleted')):
            cases[bool(deleted)].append(case_id)
        ids = ['%s' % case_id for case_id in cases[False]] + \
                ['(%s)' % case_id for case_id in cases[True]]
        return utils.commalist(ids, 'and')

    def desc_person_cases(self):
        def fmt(person_id):
            ids = ['%s' % case_id for case_id in cases[(person_id, False)]] + \
                  ['(%s)' % case_id for case_id in cases[(person_id, True)]]
            return utils.commalist(ids, 'and')
        query = globals.db.query('cases')
        query.where_in('person_id', (self.id_a, self.id_b))
        a_cases, b_cases = [], []
        cols = 'person_id', 'case_id', 'syndrome_id', 'deleted'
        for person_id, case_id, syndrome_id, deleted in query.fetchcols(cols):
            case_desc = PMCaseDesc(case_id, syndrome_id, deleted)
            if person_id == self.id_a:
                a_cases.append(case_desc)
            elif person_id == self.id_b:
                b_cases.append(case_desc)
        return a_cases, b_cases

    def merge(self, credentials):
        # lock the relevent cases
        persondupe.dupe_lock(globals.db)
        query = globals.db.query('cases', for_update=True)
        query.where_in('person_id', (self.id_a, self.id_b))
        case_ids = query.fetchcols('case_id')
        # lock the person records and make sure they haven't changed
        # and estimate how how many changes each record might require
        a_delta_count = b_delta_count = 0
        person_a, person_b = self._fetch_persons(for_update=True)
        for mc in self.fields:
            try:
                a_changed, b_changed = mc.apply(person_a, person_b)
            except PersonHasChanged:
                person_a.db_revert()
                person_b.db_revert()
                self.init_fields(person_a, person_b)
                raise
            if a_changed:
                a_delta_count += 1
            if b_changed:
                b_delta_count += 1
        # Now decide which direction to merge
        if b_delta_count > a_delta_count:
            update_person, delete_person = person_a, person_b
        else:
            update_person, delete_person = person_b, person_a
        # Update the log
        case_ids.sort()
        update_desc = update_person.db_desc()
        delete_desc = delete_person.db_desc()
        if not update_desc:
            update_desc = 'no edits required'
        if not delete_desc:
            delete_desc = 'no edits required'
        desc = 'Merge person, System IDs %s, UPDATED %s, DELETED %s' %\
                    (utils.commalist(case_ids, 'and'), update_desc, delete_desc)
        for case_id in case_ids:
            credentials.user_log(globals.db, desc, case_id=case_id)
        # Now update the cases and persons
        curs = globals.db.cursor()
        try:
            dbobj.execute(curs, 'UPDATE cases SET person_id=%s'
                                ' WHERE person_id=%s',
                          (update_person.person_id, delete_person.person_id))
        finally:
            curs.close()
        fuzzyperson.update(globals.db, update_person.person_id,
                           update_person.surname, update_person.given_names)
        update_person.db_update(refetch=False)
        delete_person.db_delete()
#        globals.db.rollback()  # when testing
        return update_person, case_ids


def merge_case_persons(case_id_a, case_id_b):
    query = globals.db.query('cases')
    query.where_in('case_id', (case_id_a, case_id_b))
    rows = dict(query.fetchcols(('case_id', 'person_id')))
    person_id_a = rows.get(case_id_a)
    person_id_b = rows.get(case_id_b)
    if person_id_a is None:
        raise Error('ID %s not found' % case_id_a)
    if person_id_b is None:
        raise Error('ID %s not found' % case_id_b)
    if person_id_a == person_id_b:
        raise Error('Both IDs map to the same person')
    persondupe.dupe_lock(globals.db)
    return Merge(person_id_a, person_id_b)
