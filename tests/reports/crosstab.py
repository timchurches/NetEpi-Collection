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

from casemgr import reports, messages

from tests.reports import common
from tests import testcommon

crosstab = '''\
<?xml version="1.0"?>
<report type="crosstab" name="testreport">
 <formdep name="sars_exposure" version="12" label="SARS Exp" />
 <crosstab include_empty_pages="yes">
  <axis name="row" type="demog" field="case_status" />
  <axis name="column" type="demog" field="sex" />
  <axis name="page" type="form" form="sars_exposure" field="Close_contact" />
 </crosstab>
</report>
'''

row_options = [(None, 'Missing'), ('!TOTAL!', 'TOTAL')]
col_options = [('M', 'Male'), ('!TOTAL!', 'TOTAL')]
page_options = [
    ('True', 'Yes'), 
    ('False', 'No'), 
    ('Unknown', 'Unknown'), 
    ('!TOTAL!', 'TOTAL')
]

cells_expect = [
    [[1, 1], 
     [1, 1]], 
    [[1, 1], 
     [1, 1]], 
    [[1, 1], 
     [1, 1]], 
    [[3, 3], 
     [3, 3]],
]

style_expect = [
    [['', 'l'], 
     ['t', 't l']], 
    [['', 'l'], 
     ['t', 't l']], 
    [['', 'l'], 
     ['t', 't l']], 
    [['', 'l'], 
     ['t', 't l']],
]

id_expect = [
    [[[1], [1]], [[1], [1]]], 
    [[[5], [5]], [[5], [5]]], 
    [[[1], [1]], [[1], [1]]], 
    [[[1, 5], [1, 5]], [[1, 5], [1, 5]]]
]

desc_expect = [
    [['Status: Missing, Sex: Male, Contact with case: Yes', 
      'Status: Missing, Contact with case: Yes'],
     ['Sex: Male, Contact with case: Yes', 
      'Contact with case: Yes']], 
    [['Status: Missing, Sex: Male, Contact with case: No',
      'Status: Missing, Contact with case: No'],
     ['Sex: Male, Contact with case: No',
      'Contact with case: No']],
    [['Status: Missing, Sex: Male, Contact with case: Unknown',
      'Status: Missing, Contact with case: Unknown'],
     ['Sex: Male, Contact with case: Unknown',
      'Contact with case: Unknown']],
    [['Status: Missing, Sex: Male',
      'Status: Missing'],
     ['Sex: Male', '']]
]

demog_col_options = [
    ('interpreter_req', 'Interpreter'),
    ('case_status', 'Status'),
    ('case_assignment', 'Case Assignment'),
    ('sex', 'Sex'),
    ('state', 'State'),
    ('passport_country', 'Passport country/Nationality'),
]

class CrosstabReportTests(common.ReportTest):

    def test_crosstab(self):
        credentials = testcommon.DummyCredentials()
        params = self.make_report(crosstab)
        self.assertEqual(params.row.form_options(), [
            ('none:', 'None'),
            ('demog:', 'Demographic fields'),
            ('form:sars_exposure', 'Exposure History (SARS)'),
            ('form:hospital_admit', 'Hospital admission'),
        ])
        self.assertEqual(params.row.show_fields(), True)
        self.assertEqual(params.col.show_fields(), True)
        self.assertEqual(params.page.show_fields(), True)
        self.assertListEq(params.row.col_options(), demog_col_options)
        self.assertListEq(params.col.col_options(), demog_col_options)
        self.assertListEq(params.page.col_options(),
            [('close_contact', 'Contact with case')])
        msgs = messages.Messages()
        report = params.report(credentials, msgs)
        self.assertEqual(report.row.options, row_options)
        self.assertEqual(report.col.options, col_options)
        self.assertEqual(report.page.options, page_options)
        # Check counts
        pages = []
        for page_val, page_lab in report.page.options:
            page = []
            for row_val, row_label in report.row.options:
                row = []
                for col_val, col_label in report.col.options:
                    key = row_val, col_val, page_val
                    row.append(report.tally[key])
                page.append(row)
            pages.append(page)
        self.assertEqual(pages, cells_expect)
        # Check styling
        pages = []
        for page_val, page_lab in report.page.options:
            page = []
            for row_val, row_label in report.row.options:
                row = []
                for col_val, col_label in report.col.options:
                    row.append(report.style(row_val, col_val))
                page.append(row)
            pages.append(page)
        self.assertEqual(pages, style_expect)
        # Case ID Lookup
        pages = []
        for page_idx in range(len(report.page.options)):
            page = []
            for row_idx in range(len(report.row.options)):
                row = []
                for col_idx in range(len(report.col.options)):
                    coords = row_idx, col_idx, page_idx
                    row.append(report.get_key_case_ids(*coords))
                page.append(row)
            pages.append(page)
        self.assertEqual(pages, id_expect)
        # Cell desc Lookup
        pages = []
        for page_idx in range(len(report.page.options)):
            page = []
            for row_idx in range(len(report.row.options)):
                row = []
                for col_idx in range(len(report.col.options)):
                    coords = row_idx, col_idx, page_idx
                    row.append(report.desc_key(*coords))
                page.append(row)
            pages.append(page)
        self.assertEqual(pages, desc_expect)
