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

# Test implicit PostgreSQL casts

from pyPgSQL import PgSQL
PgSQL.useUTCtimeValue = True            # Works around brokeness in some vers.
from mx import DateTime

def test(db, from_type, value, to_type, expect):
    curs = db.cursor()
    try:
        curs.execute('create table pgcasttest (a %s, b %s)' % 
                     (from_type, to_type))
        curs.execute('insert into pgcasttest (a) values (%s)', (value,))
        curs.execute('insert into pgcasttest (b) select a from pgcasttest');
        curs.execute('select b from pgcasttest where a is null');
        result = curs.fetchall()
        assert len(result) == 1, 'result %r' % result
        assert result[0][0] == expect, 'result %r' % result
    finally:
        curs.close()
        db.rollback()

db = PgSQL.connect(database='test')
test(db, 'varchar', 'a', 'text', 'a')
test(db, 'text', 'a', 'varchar', 'a')
test(db, 'float', 1.1, 'varchar', '1.1')
test(db, 'float', 1.1, 'text', '1.1')
#test(db, 'float', 1.1e99, 'varchar(1)', '1.1e99')
#test(db, 'text', '1.1', 'float', 1.1)
#test(db, 'bool', True, 'text', 'true')
#test(db, 'bool', True, 'int', 1)
test(db, 'float', 1.1, 'int', 1)
test(db, 'float', 1.5, 'int', 2)
test(db, 'int', 1, 'float', 1.0)
test(db, 'date', '2002-3-4', 'text', '2002-03-04')
test(db, 'date', '2002-3-4', 'varchar', '2002-03-04')
test(db, 'date', '2002-3-4', 'timestamp', DateTime.DateTime(2002,3,4))
test(db, 'timestamp', '2002-3-4 5:6:7', 'text', '2002-03-04 05:06:07')
test(db, 'timestamp', '2002-3-4 5:6:7', 'varchar', '2002-03-04 05:06:07')
test(db, 'timestamp', '2002-3-4 5:6:7', 'date', DateTime.DateTime(2002,3,4))
test(db, 'time', '5:6:7', 'text', '05:06:07')
test(db, 'time', '5:6:7', 'varchar', '05:06:07')
