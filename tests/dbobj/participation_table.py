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

from tests import testcommon

from cocklebur import dbobj
from cocklebur.dbobj.participation_table import ParticipationTable

class DatabaseDescriber(dbobj.DatabaseDescriberCore):
    oidValue = 999
    rowcount = 1

    def __init__(self):
        dbobj.DatabaseDescriberCore.__init__(self, testcommon.test_dsn)
        self.results = []

    def set_result(self, table, rows, expect=None, *expect_args):
        self.results.append((table, rows, expect, expect_args))

    def cursor(self):
        return self

    def execute(self, cmd, args):
#        print cmd, args
        try:
            table, self.rows, expect, expect_args = self.results.pop(0)
        except IndexError:
            expect, expect_args = '<nothing>', ()
        if expect is not None:
            try: cmd = cmd % tuple(args)
            except TypeError: pass
            try: expect = expect % tuple(expect_args)
            except TypeError: pass
            if cmd != expect:
                raise AssertionError('execute expected:\n    %s\ngot:\n    %s'% 
                                        (expect, cmd))
        self.description = []
        if table:
            for col in self.get_table(table).get_columns():
                self.description.append((col.name,))

    def fetchmany(self, n):
        result = self.rows[:n]
        del self.rows[:n]
        return result

class Case(unittest.TestCase):

    def pt_test(self):
        def rows_column(rows, col):
            return [getattr(row, col) for row in rows]
        db = DatabaseDescriber()

        # Set up table describers
        td = db.new_table('left_table')
        td.column('left_key', dbobj.SerialColumn, primary_key=True)

        td = db.new_table('right_table')
        td.column('right_key', dbobj.SerialColumn, primary_key=True)
        td.column('right_name', dbobj.StringColumn)

        td = db.new_table('pt_table')
        td.column('pt_key', dbobj.SerialColumn, primary_key=True)
        td.column('left', dbobj.ReferenceColumn, references='left_table')
        td.column('right', dbobj.ReferenceColumn, references='right_table')

        # Load participation table
        pt = ParticipationTable(td, 'left', 'right')
        db.set_result('pt_table', [[1, 1, 1], [2, 1, 2]],
                      'SELECT pt_table.* FROM pt_table'
                        ' WHERE (left IN (%s,%s)) ORDER BY pt_key', 1, 2)
        db.set_result('right_table', [[1, 'a'], [2, 'b']],
                      'SELECT right_table.* FROM right_table'
                       ' WHERE (right_key IN (%s,%s))', 1, 2)
        pt.preload([1, 2])

        # Check initial state
        self.assertEqual(pt.db_has_changed(), False)
        self.assertRaises(KeyError, pt.__getitem__, 0)
        self.assertEqual(len(pt[1]), 2)
        self.assertEqual(pt[1].slave_keys(), [1, 2])
        self.assertEqual(rows_column(pt[1], 'right_key'), [1, 2])
        self.assertEqual(rows_column(pt[1], 'right_name'), ['a', 'b'])
        self.assertEqual(len(pt[2]), 0)
        self.assertEqual(list(pt[2]), [])

        # Revert should do nothing at this stage
        pt[1].db_revert()
        self.assertEqual(pt.db_has_changed(), False)
        self.assertEqual(pt[1].slave_keys(), [1, 2])
        self.assertEqual(rows_column(pt[1], 'right_key'), [1, 2])
        self.assertEqual(rows_column(pt[1], 'right_name'), ['a', 'b'])

        # Moving the first item up or the last item down should be NOOP
        pt[1].move_up(0)
        self.assertEqual(pt.db_has_changed(), False)
        self.assertEqual(pt[1].slave_keys(), [1, 2])
        pt[1].move_down(1)
        self.assertEqual(pt.db_has_changed(), False)
        self.assertEqual(pt[1].slave_keys(), [1, 2])

        # Test move up
        pt[1].move_up(1)
        self.assertEqual(pt.db_has_changed(), True)
        self.assertEqual(pt[1].slave_keys(), [2, 1])
        self.assertEqual(rows_column(pt[1], 'right_key'), [2, 1])
        self.assertEqual(rows_column(pt[1], 'right_name'), ['b', 'a'])

        # Test move down
        pt[1].move_down(0)
        self.assertEqual(pt.db_has_changed(), False)
        self.assertEqual(pt[1].slave_keys(), [1, 2])
        self.assertEqual(rows_column(pt[1], 'right_key'), [1, 2])
        self.assertEqual(rows_column(pt[1], 'right_name'), ['a', 'b'])

        # Test pop (delete)
        a = pt[1].pop(0)
        self.assertEqual(pt.db_has_changed(), True)
        self.assertEqual(pt[1].slave_keys(), [2])
        self.assertEqual(rows_column(pt[1], 'right_key'), [2])
        self.assertEqual(rows_column(pt[1], 'right_name'), ['b'])

        b = pt[1].pop(0)
        self.assertEqual(pt.db_has_changed(), True)
        self.assertEqual(pt[1].slave_keys(), [])
        self.assertEqual(rows_column(pt[1], 'right_key'), [])
        self.assertEqual(rows_column(pt[1], 'right_name'), [])

        pt[1].add(a)
        pt[1].add(b)
        self.assertEqual(pt.db_has_changed(), True)     # XXX
        self.assertEqual(pt[1].slave_keys(), [1, 2])
        self.assertEqual(rows_column(pt[1], 'right_key'), [1, 2])
        self.assertEqual(rows_column(pt[1], 'right_name'), ['a', 'b'])

        # Test revert after deletes and adds
        pt.db_revert()
        self.assertEqual(pt.db_has_changed(), False)
        self.assertEqual(pt[1].slave_keys(), [1, 2])
        self.assertEqual(rows_column(pt[1], 'right_key'), [1, 2])
        self.assertEqual(rows_column(pt[1], 'right_name'), ['a', 'b'])

        # Add a new row
        row = db.new_row('right_table')
        row.right_key = 3
        row.right_name = 'c'
        self.assertEqual(row in pt[1], False)
        pt[1].add(row)
        self.assertEqual(row in pt[1], True)
        self.assertEqual(pt.db_has_changed(), True)
        self.assertEqual(pt[1].slave_keys(), [1, 2, 3])
        self.assertEqual(rows_column(pt[1], 'right_key'), [1, 2, 3])
        self.assertEqual(rows_column(pt[1], 'right_name'), ['a', 'b', 'c'])
        db.set_result(None, [],
                      'INSERT INTO pt_table (left,right) VALUES (%s,%s)', 1, 3)
        db.set_result('pt_table', [[3, 1, 3]],
                      'SELECT * FROM pt_table WHERE oid=%s', 999)
        pt.db_update()
        self.assertEqual(pt.db_has_changed(), False)

        # Revert now should have no effect
        pt.db_revert()
        self.assertEqual(pt[1].slave_keys(), [1, 2, 3])

        # Test pop with commit
        pt[1].pop(0)
        db.set_result(None, [],
                      'DELETE FROM pt_table WHERE pt_key=%s', 1)
        pt.db_update()
        self.assertEqual(pt.db_has_changed(), False)

        # Move with commit
        pt[1].move_up(1)
        self.assertEqual(pt.db_has_changed(), True)
        self.assertEqual(pt[1].slave_keys(), [3, 2])
        self.assertEqual(rows_column(pt[1], 'right_key'), [3, 2])
        self.assertEqual(rows_column(pt[1], 'right_name'), ['c', 'b'])
        db.set_result(None, [],
                      'UPDATE pt_table SET right=%s WHERE pt_key=%s', 3, 2)
        db.set_result('pt_table', [[2, 1, 3]],
                      'SELECT * FROM pt_table WHERE pt_key=%s', 2)
        db.set_result(None, [],
                      'UPDATE pt_table SET right=%s WHERE pt_key=%s', 2, 3)
        db.set_result('pt_table', [[3, 1, 2]],
                      'SELECT * FROM pt_table WHERE pt_key=%s', 3)
        pt.db_update()
        self.assertEqual(pt.db_has_changed(), False)
        self.assertEqual(rows_column(pt[1], 'right_key'), [3, 2])
        self.assertEqual(rows_column(pt[1], 'right_name'), ['c', 'b'])

        # Add row, move, commit
        row = db.new_row('right_table')
        row.right_key = 4
        row.right_name = 'd'
        self.assertEqual(row in pt[1], False)
        pt[1].add(row)
        self.assertEqual(pt.db_has_changed(), True)
        self.assertEqual(pt[1].slave_keys(), [3, 2, 4])
        pt[1].move_up(2)
        self.assertEqual(pt[1].slave_keys(), [3, 4, 2])
        db.set_result(None, [],
                      'UPDATE pt_table SET right=%s WHERE pt_key=%s', 4, 3)
        db.set_result('pt_table', [[3, 1, 4]],
                      'SELECT * FROM pt_table WHERE pt_key=%s', 3)
        db.set_result(None, [],
                      'INSERT INTO pt_table (left,right) VALUES (%s,%s)', 1, 2)
        db.set_result('pt_table', [[4, 1, 2]],
                      'SELECT * FROM pt_table WHERE oid=%s', 999)
        pt.db_update()
        self.assertEqual(pt.db_has_changed(), False)
        self.assertEqual(rows_column(pt[1], 'right_key'), [3, 4, 2])
        self.assertEqual(rows_column(pt[1], 'right_name'), ['c', 'd', 'b'])


class Suite(unittest.TestSuite):
    test_list = (
        'pt_test',
    )
    def __init__(self):
        unittest.TestSuite.__init__(self, map(Case, self.test_list))

def suite():
    return Suite()

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
