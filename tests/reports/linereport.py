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
from itertools import izip

from casemgr import reports, messages

from tests.reports import common
from tests import testcommon

expectrows = [
    ([None, 'case_A', None, 1, 
      'Person_Surname_A', 'Person_Given_Name_A', 'Male', 
      None, None, '02/04/2003 00:00:00', 'TagTwo'],
     [('F11', 'Exposure History (SARS) F11', 
       'Contact with case: Yes, Contact duration (hours): 23.1, '
       'Date of first contact: 01/03/2003'),
      ('F44', 'Exposure History (SARS) F44', 
       'Contact with case: Unknown, Contact duration (hours): 29.1, '
       'Date of first contact: 02/01/2001')]),
    ([None, 'case_B', None, 2, 
      'Person_Surname_B', 'Person_Given_Name_B', 'Male', 
      None, None, '03/05/2003 00:00:00', 'TagOne TagTwo'],
     []),
    ([None, 'case_E_diff_unit_acl', None, 5, 
      'Person_Surname_B', 'Person_Given_Name_B', 'Male', 
      None, None, '04/06/2003 00:00:00', None],
     [('F33', 'Exposure History (SARS) F33', 
       'Contact with case: No, Contact duration (hours): 2.4, '
       'Date of first contact: 02/04/2002')]),
]

class LineReportTests(common.ReportTest):

    def test_report(self):
        """
        report generation
        """
        credentials = testcommon.DummyCredentials()
        params = self.make_report()
        self.assertEqual(params.get_case_ids(credentials), [1, 2, 5])
        self.assertEqual(params.count(credentials), 3)
        msgs = messages.Messages()
        chunker = params.report(credentials, msgs)
        report_headings = list(common.expect_headings)
        report_headings.remove('Date of birth/Age')
        self.assertEqual(chunker.headings(), report_headings)
        result = list(chunker)
        self.assertEqual(len(result), len(expectrows))
        for got, (col_want, text_want) in izip(result,expectrows):
            self.assertEqual(got.columns, col_want)
            self.assertEqual(got.freetext, text_want)
