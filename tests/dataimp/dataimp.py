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

import os
import shutil
import unittest
from cStringIO import StringIO

from mx.DateTime.ISO import ParseDateTime as dt
from mx import DateTime

from cocklebur import dbobj
from casemgr.dataimp import dataimp, datasrc
from casemgr.dataimp.xmlload import xmlload
from casemgr.dataimp.elements import *

import config

from tests import testcommon



import_named_xml = '''\
<?xml version="1.0"?>
<importrules name="" mode="named" encoding="utf-8" 
    fieldsep="," srclabel="import" conflicts="ignore">
 <source field="surname" src="Surname" />
 <agesource field="DOB" src="DoB" age="Age">
  <date format="DD/MM/YYYY"/>
 </agesource>
 <source field="case_status" src="Status">
  <translate match="suspected" to="preliminary" ignorecase="yes" />
 </source>
 <fixed field="locality" value="NSW" />
 <ignore field="street_address" />
 <form name="sars_exposure" version="1">
  <source field="Contact_duration" src="Duration" />
  <fixed field="Close_contact" value="Unknown" />
  <ignore field="Contact_date_first" />
  <multivalue field="Contact_favourite_food" src="Likes" delimiter="/" />
 </form>
</importrules>
'''

import_positional_xml = '''\
<?xml version="1.0"?>
<importrules name="" mode="positional" encoding="utf-8" 
    fieldsep="," srclabel="import" conflicts="ignore">
 <source field="surname" src="1" />
 <agesource field="DOB" src="3" age="4">
  <date format="DD/MM/YYYY"/>
 </agesource>
 <source field="case_status" src="2">
  <translate match="suspected" to="preliminary" ignorecase="yes" />
 </source>
 <fixed field="locality" value="NSW" />
 <ignore field="street_address" />
 <form name="sars_exposure" version="1">
  <source field="Contact_duration" src="5" />
  <fixed field="Close_contact" value="Unknown" />
  <ignore field="Contact_date_first" />
  <multivalue field="Contact_favourite_food" src="7" delimiter="/" />
 </form>
</importrules>
'''

data = '''\
Surname,Status,DoB,Age,Duration,Id,Likes
blogs,confirmed,24/11/2001,,1,100,Icecream
smith,confirmed,,3,2,101,Lambchops/Apples
jones,suspected,4m,,,102,
'''

data_update = '''\
smith,confirmed,20/1/2000,,2,101,
williams,excluded,2/12/1940,,3,104,apples
'''

error_named_xml = '''\
<?xml version="1.0"?>
<importrules name="" mode="named" encoding="utf-8" 
    fieldsep="," srclabel="import" conflicts="ignore">
 <source field="surname" src="Surname" />
 <agesource field="DOB" src="DoB" age="Age">
  <date format="DD/MM/YYYY"/>
 </agesource>
 <source field="case_status" src="Status">
  <translate match="suspected" to="preliminary" ignorecase="yes" />
 </source>
 <fixed field="locality" value="NSW" />
 <ignore field="street_address" />
 <form name="sars_exposure" version="1">
  <source field="Contact_duration" src="Duration" />
  <source field="Close_contact" src="Contact" />
  <source field="Contact_date_first" src="Date" />
  <multivalue field="Contact_favourite_food" src="Likes" delimiter="/" />
 </form>
</importrules>
'''

# Need to reproduce the effects of casemgr.person DOB processing, as well as
# cocklebur.datetime, cocklebur.dbobj.column_describer and a round-trip through
# postgres - urgh.
truncate_tod = DateTime.RelativeDateTime(hour=0, minute=0, second=0)
three_years = DateTime.RelativeDateTime(years=3)
age3y = DateTime.now() - three_years - truncate_tod
four_months = DateTime.RelativeDateTime(months=4)
age4m = DateTime.now() - four_months - truncate_tod

