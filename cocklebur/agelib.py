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
Date-of-birth & age handling
"""
from __future__ import division

import re

from mx import DateTime

from cocklebur import datetime

# Tim: Medical shorthand often uses "3/52" to mean 3 weeks, "4/12" to mean 4
# months, "5/7" to mean 5 days, "13/24" to mean 13 hours, but not "43/60"
# because that could be minutes or seconds. But 3wks or 3w, 4mths or 4m, 5d,
# 13hrs etc are also used. 

Error = datetime.Error

PREC_YEAR = 366
PREC_MONTH = 31
PREC_WEEK = 7
PREC_DAY = 1
PREC_DOB = 0

class Age(object):
    """
    An Age records an integer /age/ in /units/, where units is:
        'y' for years
        'm' for months
        'w' for weeks
        'd' for days
    """
    __slots__ = 'age', 'units'

    def __init__(self, age, units):
        if units not in 'ymwd':
            raise ValueError('bad age units' % units)
        if units == 'y' and (age < 0 or age >= 140):
            raise Error('Age outside valid range: %s' % age)
        self.age = int(age)
        self.units = units

    def __eq__(self, other):
        if isinstance(other, Age):
            return self.age == other.age and self.units == other.units
        elif isinstance(other, tuple):
            return (self.age, self.units) == other
        return False

    age_unit_abr = [
        ('y', ('years', 'year', 'yrs', 'yr', 'y')),
        ('m', ('months', 'month', 'mths', 'mth', 'm')),
        ('w', ('weeks', 'week', 'wks', 'wk', 'w')),
        ('d', ('days', 'day', 'd')),
    ]
    unit_abr_map = {}
    for unit, abrs in age_unit_abr:
        for abr in abrs:
            unit_abr_map[abr] = unit

    age_units_re = re.compile('(\d+)\s*(\D+)$')

    denom_units = {
        12: 'm',
        52: 'w',
        7: 'd'
    }

    def parse(cls, agestr):
        """
        Parse an age, for example 4/12 or 4m
        """
        try:
            if not agestr:
                raise ValueError
            agestr = agestr.strip()
            if '/' in agestr:
                age, denom = agestr.split('/', 1)
                age = int(age.rstrip())
                units = cls.denom_units[int(denom.lstrip())]
            else:
                match = cls.age_units_re.match(agestr)
                if match:
                    age = int(match.group(1))
                    units = cls.unit_abr_map[match.group(2).lower()]
                else:
                    age = int(agestr)
                    units = 'y'
            return cls(age, units)
        except (KeyError, ValueError):
            raise Error('Unknown age format: %r' % agestr)
    parse = classmethod(parse)

    def from_dob(cls, dob, now=None):
        """
        Make an Age from a date-of-birth
        """
        if hasattr(dob, 'mx'):
            dob = dob.mx()
        elif not isinstance(dob, DateTime.DateTimeType):
            raise TypeError('bad date-of-birth type %r' % dob)
        if now is None:
            now = DateTime.now()
        if dob > now:
            raise Error('date-of-birth %s is in the future' % dob)
        age = DateTime.Age(now, dob)
        if age.years >= 3:
            return cls(age.years + age.months / 12, 'y')
        months = age.years * 12 + age.months + age.days / 30.5
        if months >= 3:
            return cls(months, 'm')
        age = now - dob
        if age.days > 30:
            return cls(age.days / 7, 'w')
        return cls(age.days, 'd')
    from_dob = classmethod(from_dob)

    def to_dobprec(self, now=None):
        """
        Given an integer age and unit code, return a DOB & precision
        """
        if self.units == 'y':
            age = DateTime.RelativeDateTime(years=self.age)
            prec = PREC_YEAR
        elif self.units == 'm':
            age = DateTime.RelativeDateTime(months=self.age)
            prec = PREC_MONTH
        elif self.units == 'w':
            age = DateTime.RelativeDateTime(weeks=self.age)
            prec = PREC_WEEK
        elif self.units == 'd':
            age = DateTime.RelativeDateTime(days=self.age)
            prec = PREC_DAY
        else:
            raise AssertionError('Bad age units: %s' % self.units)
        if now is None:
            now = datetime.now()
        return now - age, prec

    units_map = {
        'y': ('year', 'years'),
        'm': ('month', 'months'),
        'w': ('week', 'weeks'),
        'd': ('day', 'days'),
    }

    def __str__(self):
        return '%.0f%s' % (self.age, self.units)

    def friendly(self):
        units = self.units_map[self.units][int(self.age) != 1]
        return '%.0f %s' % (self.age, units)


def agestr(dob, now=None):
    """
    Given a DOB return a string describing the age
    """
    if dob:
        try:
            return str(Age.from_dob(dob, now))
        except Error:
            return '??'


def dob_if_dob(dob, prec):
    """
    If exact DOB is known, return as a string, otherwise return None
    """
    if dob and not prec:
        return dob.strftime(datetime.mx_parse_date.format)


def age_if_dob(dob):
    """
    If DOB (not age) string, return age string, otherwise return None
    """
    if dob:
        try:
            return str(Age.from_dob(datetime.mx_parse_date(dob)))
        except Error:
            pass


def parse_dob_or_age(value, now=None):
    """
    Given a date-of-birth or age string, return a DOB & precision
    """
    if not value:
        return None, None
    try:
        return Age.parse(value).to_dobprec(now)
    except Error:
        pass
    try:
        return datetime.mx_parse_date(value).mx(), PREC_DOB
    except Error:
        raise Error('Invalid DOB/age %r' % value)


def dob_query(query, field, dob, prec):
    """
    Add a DOB clause to the supplied /query/. /field/ is the base column name.
    """
    if dob:
        q = 'abs(%s-%%s::date) <= GREATEST(%s_prec,%%s)' % (field, field)
        query.where(q, dob, prec)


def dobage_str(dob, prec, now=None):
    """
    If exact DOB, return DOB and age, otherwise just return age string
    """
    if not dob:
        return None
    if isinstance(dob, basestring):
        try:
            dob, prec = parse_dob_or_age(dob)
        except datetime.Error, e:
            return '??' 
    try:
        age = Age.from_dob(dob, now)
    except Error:
        return '??'
    if prec:
        return age.friendly()
    else:
        dob = dob.strftime(datetime.mx_parse_date.format)
        return '%s (%s)' % (dob, age)


def from_db(row, field='DOB'):
    """
    Given an object /row/ with DOB+DOB_prec, return either a DOB string
    or an age string.
    """
    dob = getattr(row, field)
    if dob:
        prec = getattr(row, field + '_prec')
        if prec:
            return str(Age.from_dob(dob))
        else:
            return dob.strftime(datetime.mx_parse_date.format)


def to_db(value, row, field='DOB'):
    """
    Given either a DOB string or an age string, set DOB+DOB_prec on the 
    object /row/ if the value is different.
    """
    if not value:
        dob = None
        prec = None
    elif isinstance(value, basestring):
        row_dob = getattr(row, field)
        row_age = None
        if row_dob:
            row_age = Age.from_dob(row_dob)
        try:
            age = Age.parse(value)
            if age == row_age:
                return
            dob, prec = age.to_dobprec()
        except Error:
            try:
                dob = datetime.mx_parse_date(value).mx()
                prec = PREC_DOB
            except Error:
                raise Error('Invalid DOB/age %r' % value)
    else:
        dob = value
        prec = PREC_DOB
    setattr(row, field, dob)
    setattr(row, field+'_prec', prec)
