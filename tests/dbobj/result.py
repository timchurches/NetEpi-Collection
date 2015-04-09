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
from cPickle import dumps, loads
from cocklebur import dbobj, datetime
from mx.DateTime import DateTime

from tests import testcommon

class DummyCursor:
    description = [
        ('textcol',),
        ('intcol',),
        ('boolcol',),
        ('datecol',),
        ('lastupt',),
        ('id',),
        ('ignore',),
    ]
    oidValue = 999
    rowcount = 1

    def __init__(self, db):
        self.db = db

    def execute(self, cmd, args):
        if self.db.raise_exc:
            raise self.db.raise_exc
        if self.db.last_cmd is None:
            self.db.last_cmd = []
        self.db.last_cmd.append((cmd, tuple(args)))

    def fetchmany(self, count):
        count /= 2      # Just to keep the code on it's toes.
        try:
            return self.db.result[:count]
        finally:
            del self.db.result[:count]

    def close(self):
        pass

class DummyDB:
    def close(self):
        pass
    def rollback(self):
        pass
    def commit(self):
        pass

class DummyDescriber(dbobj.DatabaseDescriberCore):
    def __init__(self):
        dbobj.DatabaseDescriberCore.__init__(self, testcommon.test_dsn)
        self.reset()

    def _connect_db(self):
        self.db = DummyDB()

    def reset(self, raise_exc=None, result=[]):
        self.last_cmd = None
        self.raise_exc = raise_exc
        self.result = result

    def cursor(self):
        if not self.db:
            self._connect_db()
        return DummyCursor(self)

db = DummyDescriber()
td = db.new_table('testtable')
td.column('id', dbobj.SerialColumn, primary_key=True)
td.column('textcol', dbobj.StringColumn)
td.column('intcol', dbobj.IntColumn)
td.column('boolcol', dbobj.BooleanColumn, default='False')
td.column('datecol', dbobj.DatetimeColumn, default='CURRENT_TIMESTAMP')
td.column('lastupt', dbobj.LastUpdateColumn)
td.column('missing', dbobj.IntColumn)

table_name = '%s.%s' % (testcommon.test_dsn.database, 'testtable')


class Case(unittest.TestCase):
    def check_exec(self, expect):
        def cmdstr(cmd):
            if cmd is None:
                return 'None'
            cmd = ['%s args %s' % c for c in cmd]
            cmd.insert(0, '')
            return '\n    '.join(cmd)
        self.assertEqual(db.last_cmd, expect,
                         'Execute mismatch'
                         '\nExpected: %s'
                         '\nGot: %s' % 
                            (cmdstr(expect), cmdstr(db.last_cmd)))

    def test_null_result(self):
        db.reset(result=[])
        curs = db.cursor()
        rs = dbobj.ResultSet(td)
        rs.from_cursor(curs)
        self.assertEqual(list(rs), [])
        self.assertEqual(len(rs), 0)
        self.assertEqual(rs.table_desc(), td)

    def test_short_result(self):
        db.reset(result=[
            ('abc', -1, True, DateTime(2003,1,1), None, 0, 0),
            ('def', -2, False, DateTime(2005,2,2), None, 2, 0),
        ])
        curs = db.cursor()
        rs = dbobj.ResultSet(td)
        rs.from_cursor(curs)
        self.assertEqual(len(rs), 2)
        self.assertEqual(rs.db_has_changed(), False)
        rs.db_update()
        self.check_exec(None)
        self.assertEqual(rs[0].textcol, 'abc')
        self.assertEqual(rs[1].textcol, 'def')
        self.assertEqual(repr(rs[0]), 
            "<%s: id=0, textcol='abc', intcol=-1, boolcol=True, datecol=<cocklebur.datetime.mx_parse_datetime 01/01/2003 00:00:00>, lastupt=None, missing=None>" % table_name)
        self.assertEqual(rs[0].db_desc(), None)
        self.assertEqual(rs[0].is_new(), False)
        self.assertEqual(rs[0].db_has_changed(), False)
        # Make sure we can pickle and restore the set
        rs2 = loads(dumps(rs))
        self.assertEqual(rs[0].textcol, 'abc')
        self.assertEqual(rs[1].textcol, 'def')
        self.assertEqual(repr(rs[0]), 
            "<%s: id=0, textcol='abc', intcol=-1, boolcol=True, datecol=<cocklebur.datetime.mx_parse_datetime 01/01/2003 00:00:00>, lastupt=None, missing=None>" % table_name)

        # Refetch
        db.reset(result=[
            ('abc', -1, True, DateTime(2003,1,1), None, 0, 0),
        ])
        rs[0].db_refetch()
        self.check_exec([
            ('SELECT * FROM testtable WHERE id=%s', (0,)),
        ])

    def test_long_result(self):
        # We use fetchmany, so this tests our ability to repeatedly fetch
        db.reset(result=[
            ('abc', -1, True, DateTime(2003,1,1), None, 0, 0),
            ('def', -2, False, DateTime(2005,2,2), None, 2, 0),
            ('ghi', -4, False, DateTime(2002,3,4), None, 3, 0),
        ] * 99)
        curs = db.cursor()
        rs = dbobj.ResultSet(td)
        rs.from_cursor(curs)
        self.assertEqual(len(rs), 99 * 3)

    def get_rs(self):
        db.reset(result=[
            ('abc', -1, True, DateTime(2003,1,1), None, 0, 0),
            ('def', -2, False, DateTime(2005,2,2), None, 2, 0),
        ])
        rs = dbobj.ResultSet(td)
        rs.from_cursor(db.cursor())
        return rs

    def test_del(self):
        rs = self.get_rs()
        del rs[0]
        self.assertEqual(len(rs), 1)
        self.assertEqual(rs.db_has_changed(), True)
        self.assertEqual(repr(rs[0]), 
            "<%s: id=2, textcol='def', intcol=-2, boolcol=None, datecol=<cocklebur.datetime.mx_parse_datetime 02/02/2005 00:00:00>, lastupt=None, missing=None>" % table_name)
        rs.db_revert()
        self.assertEqual(rs.db_has_changed(), False)
        self.assertEqual(len(rs), 2)
        del rs[0]
        rs.db_update()
        self.check_exec([('DELETE FROM testtable WHERE id=%s', (0,))])

        # Check that a revert after update is a no-op
        rs.db_revert()
        self.assertEqual(len(rs), 1)

        # Check that deleting a row with dependancies raises an exception, and
        # reverses the delete 
        rs = self.get_rs()
        db.reset(raise_exc=dbobj.IntegrityError)
        del rs[0]
        self.assertRaises(dbobj.IntegrityError, rs.db_update)
        self.assertEqual(len(rs), 2)

