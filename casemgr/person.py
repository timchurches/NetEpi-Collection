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
from mx import DateTime
from cocklebur import datetime, agelib, dbobj
from casemgr import globals, fuzzyperson
import config

Error = dbobj.ValidationError

sexes = [
    ('', 'Unknown'),
    ('F', 'Female'),
    ('M', 'Male'),
]

def expandsex(value):
    if value == 'M':
        return 'Male'
    elif value == 'F':
        return 'Female'
    elif not value:
        return 'Unknown'
    else:
        return value

indigenous_values = [
    ('', 'Unknown'),
    ('neither', 'Neither'),
    ('aboriginal', 'Aboriginal only'),
    ('aboriginal_tsi', 'Both Aboriginal and Torres Strait Islander'),
    ('tsi_only', 'Torres Strait Islander only'),
]
indigenous_map = dict([(k, v) for k, v in indigenous_values])


name_split = re.compile(r'([ ()/:;".,-]+)')
def soft_titlecase(text):
    """
    Titlecase /text/ unless /text/ is already (partially) mixed case.
    When titlecasing, apply special rules for things like "POBOX" and
    "O'Reilly".
    """
    casemap = {
        'po': 'PO',
        'gpo': 'GPO',
        'rmb': 'RMB',
        'pobox': 'PO Box',
        'von': 'von',
    }
    text = text.strip()
    words = name_split.split(text)
    for word in words:
        if word.istitle():
            return text
    result = []
    while len(words):
        word = words.pop(0)
        if word.islower() or word.isupper():
            word = word.capitalize()
            if word.startswith("O'"):
                word = "O'" + word[2:].capitalize()
        word = casemap.get(word.lower(), word)
        result.append(word)
        try:
            sep = words.pop(0)
        except IndexError:
            pass
        else:
            result.append(sep)
    return ''.join(result)


