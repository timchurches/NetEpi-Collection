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

from cStringIO import StringIO

from casemgr import reports
from casemgr.syndrome import SyndFormInfo
from casemgr.reports import ReportParseError
from casemgr.reports import xmlload
from casemgr.reports.report import ReportParamsBase

from tests.reports import common
from tests import testcommon

class ReportSaveNLoadTest(testcommon.TestCase):

    def expecterr(self, exc, xml):
        self.assertRaises(exc, reports.parse_file, None, StringIO(xml))

    def roundtrip(self, xml_in):
        syndrome_info = {
            'sars_exposure': SyndFormInfo('sars_exposure', 'SARS Exp', 12),
            'hospital_admit': SyndFormInfo('hospital_admit', 'Hosp Adm', 8),
        }
        saved = ReportParamsBase.form_info, ReportParamsBase.all_form_info
        ReportParamsBase.form_info = syndrome_info.get
        ReportParamsBase.all_form_info = syndrome_info.items
        try:
            params = xmlload.xmlload(StringIO(xml_in))
            f = StringIO()
            params.xmlsave(f)
            xml_out = f.getvalue()
            self.assertEqLines(xml_in, xml_out)
        finally:
            ReportParamsBase.form_info, ReportParamsBase.all_form_info = saved

    def test_error_handling(self):
        self.expecterr(ReportParseError, '<report />')
        self.expecterr(KeyError, '<report name="" type="linereport" />')

    def test_simple_line(self):
        self.roundtrip('''\
<?xml version="1.0"?>
<report type="line" name="xxx">
 <export strip_newlines="yes" column_labels="fields" row_type="forms" />
 <groups />
</report>
''')

    def test_filter(self):
        self.roundtrip('''\
<?xml version="1.0"?>
<report type="line" name="xxx">
 <export strip_newlines="yes" column_labels="fields" row_type="forms" />
 <formdep name="sars_exposure" version="12" label="SARS Exp" />
 <filter op="and">
  <term form="sars_exposure" field="contact_favourite_food" op="in">
   <value>AA</value>
  </term>
  <term field="local_case_id" op="pattern">
   <value>AA</value>
  </term>
  <term field="onset_datetime" op="range">
   <from inclusive="yes">2009-06-05 00:00:00</from>
   <to inclusive="yes">2009-06-12 00:00:00</to>
  </term>
  <term field="case_id" op="caseset" caseset="Foo">
   <commalist>1,2,3,4</commalist>
  </term>
 </filter>
 <groups />
</report>
''')

    def test_line(self):
        self.roundtrip('''\
<?xml version="1.0"?>
<report type="line" name="xxx">
 <export strip_newlines="yes" column_labels="fields" row_type="forms" />
 <formdep name="sars_exposure" version="12" label="SARS Exp" />
 <groups>
  <group type="demog" label="Columns">
   <column name="case_id" label="System ID" />
   <column name="case_status" label="Status" />
   <column name="surname" label="Surname" />
  </group>
  <group type="form" form="sars_exposure" label="SARS Exposure">
   <column name="close_contact" label="Close contact" />
   <column name="contact_duration" label="Contact duration" />
   <column name="contact_date_first" label="First contact" />
  </group>
 </groups>
 <ordering>
  <orderby column="surname" direction="asc" />
  <orderby column="given_names" direction="asc" />
 </ordering>
</report>
''')

    def test_crosstab(self):
        self.roundtrip('''\
<?xml version="1.0"?>
<report type="crosstab" name="testreport">
 <formdep name="sars_exposure" version="12" label="SARS Exp" />
 <crosstab include_empty_pages="yes">
  <axis name="row" type="demog" field="case_status" />
  <axis name="column" type="demog" field="sex" />
  <axis name="page" type="form" form="sars_exposure" field="contact_favourite_food" />
 </crosstab>
</report>
''')

    def test_epicurve(self):
        self.roundtrip('''\
<?xml version="1.0"?>
<report type="epicurve" name="testreport">
 <formdep name="sars_exposure" version="12" label="SARS Exp" />
 <epicurve missing_forms="no" format="png" nbins="D1">
  <dates field="notification_datetime" />
  <dates field="onset_datetime" />
  <stacking form="sars_exposure" field="contact_favourite_food" ratios="no">
   <suppress>False</suppress>
  </stacking>
 </epicurve>
</report>
''')

    def test_contactvis(self):
        self.roundtrip('''\
<?xml version="1.0"?>
<report type="contactvis" name="testreport">
 <contactvis format="png" labelwith="surname,given_names" vismode="None" />
</report>
''')


class ReportSharingTest(testcommon.AppTestCase):

    def test_sharing(self):
        """
        saving, loading and sharing semantics
        """
        def _menu(cred, private=[], unit=[], public=[], quick=[]):
            opts = reports.ReportMenu(cred, 2, 'line').by_sharing
            self.assertEqual([i.label for i in opts['private']], private)
            self.assertEqual([i.label for i in opts['unit']], unit)
            self.assertEqual([i.label for i in opts['public']], public)
            self.assertEqual([i.label for i in opts['quick']], quick)
        cred_user = testcommon.DummyCredentials()
        cred_unit = testcommon.DummyCredentials(user_id=2)
        cred_other = testcommon.DummyCredentials(user_id=2,unit_id=2)
        params = reports.new_report(2, 'line')
        params.label = 'Test Save'
        # Only visible to us
        params.sharing = 'private'
        params.save(cred_user)
        _menu(cred_user, private=['Test Save'])
        _menu(cred_unit)
        _menu(cred_other)
        # Visible to our unit
        params.sharing = 'unit'
        params.save(cred_user)
        _menu(cred_user, unit=['Test Save'])
        _menu(cred_unit, unit=['Test Save'])
        _menu(cred_other)
        # Visible to all
        params.sharing = 'public'
        params.save(cred_user)
        _menu(cred_user, public=['Test Save'])
        _menu(cred_unit, public=['Test Save'])
        _menu(cred_other, public=['Test Save'])
        # Visible to all & on home page (quick reports)
        reports.reports_cache.load()
        qr = reports.reports_cache.get_synd_unit(2, 1)
        self.assertEqual([r.label for r in qr], [])
        params.sharing = 'quick'
        params.save(cred_user)
        _menu(cred_user, quick=['Test Save'])
        _menu(cred_unit, quick=['Test Save'])
        _menu(cred_other, quick=['Test Save'])
        reports.reports_cache.load()
        qr = reports.reports_cache.get_synd_unit(2, 1)
        self.assertEqual([r.label for r in qr], ['Test Save'])
        # Loading
        loaded_params = reports.load(params.loaded_from_id, cred_user)
        self.failIf(loaded_params.check().have_errors())
        reports.delete(loaded_params.loaded_from_id)
        _menu(cred_user)
        _menu(cred_unit)
        _menu(cred_other)
        # "last" autosave
        params.autosave(cred_user)
        _menu(cred_user, private=['Most recent: Test Save']) 
        _menu(cred_unit)
        _menu(cred_other)
