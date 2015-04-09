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

from casemgr import reports

from tests import testcommon
from tests.reports import common

class ExportTests(common.ReportTest):
    export_forms_label_expect = [
        ['Status', 'Local ID', 'Case Assignment', 'System ID', 'Surname', 'Given names', 'Sex', 'Locality/Suburb', 'State', 'Onset Date', 'Tags', 'Contact with case', 'Contact duration (hours)', 'Date of first contact'], 
        [None, 'case_A', None, 1, 'Person_Surname_A', 'Person_Given_Name_A', 'Male', None, None, '02/04/2003 00:00:00', 'TagTwo', 'Yes', '23.1', '01/03/2003'], 
        [None, 'case_A', None, 1, 'Person_Surname_A', 'Person_Given_Name_A', 'Male', None, None, '02/04/2003 00:00:00', 'TagTwo', 'Unknown', '29.1', '02/01/2001'], 
        [None, 'case_B', None, 2, 'Person_Surname_B', 'Person_Given_Name_B', 'Male', None, None, '03/05/2003 00:00:00', 'TagOne TagTwo', None, None, None], 
        [None, 'case_E_diff_unit_acl', None, 5, 'Person_Surname_B', 'Person_Given_Name_B', 'Male', None, None, '04/06/2003 00:00:00', None, 'No', '2.4', '02/04/2002']
    ]
    export_forms_dbcols_expect = list(export_forms_label_expect)
    export_forms_dbcols_expect[0] = ['case_status', 'local_case_id', 'case_assignment', 'case_id', 'surname', 'given_names', 'sex', 'locality', 'state', 'onset_datetime', 'tags', 'sars_exposure.close_contact', 'sars_exposure.contact_duration', 'sars_exposure.contact_date_first']

    def test_export_forms(self):
        """
        CSV report export (by form)
        """
        credentials = testcommon.DummyCredentials()
        params = self.make_report()
        params.export_row_type = 'forms'
        params.export_column_labels = 'fields'
        rows = list(params.export_rows(credentials))
        self.assertEqual(rows, self.export_forms_label_expect)
        params.export_column_labels = 'dbcols'
        rows = list(params.export_rows(credentials))
        self.assertEqual(rows, self.export_forms_dbcols_expect)

    export_cases_label_expect = [
        ['Status', 'Local ID', 'Case Assignment', 'System ID', 'Surname', 'Given names', 'Sex', 'Locality/Suburb', 'State', 'Onset Date', 'Tags', 'Contact with case (1)', 'Contact duration (hours) (1)', 'Date of first contact (1)', 'Contact with case (2)', 'Contact duration (hours) (2)', 'Date of first contact (2)'], 
        [None, 'case_A', None, 1, 'Person_Surname_A', 'Person_Given_Name_A', 'Male', None, None, '02/04/2003 00:00:00', 'TagTwo', 'Yes', '23.1', '01/03/2003', 'Unknown', '29.1', '02/01/2001'], 
        [None, 'case_B', None, 2, 'Person_Surname_B', 'Person_Given_Name_B', 'Male', None, None, '03/05/2003 00:00:00', 'TagOne TagTwo', None, None, None, None, None, None], 
        [None, 'case_E_diff_unit_acl', None, 5, 'Person_Surname_B', 'Person_Given_Name_B', 'Male', None, None, '04/06/2003 00:00:00', None, 'No', '2.4', '02/04/2002', None, None, None]
    ]
    export_cases_dbcols_expect = list(export_cases_label_expect)
    export_cases_dbcols_expect[0] = ['case_status', 'local_case_id', 'case_assignment', 'case_id', 'surname', 'given_names', 'sex', 'locality', 'state', 'onset_datetime', 'tags', 'sars_exposure.close_contact.1', 'sars_exposure.contact_duration.1', 'sars_exposure.contact_date_first.1', 'sars_exposure.close_contact.2', 'sars_exposure.contact_duration.2', 'sars_exposure.contact_date_first.2']

    def test_export_cases(self):
        """
        CSV report export (by case)
        """
        credentials = testcommon.DummyCredentials()
        params = self.make_report()
        params.export_row_type = 'cases'
        params.export_column_labels = 'fields'
        rows = list(params.export_rows(credentials))
        self.assertEqual(rows, self.export_cases_label_expect)
        params.export_column_labels = 'dbcols'
        rows = list(params.export_rows(credentials))
        self.assertEqual(rows, self.export_cases_dbcols_expect)