class Person(object):

    person_attrs = ('data_src',
                    'surname', 'given_names', 'interpreter_req', 
                    'DOB', 'DOB_prec', 'sex', 
                    'home_phone', 'work_phone', 'mobile_phone', 'fax_phone',
                    'e_mail', 
                    'street_address', 'locality', 
                    'state', 'postcode', 'country',
                    'alt_street_address', 'alt_locality', 
                    'alt_state', 'alt_postcode', 'alt_country',
                    'work_street_address', 'work_locality', 
                    'work_state', 'work_postcode', 'work_country',
                    'occupation',
                    'person_id',
                    'passport_number', 'passport_country',
                    'passport_number_2', 'passport_country_2',
                    'indigenous_status')

    def __init__(self):
        self.__clear_attrs()

    def from_person(self, seed_person):
        # seed_person might be a dbrow or another Person instance.
        self._copy_attrs(seed_person, self)
        dob = getattr(seed_person, 'DOB_edit', None)
        if dob:
            self.DOB_edit = dob
        else:
            self.DOB_edit = agelib.from_db(self)

    def __clear_attrs(self):
        for attr in self.person_attrs:
            setattr(self, attr, None)
        self.DOB_edit = None

    def _copy_attrs(self, src, dst):
        for attr in self.person_attrs:
            value = getattr(src, attr)
            if isinstance(value, str) and value == '!':
                value = None
            setattr(dst, attr, value)

    # NOTE - for "add" optionexpr's, null means "Unknown",
    # but for "search" optionexpr's, null means "Any" and "!" means "Unknown".
    # This inconsistency is necessary so that disabled demographic fields have
    # sensible behaviour, and so when a "search" transitions into an "add", the
    # field gets a sane default.
    def to_query(self, db, query, fuzzy=False):
        def q(query, field):
            value = getattr(self, field)
            if value:
                if value == '!':
                    query.where('persons.%s IS NULL' % field)
                else:
                    query.where('persons.%s ILIKE %%s' % field, 
                                dbobj.wild(value))
        self.normalise()
        q(query, 'data_src')
        q(query, 'locality')
        q(query, 'postcode')
        q(query, 'state')
        q(query, 'country')
        q(query, 'alt_locality')
        q(query, 'alt_postcode')
        q(query, 'alt_state')
        q(query, 'alt_country')
        q(query, 'work_locality')
        q(query, 'work_postcode')
        q(query, 'work_state')
        q(query, 'work_country')
        q(query, 'occupation')
        q(query, 'interpreter_req')
        q(query, 'indigenous_status')
        or_query = query.sub_expr(conjunction = 'OR')
        # sex will be not True or M or F
        sex = self.sex and self.sex.upper() != 'U' and self.sex
        # names AND dob AND sex
        if fuzzy and (dbobj.is_wild(self.surname) 
                            or dbobj.is_wild(self.given_names)):
            fuzzy = False
        if fuzzy:
            and_query = or_query.sub_expr(conjunction = 'AND')
            if self.surname or self.given_names:
                try:
                    fuzzyperson.find(and_query, self.surname, self.given_names)
                except ValueError, e:
                    raise Error(str(e))
            try:
                agelib.dob_query(and_query, 'persons.DOB', 
                                 self.DOB, self.DOB_prec)
            except datetime.Error, e:
                raise Error('Date of birth/age: %s' % e)
            if sex:
                and_query.where('persons.sex ilike %s', self.sex)
        else:
            if self.surname or self.given_names or sex or self.DOB:
                and_query = or_query.sub_expr(conjunction='AND')
                names = []
                if self.surname:
                    names.extend(self.surname.split())
                if self.given_names:
                    names.extend(self.given_names.split())
                if names:
                    for word in names:
                        word = dbobj.wild(word)
                        name_expr = and_query.sub_expr(conjunction='OR')
                        name_expr.where('surname ILIKE %s', word)
                        name_expr.where('given_names ILIKE %s', word)
                try:
                    agelib.dob_query(and_query, 'persons.DOB', 
                                     self.DOB, self.DOB_prec)
                except datetime.Error, e:
                    raise Error('Date of birth/age: %s' % e)
                if sex:
                    and_query.where('persons.sex ilike %s', self.sex)
        q(or_query, 'home_phone')
        q(or_query, 'work_phone')
        q(or_query, 'mobile_phone')
        q(or_query, 'fax_phone')
        q(or_query, 'e_mail')
        q(or_query, 'person_id')
        q(or_query, 'street_address')
        q(or_query, 'alt_street_address')
        q(or_query, 'work_street_address')
        if self.passport_number:
            if self.passport_country:
                and_query = or_query.sub_expr(conjunction = 'AND')
                q(and_query, 'passport_number')
                q(and_query, 'passport_country')
            else:
                q(or_query, 'passport_number')
        else:
            q(or_query, 'passport_country')
        if self.passport_number_2:
            if self.passport_country_2:
                and_query = or_query.sub_expr(conjunction = 'AND')
                q(and_query, 'passport_number_2')
                q(and_query, 'passport_country_2')
            else:
                q(or_query, 'passport_number_2')
        else:
            q(or_query, 'passport_country_2')

    def expandsex(self):
        return expandsex(self.sex)

    def validate(self):
        pass

    def normalise(self):
        try:
            agelib.to_db(self.DOB_edit, self)
        except datetime.Error, e:
            raise Error('Date of birth/age: %s' % e)
        for attr in self.person_attrs:
            value = getattr(self, attr)
            if value:
                try:
                    norm_fn = getattr(self, 'normalise_' + attr)
                except AttributeError:
                    pass
                else:
                    setattr(self, attr, norm_fn(value))

    def _name_upper(self, name):
        return name.strip().upper()

    normalise_surname = _name_upper
    normalise_sex = _name_upper
    normalise_locality = _name_upper
    normalise_alt_locality = _name_upper
    normalise_work_locality = _name_upper

    normalise_street_address = staticmethod(soft_titlecase)
    normalise_alt_street_address = staticmethod(soft_titlecase)
    normalise_work_street_address = staticmethod(soft_titlecase)
    normalise_given_names = staticmethod(soft_titlecase)

    def summary(self, order=None):
        from casemgr import demogfields
        fields = demogfields.get_demog_fields(globals.db, None)
        fields = fields.reordered_context_fields(order, 'result')
        return fields.summary(self)