class DataImpTest(testcommon.AppTestCase):

    create_tables = testcommon.AppTestCase.create_tables + (
        'nicknames',
        'person_phonetics',
        'syndrome_case_status',
        'syndrome_demog_fields',
        'import_defs',
    )

    scratchdir = os.path.join(os.path.dirname(__file__), 'scratch')

    def setUp(self):
        testcommon.AppTestCase.setUp(self)
        config.scratchdir = self.scratchdir
        os.mkdir(config.scratchdir)

    def tearDown(self):
        shutil.rmtree(self.scratchdir)
        testcommon.AppTestCase.tearDown(self)

    def dumprules(self, rules):
        # Debugging aid
        from casemgr.dataimp.xmlsave import xmlsave
        xmlsave(f, rules)
        print f.getvalue()

    def test_errors(self):
        rules = xmlload(StringIO(import_named_xml))
        cred = testcommon.DummyCredentials()
        imp = dataimp.PreviewImport(cred, 1, datasrc.NullDataImpSrc, rules)
        self.assertEqual(list(imp.errors), ['No data source selected'])

    def _test_preview(self, rules_xml, data):
        cred = testcommon.DummyCredentials()
        rules = xmlload(StringIO(rules_xml))
        src = datasrc.DataImpSrc('foo', StringIO(data))
        now = DateTime.DateTime(2010,7,20,17,23,1)
        imp = testcommon.freeze_time(now, dataimp.PreviewImport, 
                                     cred, 1, src, rules)
        self.failIf(imp.errors, imp.errors)
        self.assertEqual(imp.group_header, [('Demographics', 4),
                                            ('Exposure History (SARS)', 3)])
        self.assertEqual(imp.header, [
            'Status', 'Surname', 'Date of birth/Age', 'Locality/Suburb',
            'Contact with case',
            'Contact duration (hours)',
            'Favourite foods',
        ])
        self.assertEqual(imp.rows, [
            ['Confirmed', 'BLOGS', '24/11/2001 (8y)', 'NSW', 
                'Unknown', '1', 'Icecream'], 
            ['Confirmed', 'SMITH', '3 years', 'NSW', 
                'Unknown', '2', 'Lamb Chops/Apples'], 
            ['Preliminary', 'JONES', '4 months', 'NSW', 
                'Unknown', None, None]
        ])

    def test_preview_named(self):
        self._test_preview(import_named_xml, data)

    def test_preview_positional(self):
        positional_data = '\n'.join(data.splitlines()[1:])
        self._test_preview(import_positional_xml, positional_data)

    def test_preview_errors(self):
        cred = testcommon.DummyCredentials()
        rules = xmlload(StringIO(error_named_xml))
        data = '''\
Surname,Status,DoB,Age,Duration,Contact,Date,Id,Likes
blogs,XXX,24/11/2001,,,False,,100,
smith,confirmed,,10000,2,True,,101,Apples
jones,suspected,2008-1-30,,,Unknown,,102,Tomato
,,,,,,,,
williams,,,,a,XX,XX,103,
,,,,,,
'''
        src = datasrc.DataImpSrc('foo', StringIO(data))
        imp = dataimp.PreviewImport(cred, 1, src, rules)
        self.assertListEq(list(imp.errors), [
            'foo: record 5 (line 7): Column count is not constant: has 7 columns, expected 9',
            "record 1 (line 2): Status: 'XXX' not a valid choice",
            "record 2 (line 3): Date of birth/Age: date/time '10000' does not match format 'DD/MM/YYYY'",
            "record 3 (line 4): Date of birth/Age: date/time '2008-1-30' does not match format 'DD/MM/YYYY'",
            'record 3 (line 4): Favourite foods: tomato not valid choice(s)',
            'record 4 (line 5): Either Surname or Local ID must be specified',
            'record 4 (line 5): Exposure History (SARS): Contact with case: this field must be answered',
            "record 5 (line 6): Contact with case: 'XX' not a valid choice",
            'record 5 (line 6): Exposure History (SARS): Contact with case: this field must be answered',
            'record 5 (line 6): Exposure History (SARS): Contact duration (hours): value must be a number',
            'record 5 (line 6): Exposure History (SARS): Date of first contact: could not parse date "XX"',
        ])
        self.assertEqual(imp.errors.count(), 11)
        self.failUnless(0 not in imp.errors)
        self.failUnless(1 in imp.errors)
        self.failUnless(5 in imp.errors)
        self.failUnless(6 not in imp.errors)
        self.assertEqual(imp.errors.get(4), [
            'record 4 (line 5): Either Surname or Local ID must be specified',
            'record 4 (line 5): Exposure History (SARS): Contact with case: this field must be answered',
        ])
        # Check "too many errors" handling
        lines = data.splitlines()
        data = '\n'.join([lines[0]] + [lines[1]] * 101)
        src = datasrc.DataImpSrc('foo', StringIO(data))
        imp = dataimp.PreviewImport(cred, 1, src, rules)
        self.assertEqual(list(imp.errors)[0], 
            'More than %s errors, giving up' % imp.errors.MAX_ERRORS)
        self.assertEqual(imp.errors.count(), 100)


    def _fetch_rows(self):
        query = self.db.query('persons', order_by='person_id')
        query.join('JOIN cases USING (person_id)')
        query.join('LEFT JOIN case_form_summary USING (case_id)')
        query.join('LEFT JOIN form_sars_exposure_00001 USING (summary_id)')
        query.where('persons.data_src = %s', 'import')
        cols = (
            'surname', 'DOB', 'DOB_prec', 'case_status', 'locality',
            'street_address', 'local_case_id',
            'Contact_duration', 'Close_contact', 'Contact_date_first',
            'Contact_favourite_foodicecream',
            'Contact_favourite_foodapples',
            'Contact_favourite_foodlambchops',
        )
        return query.fetchcols(cols)

    def test_import_named(self):
        cred = testcommon.DummyCredentials()
        rules = xmlload(StringIO(import_named_xml))
        src = datasrc.DataImpSrc('foo', StringIO(data))
        imp = dataimp.DataImp(cred, 1, src, rules)
        self.failIf(imp.errors, imp.errors)
        self.assertEqual(imp.errors.count(), 0)
        self.assertEqual(imp.new_cnt, 3)
        self.assertEqual(imp.update_cnt, 0)
        self.assertListEq(self._fetch_rows(), [
            ('BLOGS', dt('2001-11-24'), 0, 'confirmed', 'NSW', None, None,
                1.0, 'Unknown', None, True, False, False), 
            ('SMITH', age3y, 366, 'confirmed', 'NSW', None, None,
                2.0, 'Unknown', None, False, True, True), 
            ('JONES', age4m, 31, 'preliminary', 'NSW', None, None,
                None, 'Unknown', None, False, False, False),
        ])

    def test_import_named_update(self):
        cred = testcommon.DummyCredentials()
        rules = xmlload(StringIO(import_named_xml))
        rules.add(ImportSource('local_case_id', 'Id'))
        src = datasrc.DataImpSrc('foo', StringIO(data))
        imp = dataimp.DataImp(cred, 1, src, rules)
        self.failIf(imp.errors, imp.errors)
        self.assertEqual(imp.errors.count(), 0)
        self.assertEqual(imp.new_cnt, 3)
        self.assertEqual(imp.update_cnt, 0)
        self.assertListEq(self._fetch_rows(), [
            ('BLOGS', dt('2001-11-24'), 0, 'confirmed', 'NSW', None, '100',
                1.0, 'Unknown', None, True, False, False), 
            ('SMITH', age3y, 366, 'confirmed', 'NSW', None, '101',
                2.0, 'Unknown', None, False, True, True), 
            ('JONES', age4m, 31, 'preliminary', 'NSW', None, '102',
                None, 'Unknown', None, False, False, False),
        ])
        src = datasrc.DataImpSrc('foo', StringIO(data + data_update))
        imp = dataimp.DataImp(cred, 1, src, rules)
        self.assertEqual(imp.new_cnt, 1)
        self.assertEqual(imp.update_cnt, 4)
        self.failIf(imp.errors, imp.errors)
        self.assertEqual(imp.errors.count(), 0)
        self.assertListEq(self._fetch_rows(), [
            ('BLOGS', dt('2001-11-24'), 0, 'confirmed', 'NSW', None, '100',
                1.0, 'Unknown', None, True, False, False), 
            ('SMITH', dt('2000-01-20'), 0, 'confirmed', 'NSW', None, '101',
                2.0, 'Unknown', None, False, False, False), 
            ('JONES', age4m, 31, 'preliminary', 'NSW', None, '102',
                None, 'Unknown', None, False, False, False),
            ('WILLIAMS', dt('1940-12-02'), 0, 'excluded', 'NSW', None, '104', 
                3.0, 'Unknown', None, False, True, False),
        ])

if __name__ == '__main__':
    unittest.main()
