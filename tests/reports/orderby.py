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

expect_ordercols = [
    ('interpreter_req', 'Interpreter'),
    ('case_status', 'Status'),
    ('local_case_id', 'Local ID'),
    ('case_assignment', 'Case Assignment'),
    ('case_id', 'System ID'),
    ('surname', 'Surname'),
    ('given_names', 'Given names'),
    ('DOB', 'Date of birth/Age'),
    ('sex', 'Sex'),
    ('home_phone', 'Home phone'),
    ('mobile_phone', 'Mobile phone'),
    ('fax_phone', 'Fax'),
    ('street_address', 'Street address'),
    ('locality', 'Locality/Suburb'),
    ('state', 'State'),
    ('postcode', 'Postcode'),
    ('work_phone', 'Work/School phone'),
    ('passport_number', 'Passport number'),
    ('passport_country', 'Passport country/Nationality'),
    ('notification_datetime', 'Notification Date'),
    ('onset_datetime', 'Onset Date'),
    ('tags', 'Tags'),
    ('deleted', 'Deleted'),
    ('delete_reason', 'Deletion reason'),
    ('delete_timestamp', 'Deletion date'),
]

class ReportOrderbyTests(testcommon.AppTestCase):

    def test_order(self):
        """
        order by column parameter handling
        """
        params = reports.new_report(2, 'line')
        self.assertEqual(len(params.order_by), 0)
        self.assertEqual(params.query_order(), '')
        params.add_order()
        params.order_by[0].col = 'onset_datetime'
        params.order_by[0].rev = 'desc'
        params.add_order()
        params.order_by[1].col = 'surname'
        self.assertEqual(params.query_order(), 
                         'onset_datetime desc,surname asc')
        params.del_order(0)
        self.assertEqual(params.query_order(), 'surname asc')
        self.assertEqual(params.order_cols(), expect_ordercols)
