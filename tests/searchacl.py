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

import unittest

from cocklebur import dbobj

import testcommon

from casemgr import caseaccess

#dbobj.execute_debug(1)


class Cred:

    def __init__(self, unit_id):
        class _Unit:
            def __init__(self, unit_id):
                self.unit_id = unit_id
        class _User:
            def __init__(self, user_id):
                self.user_id = user_id
        if unit_id:
            self.unit = _Unit(unit_id)
            self.rights = ()
        else:
            self.rights = ('ACCESSALL',)
        self.user = _User(0)


class Case(testcommon.DBTestCase):

    def setUp(self):
        td = self.new_table('cases')
        td.column('case_id', dbobj.SerialColumn, primary_key=True)
        td.column('syndrome_id', dbobj.IntColumn)
        td.column('deleted', dbobj.BooleanColumn)
        td.create()

        td = self.new_table('case_acl')
        td.column('case_id', dbobj.ReferenceColumn, references = 'cases')
        td.column('unit_id', dbobj.IntColumn)
        td.create()

        td = self.new_table('workqueues')
        td.column('queue_id', dbobj.SerialColumn, primary_key=True)
        td.column('unit_id', dbobj.IntColumn)
        td.column('user_id', dbobj.IntColumn)
        td.create()

        td = self.new_table('workqueue_members')
        td.column('queue_id', dbobj.ReferenceColumn, references = 'workqueues')
        td.column('unit_id', dbobj.IntColumn)
        td.column('user_id', dbobj.IntColumn)
        td.create()

        td = self.new_table('tasks')
        td.column('task_id', dbobj.SerialColumn, primary_key=True)
        td.column('case_id', dbobj.ReferenceColumn, references = 'cases')
        td.column('queue_id', dbobj.ReferenceColumn, references = 'workqueues')
        td.create()

        curs = self.db.cursor()
        # Case 1, syndrome 1, unit 1 & 3
        dbobj.execute(curs, 'INSERT INTO cases VALUES (1, 1, false)')
        dbobj.execute(curs, 'INSERT INTO case_acl VALUES (1, 1)')
        dbobj.execute(curs, 'INSERT INTO case_acl VALUES (1, 3)')
        self.db.commit()

        # Case 4, syndrome 1, no unit
        dbobj.execute(curs, 'INSERT INTO cases VALUES (4, 1, false)')

        # Case 5, syndrome 2, unit 1
        dbobj.execute(curs, 'INSERT INTO cases VALUES (5, 2, false)')
        dbobj.execute(curs, 'INSERT INTO case_acl VALUES (5, 1)')

    # XXX Need to test access via tasks
    def runTest(self):
        def _test(cred, expect):
            query = self.db.query('cases')
            caseaccess.acl_query(query, cred)
            self.assertEqual(query.fetchcols('case_id'), expect)

        _test(Cred(None), [1, 4, 5])
        _test(Cred(1),    [1, 5])
        _test(Cred(2),    [])


class Suite(unittest.TestSuite):
    test_list = (
        'runTest',
    )
    def __init__(self):
        unittest.TestSuite.__init__(self, map(Case, self.test_list))

def suite():
    return Suite()

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