class EditPerson(Person):

    def set_dbrow(self, dbrow):
        self.__dbrow = dbrow
        self._copy_attrs(self.__dbrow, self)
        self.DOB_edit = agelib.from_db(self)

#    def has_changed(self):
#        for attr in self.person_attrs:
#            a = getattr(self.__dbrow, attr)
#            b = getattr(self, attr)
#            if (a or b) and a != b:
#                import sys
#                print >> sys.stderr, '%r %r %r' % (attr, getattr(self.__dbrow, attr), getattr(self, attr))
#                return True
#        return False

    def has_changed(self):
        self.normalise()
        self._copy_attrs(self, self.__dbrow)
        try:
            return self.__dbrow.db_has_changed()
        finally:
            self.__dbrow.db_revert()

    def db_desc(self):
        self.normalise()
        self._copy_attrs(self, self.__dbrow)
        try:
            return self.__dbrow.db_desc()
        finally:
            self.__dbrow.db_revert()

    def db_update(self):
        do_fuzzy_update = (self.surname != self.__dbrow.surname or 
                           self.given_names != self.__dbrow.given_names)
        self._copy_attrs(self, self.__dbrow)
        try:
            self.__dbrow.db_update()
        except dbobj.RecordDeleted:
            raise dbobj.RecordDeleted('%s has been deleted (or merged) by another user' % config.person_label)
        self._copy_attrs(self.__dbrow, self)
        self.DOB_edit = agelib.from_db(self)
        if do_fuzzy_update:
            fuzzyperson.update(self.__dbrow.db(), self.person_id,
                               self.surname, self.given_names)

    def db_revert(self):
        self.__dbrow.db_revert()
        self._copy_attrs(self.__dbrow, self)

    def db_delete(self):
        self.__dbrow.db_delete()


def person(seed_person=None):
    """
    Returns a Person object *not* for editing, optionally filled with fields
    from /seed_person/.
    """
    person = Person()
    if seed_person is not None:
        person.from_person(seed_person)
    return person


def edit_row(dbrow):
    """
    Returns a Person object for editing representing an existing person given a
    person table row.
    """
    person = EditPerson()
    person.set_dbrow(dbrow)
    return person


def edit_id(person_id):
    """
    Returns a Person object for editing representing an existing person given a
    person_id
    """
    query = globals.db.query('persons')
    query.where('person_id = %s', person_id)
    dbrow = query.fetchone()
    if dbrow is None:
        raise Error('Person record not found')
    person = EditPerson()
    person.set_dbrow(dbrow)
    return person


def edit_new(seed_person=None):
    """
    Returns a new Person object for editing, optionally filled with fields from
    /seed_person/.
    """
    person = EditPerson()
    person.set_dbrow(globals.db.new_row('persons'))
    if seed_person is not None:
        person.from_person(seed_person)
    person.data_src = None
    return person


class DelayLoadPersons:

    def __init__(self, person_cls=Person):
        self.defered_person_ids = {}
        self.person_cls = person_cls

    def get(self, person_id):
        try:
            return self.defered_person_ids[person_id]
        except KeyError:
            inst = self.person_cls()
            self.defered_person_ids[person_id] = inst
            return inst

    def load(self, db):
        """
        Load all registered persons, return a list of ID's not found
        """
        query = db.query('persons')
        query.where_in('person_id', self.defered_person_ids.keys())
        for row in query.fetchall():
            p = self.defered_person_ids.pop(row.person_id)
            p.from_person(row)
        return self.defered_person_ids.keys()
