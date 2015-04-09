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

from cocklebur import xmlparse
from casemgr.dataimp import elements

ParseError = xmlparse.ParseError

class ImportXMLParse(xmlparse.XMLParse):

    root_tag = 'importrules'

    class _Translate(xmlparse.Node):
        
        def end_element(self, parent):
            parent.rule.translations.append(self.ctor(**self.attrs))


    class Date(_Translate):
        permit_attrs = ('format',)
        ctor = elements.Date


    class Translate(_Translate):
        permit_attrs = ('match', 'to', 'ignorecase:bool')
        ctor = elements.Translate


    class RegExp(_Translate):
        permit_attrs = ('match', 'to', 'ignorecase:bool')
        ctor = elements.RegExp


    class Case(_Translate):
        permit_attrs = ('mode',)
        ctor = elements.Case


    class _Rule(xmlparse.Node):
        __slots__ = ('rule',)
        subtags = ('date', 'translate', 'regexp', 'case')

        def start_element(self, parent):
            self.rule = self.ctor(**self.attrs)

        def end_element(self, parent):
            parent.node.add(self.rule)


    class Source(_Rule):
        permit_attrs = ('field', 'src', 'name', 'pos')
        ctor = elements.ImportSource

    # Legacy
    class Named(Source): pass
    class Positional(Source): pass

    class AgeSource(Source):
        permit_attrs = ('field', 'src', 'age')
        ctor = elements.ImportAgeSource

    class MultiValue(Source):
        permit_attrs = ('field', 'src', 'delimiter')
        ctor = elements.ImportMultiValue

    class Fixed(_Rule):
        ctor = elements.ImportFixed
        permit_attrs = ('field', 'value')


    class Ignore(_Rule):
        ctor = elements.ImportIgnore
        permit_attrs = ('field',)


    class Form(xmlparse.Node):
        __slots__ = ('node')
        permit_attrs = (
            'name', 'version:int',
        )
        subtags = (
            'source', 'agesource', 'multivalue', 'fixed', 'ignore',
        )

        def start_element(self, parent):
            self.node = parent.node.new_form(**self.attrs)


    class ImportRules(xmlparse.Node):
        __slots__ = 'node',
        permit_attrs = (
            'name', 'mode', 'encoding', 'fieldsep', 'srclabel', 'conflicts',
        )
        subtags = (
            'form', 'source', 'agesource', 'named', 'positional', 
            'fixed', 'ignore',
        )

        def start_element(self, parent):
            self.node = elements.ImportRules(**self.attrs)


def xmlload(f):
    return ImportXMLParse().parse(f).node
