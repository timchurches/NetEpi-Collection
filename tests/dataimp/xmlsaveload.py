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
#

import unittest
from cStringIO import StringIO

from tests import testcommon

from casemgr.dataimp import editor
from casemgr.dataimp.elements import *
from casemgr.dataimp.xmlsave import xmlsave
from casemgr.dataimp.xmlload import xmlload

simple_rules = '''\
<?xml version="1.0"?>
<importrules name="test" mode="named" encoding="utf-8" fieldsep="," srclabel="import" conflicts="ignore">
 <agesource field="DOB" src="date-of-birth" age="age">
  <date format="YYYY/MM/DD" />
 </agesource>
 <ignore field="case_definition" />
 <fixed field="case_status" value="None" />
 <source field="given_names" src="firstname">
  <case mode="title" />
 </source>
 <form name="foo" version="1">
  <fixed field="bah" value="baz" />
  <multivalue field="checkbox" src="multichoice" delimiter="/">
   <case mode="upper" />
   <translate match="PROVISIONAL" to="SUSPECTED" />
   <regexp match="CONFIRMED_.*" to="CONFIRMED" />
  </multivalue>
 </form>
</importrules>
'''

class DataImpSaveNLoadTest(testcommon.TestCase):

    def test_save(self):
        rules = ImportRules('test')
        rule = ImportSource('given_names', 'firstname')
        rule.translations.append(Case('title'))
        rules.add(rule)
        rule = ImportAgeSource('DOB', 'date-of-birth', 'age')
        rule.translations.append(Date(format='YYYY/MM/DD'))
        rules.add(rule)
        rules.add(ImportFixed('case_status', 'None'))
        rules.add(ImportIgnore('case_definition'))
        form = rules.new_form('foo', 1)
        form.add(ImportFixed('bah', 'baz'))
        rule = ImportMultiValue('checkbox', 'multichoice', '/')
        rule.translations.append(Case('upper'))
        rule.translations.append(Translate('PROVISIONAL', 'SUSPECTED'))
        rule.translations.append(RegExp('CONFIRMED_.*', 'CONFIRMED'))
        form.add(rule)
        f = StringIO()
        xmlsave(f, rules)
        self.assertEqLines(f.getvalue(), simple_rules)

    def test_load(self):
        rules = xmlload(StringIO(simple_rules))
        f = StringIO()
        xmlsave(f, rules)
        self.assertEqual(f.getvalue(), simple_rules)
