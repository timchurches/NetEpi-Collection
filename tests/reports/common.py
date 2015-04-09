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

from tests import testcommon

expect_forms = [
    ('', '- Choose a form -'), 
    ('sars_exposure', 'Exposure History (SARS)'), 
    ('hospital_admit', 'Hospital admission'),
]

expect_headings = [
    'Status', 'Local ID', 'Case Assignment', 'System ID', 
    'Surname', 'Given names', 'Date of birth/Age', 'Sex', 
    'Locality/Suburb', 'State', 'Onset Date', 'Tags',
]

linereport = '''\
<?xml version="1.0"?>
<report type="line" name="Test Report">
 <syndrome>SARS</syndrome>
 <export strip_newlines="yes" column_labels="fields" row_type="forms" />
 <formdep name="sars_exposure" version="1" label="Exposure History (SARS)" />
 <groups>
  <group type="demog" label="Columns">
   <column name="case_status" label="Status" />
   <column name="local_case_id" label="Local ID" />
   <column name="case_assignment" label="Case Assignment" />
   <column name="case_id" label="System ID" />
   <column name="surname" label="Surname" />
   <column name="given_names" label="Given names" />
   <column name="sex" label="Sex" />
   <column name="locality" label="Locality/Suburb" />
   <column name="state" label="State" />
   <column name="onset_datetime" label="Onset Date" />
   <column name="tags" label="Tags" />
  </group>
  <group type="demog" label="Additional information" />
  <group type="form" form="sars_exposure" label="Exposure History (SARS)">
   <column name="close_contact" label="Contact with case" />
   <column name="contact_duration" label="Contact duration (hours)" />
   <column name="contact_date_first" label="Date of first contact" />
  </group>
 </groups>
 <ordering>
  <orderby column="onset_datetime" direction="asc" />
 </ordering>
</report>
'''

class ReportTest(testcommon.AppTestCase):

    def make_report(self, xml=None):
        if xml is None:
            xml = linereport
        return reports.parse_file(2, StringIO(xml))