#       Hmmm - slice does not work
#        rs = self.get_rs()
#        del rs[:]
#        self.assertEqual(len(rs), 0)
#        rs.db_update()
#        self.check_exec([
#            ('DELETE FROM testtable WHERE id=%s', (0,)),
#            ('DELETE FROM testtable WHERE id=%s', (2,)),
#        ])

    def test_pop(self):
        rs = self.get_rs()
        self.assertEqual(repr(rs.pop(0)), 
            "<%s: id=0, textcol='abc', intcol=-1, boolcol=True, datecol=<cocklebur.datetime.mx_parse_datetime 01/01/2003 00:00:00>, lastupt=None, missing=None>" % table_name)
        self.assertEqual(len(rs), 1)
        rs.db_update()
        self.check_exec([('DELETE FROM testtable WHERE id=%s', (0,))])

    def test_remove(self):
        rs = self.get_rs()
        rs.remove(rs[1])
        self.assertEqual(len(rs), 1)
        self.assertEqual(repr(rs[0]), 
            "<%s: id=0, textcol='abc', intcol=-1, boolcol=True, datecol=<cocklebur.datetime.mx_parse_datetime 01/01/2003 00:00:00>, lastupt=None, missing=None>" % table_name)
        rs.db_update()
        self.check_exec([('DELETE FROM testtable WHERE id=%s', (2,))])

    def test_update(self):
        rs = self.get_rs()
        # Check changed row behaviour
        rs[0].id = 3
        self.assertEqual(rs.db_has_changed(), True)
        self.assertEqual(repr(rs[0]), 
            "<%s: id=3, textcol='abc', intcol=-1, boolcol=True, datecol=<cocklebur.datetime.mx_parse_datetime 01/01/2003 00:00:00>, lastupt=None, missing=None>" % table_name)
        self.assertEqual(rs[0].db_desc(), 'testtable[id:0->3]')
        # Check .db_revert()
        rs.db_revert()
        self.assertEqual(rs.db_has_changed(), False)
        self.assertEqual(repr(rs[0]), 
            "<%s: id=0, textcol='abc', intcol=-1, boolcol=True, datecol=<cocklebur.datetime.mx_parse_datetime 01/01/2003 00:00:00>, lastupt=None, missing=None>" % table_name)
        # Check .db_update()
        now1 = DateTime(2009, 8, 11, 10, 0, 0)
        db.reset(result=[
            ('lmn', -1, False, DateTime(2003,1,1), now1, 3, 0),
        ])
        rs[0].id = 3
        rs[0].boolcol = ''
        testcommon.freeze_time(now1, rs.db_update)
        self.check_exec([
            ('UPDATE testtable SET id=%s, boolcol=%s, lastupt=%s WHERE id=%s', 
                (3, False, now1, 0)),
            ('SELECT * FROM testtable WHERE id=%s', (3,)),
        ])
        self.assertEqual(rs.db_has_changed(), False)
        self.assertEqual(rs[0].id, 3)
        self.assertEqual(rs[0].boolcol, '')
        self.assertEqual(rs[0].textcol, 'lmn')
        self.assertEqual(rs[0].lastupt, now1)
        # Check subsequent update
        now2 = DateTime(2009, 8, 11, 10, 1, 0)
        db.reset(result=[
            ('lmn', -1, True, DateTime(2003,1,1), now2, 4, 0),
        ])
        rs[0].id = 4
        testcommon.freeze_time(now2, rs.db_update)
        self.check_exec([
            ('UPDATE testtable SET id=%s, lastupt=%s WHERE id=%s', 
                (4, now2, 3)),
            ('SELECT * FROM testtable WHERE id=%s', (4,)),
        ])
        self.assertEqual(rs.db_has_changed(), False)
        self.assertEqual(rs[0].id, 4)
        self.assertEqual(rs[0].textcol, 'lmn')
        self.assertEqual(rs[0].lastupt, now2)
        # Check rollback() behaviour - for ResultRows, the effect is to
        # (mostly) undo the effects of the last db_update(), so a subsequent
        # db_update() will attempt to reapply any changes.
        db.rollback()
        self.assertEqual(rs.db_has_changed(), True)
        self.assertEqual(rs[0].id, 4)
        self.assertEqual(rs[0].lastupt, now1)

    def test_insert(self):
        rs = self.get_rs()
        # Make a new row
        row = rs.new_row()
        row.id = 4
        row.textcol = 'xyz'
        row.intcol = 99
        row.boolcol = 1
        self.assertEqual(rs.db_has_changed(), False)
        # Attach it to the rowset
        rs.append(row)
        self.assertEqual(row.is_new(), True)
        self.assertEqual(len(rs), 3)
        self.assertEqual(rs.db_has_changed(), True)
        # Check a revert detaches it
        rs.db_revert()
        self.assertEqual(len(rs), 2)
        self.assertEqual(rs.db_has_changed(), False)
        # Check that it gets committed
        rs.append(row)
        db.reset(result=[
            ('hij', 99, True, None, None, 4, 0),
        ])
        now = DateTime(2009, 8, 11, 10, 0, 0)
        testcommon.freeze_time(now, rs.db_update)
        self.assertEqual(row.is_new(), False)
        self.check_exec([
            ('INSERT INTO testtable (id,textcol,intcol,boolcol,lastupt) VALUES (%s,%s,%s,%s,%s)', (4, 'xyz', 99, dbobj.TRUE, now)),

            ('SELECT * FROM testtable WHERE oid=%s', (999,)),
        ])
        # Now see if the refetch worked
        self.assertEqual(row.id, 4)
        self.assertEqual(row.textcol, 'hij')
        self.assertEqual(row.intcol, 99)
        self.assertEqual(row.boolcol, 'True') # This is to make web apps happy
        self.assertEqual(row.datecol, None)
        # A subsequent rollback should set us back to the pre-update state
        db.rollback()
        self.assertEqual(row.id, 4)
        self.assertEqual(row.textcol, 'xyz')
        # And we should now be able to do another update, and a commit, and any
        # following rollbacks shouldn't touch us.
        db.reset(result=[
            ('hij', 99, False, None, None, 4, 0),
        ])
        rs.db_update()
        db.commit()
        db.rollback()
        self.assertEqual(row.textcol, 'hij')

class Suite(unittest.TestSuite):
    test_list = (
        'test_null_result',
        'test_short_result',
        'test_long_result',
        'test_del',
        'test_pop',
        'test_remove',
        'test_update',
        'test_insert',
    )
    def __init__(self):
        unittest.TestSuite.__init__(self, map(Case, self.test_list))

def suite():
    return Suite()

if __name__ == '__main__':
    unittest.main()
