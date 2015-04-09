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

from tests.reports import common
from tests import testcommon

expect_availcols = [
    '',
    'home_phone,work_phone,mobile_phone',
    'age', 'DOB_only', 'deleted',
    'delete_timestamp', 'delete_reason', 'fax_phone', 'home_phone',
    'interpreter_req', 'mobile_phone',
    'notification_datetime', 'passport_country', 'passport_number',
    'postcode', 'street_address', 'work_phone',
]

expect_form_fields = [
    'close_contact', 'contact_duration', 'contact_date_first', 
    'contact_date_last', 'contact_favourite_food'
]

available_form_fields =  [
    '', '!all', '!summary',
    'contact_duration', 'close_contact', 'contact_date_first',
    'contact_favourite_food', 'contact_date_last',
]

class ReportOutgroupTests(testcommon.AppTestCase):

    def test_outgroup(self):
        """
        output column parameter handling
        """
        params = reports.new_report(2, 'line')
        # List of available demog fields
        self.assertEqual(len(params.outgroups), 2)
        availcols = [c[0] for c in params.outgroups[0].available_cols()]
        self.assertEqual(availcols, expect_availcols)
        self.assertEqual(len(params.outgroups[0]), 12)
        self.assertEqual(params.outgroups[0].labels(), common.expect_headings)

        # Group movement
        self.assertEqual(params.has_up(0), False)
        self.assertEqual(params.has_dn(0), False)
        self.assertEqual(params.has_up(1), False)
        self.assertEqual(params.has_dn(1), False)
        params.add_caseperson()
        self.assertEqual(len(params.outgroups), 3)
        self.assertEqual(params.has_dn(1), True)
        self.assertEqual(params.has_dn(2), False)
        self.assertEqual(params.has_up(2), True)
        params.colop('gdel', 2)
        # demog fields "float" to the top
        params.add_form('sars_exposure')
        params.add_caseperson()
        self.assertEqual(params.outgroups[2].form_name, None)
        self.assertEqual(params.outgroups[3].form_name, 'sars_exposure')
        params.add_form('hospital_admit')
        params.colop('gdn', 3)
        self.assertEqual(params.outgroups[3].form_name, 'hospital_admit')
        self.assertEqual(params.outgroups[4].form_name, 'sars_exposure')
        # no-op at end of list
        params.colop('gdn', 4)
        self.assertEqual(params.outgroups[3].form_name, 'hospital_admit')
        self.assertEqual(params.outgroups[4].form_name, 'sars_exposure')
        params.colop('gup', 4)
        self.assertEqual(params.outgroups[3].form_name, 'sars_exposure')
        self.assertEqual(params.outgroups[4].form_name, 'hospital_admit')
        # Can't move form above demog
        params.colop('gup', 3)
        self.assertEqual(params.outgroups[3].form_name, 'sars_exposure')
        self.assertEqual(params.outgroups[4].form_name, 'hospital_admit')

        # List of available form fields
        availcols = [c[0] for c in params.outgroups[3].available_cols()]
        self.assertEqual(availcols, available_form_fields)
        # Add "all" form fields
        self.assertEqual(params.outgroups[3].names(), [])
        params.outgroups[3].addcol = '!all'
        params.cols_update()
        self.assertEqual(params.outgroups[3].names(), expect_form_fields)
        # Add "summary" form fields
        params.colop('gdel', 3)
        params.add_form('sars_exposure')
        params.outgroups[4].addcol = '!summary'
        params.cols_update()
        self.assertEqual(params.outgroups[4].names(), expect_form_fields)
        # Add specific form fields
        params.colop('gdel', 4)
        params.add_form('sars_exposure')
        params.outgroups[4].addcol = 'contact_date_last,contact_favourite_food'
        params.cols_update()
        params.outgroups[4].addcol = 'close_contact'
        params.cols_update()
        self.assertEqual(params.outgroups[4].names(), 
            ['contact_date_last', 'contact_favourite_food', 'close_contact'])

        # Field movement
        # Move up or down should have no effect at ends of list
        params.colop('up', 0, 0)
        params.colop('dn', 0, len(params.outgroups[0]) - 1)
        self.assertEqual(params.outgroups[0].labels(), common.expect_headings)
        # Test up/dn/del
        expect = list(common.expect_headings)
        expect[0], expect[1] = expect[1], expect[0]
        params.colop('up', 0, 1)
        self.assertEqual(params.outgroups[0].labels(), expect)
        expect[2], expect[3] = expect[3], expect[2]
        params.colop('dn', 0, 2)
        self.assertEqual(params.outgroups[0].labels(), expect)
        del expect[4]
        params.colop('del', 0, 4)
        self.assertEqual(params.outgroups[0].labels(), expect)
        # Test clear
        params.colop('clear', 0)
        self.assertEqual(len(params.outgroups[0]), 0)

