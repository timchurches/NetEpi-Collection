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
This is an abstract representation of a set of import rules
"""

import sys
import re
try:
    set
except NameError:
    from sets import Set as set

from cocklebur import datetime
from casemgr import globals
from casemgr.dataimp.common import DataImpElementError as Error

debug = False

class ElementBase(object):

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return False
        if debug and self.__dict__ != other.__dict__:
            print >> sys.stderr, 'EQ', self.__class__.__name__
            keys = set(self.__dict__) | set(other.__dict__)
            for key in keys:
                if key not in self.__dict__:
                    print >> sys.stderr, '  %s not in self' % key
                elif key not in other.__dict__:
                    print >> sys.stderr, '  %s not in other' % key
                elif self.__dict__[key] != other.__dict__[key]:
                    print >> sys.stderr, '  %s not equal' % key
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class TranslationBase(ElementBase):
    pass


class Date(TranslationBase):
    
    def __init__(self, format):
        self.format = format
        self.parse = datetime.fmt_parser(format, age_years=True)

    def translate(self, value):
        if value:
            try:
                return self.parse(value)
            except datetime.Error:
                raise Error('date/time %r does not match format %r' %
                                 (value, self.format))

    def desc(self):
        return ['date format %r' % self.format]


class Translate(TranslationBase):
    
    def __init__(self, match, to, ignorecase=False):
        self.match = match
        self.to = to
        self.ignorecase = ignorecase

    def translate(self, value):
        if value:
            if self.ignorecase:
                if value.lower() == self.match.lower():
                    value = self.to
            else:
                if value == self.match:
                    value = self.to
            return value

    def desc(self):
        return ['translate %r to %r' % (self.match, self.to)]


class RegExp(TranslationBase):
    
    def __init__(self, match, to, ignorecase=False):
        self.match = match
        self.to = to
        self.ignorecase = ignorecase
        self.match_re = None

    def __deepcopy__(self, memo):
        # Work-around a problem in some versions of python. _sre.SRE_Pattern
        # has a __deepcopy__ method that raises TypeError: cannot deepcopy this
        # pattern object, but bugs in 2.3.5 and 2.4.5(?) mask this method,
        # allowing the SRE_Pattern to be deepcopied via the pickle machinery.
        return RegExp(self.match, self.to, self.ignorecase)

    def translate(self, value):
        try:
            if self.match_re is None:
                if self.ignorecase:
                    self.match_re = re.compile(self.match, re.IGNORECASE)
                else:
                    self.match_re = re.compile(self.match)
            if value:
                return self.match_re.sub(self.to, value)
        except re.error, e:
            raise Error('regexp translation: %s' % e)

    def desc(self):
        return ['regexp %r to %r' % (self.match, self.to)]


class Case(TranslationBase):
    
    def __init__(self, mode):
        self.mode = mode

    def translate(self, value):
        if value:
            if self.mode == 'lower':
                return value.lower()
            elif self.mode == 'upper':
                return value.upper()
            elif self.mode == 'title':
                return value.title()
            elif self.mode == 'capitalize':
                return value.capitalize()
            else:
                return value

    def desc(self):
        return ['case %r' % (self.mode,)]


class ImportColumnBase(ElementBase):

    def __init__(self, field):
        self.field = field
        self.translations = []

    def translation(self, xlate):
        self.translations.append(xlate)

    def translate(self, value):
        for translation in self.translations:
            value = translation.translate(value)
        return value

    def desc(self):
        desc = []
        for t in self.translations:
            desc.extend(t.desc())
        return desc


class ImportSource(ImportColumnBase):
    
    def __init__(self, field, src=None, pos=None, name=None):
        ImportColumnBase.__init__(self, field)
        self.src = src or pos or name  # Legacy

    def desc(self):
        desc = ['source column %r' % self.src]
        desc.extend(ImportColumnBase.desc(self))
        return desc


class ImportAgeSource(ImportColumnBase):
    
    def __init__(self, field, src=None, age=None):
        ImportColumnBase.__init__(self, field)
        self.src = src
        self.age = age

    def desc(self):
        desc = ['age/dob column %r' % self.src]
        if self.age:
            desc.append('age %r' % self.age)
        desc.extend(ImportColumnBase.desc(self))
        return desc


class ImportMultiValue(ImportSource):

    def __init__(self, field, src=None, delimiter=None):
        ImportSource.__init__(self, field, src)
        self.delimiter = delimiter

    def desc(self):
        desc = ['multivalue column %r, delimiter %r' % (self.src, self.delimiter)]
        desc.extend(ImportColumnBase.desc(self))
        return desc

    def translate(self, value):
        result = set()
        if value:
            for value in value.split(self.delimiter):
                for translation in self.translations:
                    value = translation.translate(value)
                if value:
                    result.add(value)
        return result


class ImportFixed(ImportColumnBase):
    def __init__(self, field, value):
        ImportColumnBase.__init__(self, field)
        self.value = value        

    def desc(self):
        return ['set to %r' % self.value]


class ImportIgnore(ImportColumnBase):

    def desc(self):
        return ['ignore']


class RuleSetBase(ElementBase):
    def __init__(self):
        self.rules_by_name = {}

    def __nonzero__(self):
        return bool(self.rules_by_name)

    def __getitem__(self, name):
        return self.rules_by_name[name]

    def get(self, name, default=None):
        return self.rules_by_name.get(name, default)

    def __contains__(self, name):
        return name in self.rules_by_name

    def __iter__(self):
        names = self.rules_by_name.keys()
        names.sort()
        for name in names:
            yield self.rules_by_name[name]

    def add(self, col):
        self.rules_by_name[col.field] = col

    def drop(self, field):
        self.rules_by_name.pop(field, None)


class ImportForm(RuleSetBase):
    def __init__(self, name, version):
        RuleSetBase.__init__(self)
        self.name = name
        self.version = version


class ImportRules(RuleSetBase):
    def __init__(self, name, mode='named', encoding='utf-8', fieldsep=',',
                 srclabel='import', conflicts='ignore'):
        RuleSetBase.__init__(self)
        self.name = name
        self.mode = mode
        self.encoding = encoding
        self.fieldsep = fieldsep
        self.srclabel = srclabel
        self.conflicts = conflicts
        self._forms = {}

    def has_forms(self):
        return bool(self._forms)

    def new_form(self, name, version):
        self._forms[name] = form = ImportForm(name, version)
        return form

    def del_form(self, name):
        del self._forms[name]

    def get_form(self, name):
        return self._forms[name]

    def forms(self):
        # XXX do we really need to sort? We need a stable order in the XML
        # representation for testing purposes, but the sort could be done
        # in xmlsave.
        anno_forms = self._forms.items()
        anno_forms.sort()
        return [form for name, form in anno_forms]

