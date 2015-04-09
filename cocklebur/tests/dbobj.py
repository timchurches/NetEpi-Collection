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
import sys
import unittest
from cocklebur.dbobj import *

test_db = 'test'
test_table = 'unittest'

# Enable/Disable debugging messages from the dbobj implementation under test.
sys.modules['cocklebur.dbobj'].debug = False

class Test(unittest.TestCase):
    def test_exprbuilder(self):
        ea = []
        e = ExprBuilder('and', ea)
        self.failIf(e)

        e.where('a = b')
        self.assertEqual(str(e), '(a = b)')

        e.where('c = %s', 'd')
        self.assertEqual(str(e), '(a = b and c = %s)')
        self.assertEqual(ea, ['d'])

        sub = e.sub_expr()
        sub.where('e = f')
        sub.where('g = %s', 'h')
        self.assertEqual(str(e), '(a = b and c = %s and (e = f or g = %s))')
        self.assertEqual(ea, ['d', 'h'])

        e.where('i = %s', 'j')
        self.assertEqual(str(e), 
                         '(a = b and c = %s and (e = f or g = %s) and i = %s)')
        self.assertEqual(ea, ['d', 'h', 'j'])

        ea = []
        e = ExprBuilder('and', ea)
        e.where('a = b')
        e.where('c = %s', 'd')
        sub = e.sub_expr()
        sub.where('e = f')
        sub.where('g = %s', 'h')
        subsub = sub.sub_expr()
        subsub.where('k = l')
        subsub.where('m = %s', 'n')
        e.where('i = %s', 'j')
        self.assertEqual(str(e), 
            '(a = b and c = %s and (e = f or g = %s or (k = l and m = %s)) and i = %s)')
        self.assertEqual(ea, ['d', 'h', 'n', 'j'])

    def test_connect(self):
        db = DatabaseDescriber(database=test_db)
        c = db.cursor()

    def test_register_table(self):
        db = DatabaseDescriber(database=test_db)
        try:
            td = db.new_table(test_table)
            td.column('name', StringColumn)
        finally:
            db.rollback()

    def test_make_table(self):
        db = DatabaseDescriber(database=test_db)
        try:
            td = db.new_table(test_table)
            td.column('name', StringColumn)
            db.make_table(test_table)
        finally:
            db.rollback()

    def test_make_table_serial(self):
        db = DatabaseDescriber(database=test_db)
        try:
            td = db.new_table(test_table)
            td.column('id', SerialColumn, primary_key=True)
            db.make_table(test_table)
        finally:
            db.rollback()

    def test_insert(self):
        db = DatabaseDescriber(database=test_db)
        try:
            td = db.new_table(test_table)
            td.column('id', SerialColumn, primary_key=True)
            td.column('name', StringColumn)
            td.column('age', IntColumn)
            td.column('temperature', FloatColumn)
            db.make_table(test_table)
            row = db.new_row(test_table)
            row.name = 'fred'
            row.age = 23
            row.temperature = 37.2
            row.db_update()
            row = db.query(test_table).where('name = %s', 'fred').fetchone()
            self.assertEqual(row.id, 1)
            self.assertEqual(row.name, 'fred')
            self.assertEqual(row.age, 23)
            self.assertEqual(row.temperature, 37.2)
        finally:
            db.rollback()

    def test_update(self):
        db = DatabaseDescriber(database=test_db)
        try:
            td = db.new_table(test_table)
            td.column('id', SerialColumn, primary_key=True)
            td.column('name', StringColumn)
            td.column('age', IntColumn)
            td.column('temperature', FloatColumn)
            db.make_table(test_table)
            row = db.new_row(test_table)
            row.name = 'fred'
            row.age = 23
            row.temperature = 37.2
            row.db_update()
            row = db.query(test_table).where('name = %s', 'fred').fetchone()
            self.assertEqual(row.id, 1)
            self.assertEqual(row.name, 'fred')
            self.assertEqual(row.age, 23)
            self.assertEqual(row.temperature, 37.2)
            row.name = 'sam'
            row.age = 24
            row.db_update()
            self.assertEqual(row.name, 'sam')
            rows = db.query(test_table).fetchall()
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row.name, 'sam')
            self.assertEqual(row.id, 1)
            self.assertEqual(row.age, 24)
            self.assertEqual(row.temperature, 37.2)
        finally:
            db.rollback()

    def test_delete(self):
        db = DatabaseDescriber(database=test_db)
        try:
            td = db.new_table(test_table)
            td.column('id', SerialColumn, primary_key=True)
            td.column('name', StringColumn)
            db.make_table(test_table)
            row = db.new_row(test_table)
            row.name = 'fred'
            row.db_update()
            row = db.query(test_table).where('name = %s', 'fred').fetchone()
            self.assertEqual(row.id, 1)
            self.assertEqual(row.name, 'fred')
            row.db_delete()
            row = db.query(test_table).where('name = %s', 'fred').fetchone()
            self.assertEqual(row, None)
        finally:
            db.rollback()

    def test_boolean(self):
        db = DatabaseDescriber(database=test_db)
        try:
            td = db.new_table(test_table)
            td.column('id', SerialColumn, primary_key=True)
            td.column('truth', BooleanColumn)
            td.column('dare', BooleanColumn)
            db.make_table(test_table)
            row = db.new_row(test_table)
            row.truth = 'True'
            row.dare = 1
            row.db_update()
            row = db.query(test_table).where('id = %s', 1).fetchone()
            self.assertEqual(row.id, 1)
            self.assertEqual(row.truth, 'True')
            self.assertEqual(row.dare, 'True')
            row.truth = None
            row.dare = 0
            row.db_update()
            rows = db.query(test_table).fetchall()
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row.id, 1)
            self.assertEqual(row.truth, '')
            self.assertEqual(row.dare, '')
        finally:
            db.rollback()

    def test_DateTime(self):
        db = DatabaseDescriber(database=test_db)
        try:
            td = db.new_table(test_table)
            td.column('id', SerialColumn, primary_key=True)
            td.column('birthday', DateColumn)
            td.column('lunchtime', TimeColumn)
            td.column('start_work', DatetimeColumn)
            db.make_table(test_table)
            row = db.new_row(test_table)
            row.birthday = '4/2/1998'
            row.lunchtime = '13:23'
            row.start_work = '3/1/2004 07:35'
            row.db_update()
            row = db.query(test_table).where('id = %s', 1).fetchone()
            self.assertEqual(row.id, 1)
            self.assertEqual(row.birthday, '04/02/1998')
            self.assertEqual(row.lunchtime, '13:23')
            self.assertEqual(row.start_work, '03/01/2004 07:35')
        finally:
            db.rollback()

    def test_rows(self):
        db = DatabaseDescriber(database=test_db)
        try:
            td = db.new_table(test_table)
            td.column('id', SerialColumn, primary_key=True)
            td.column('name', StringColumn)
            db.make_table(test_table)

            # Populate table
            row = db.new_row(test_table)
            row.name = 'fred'
            row.db_update()
            row = db.new_row(test_table)
            row.name = 'sam'
            row.db_update()

            # Query and compare result
            rows = db.query(test_table, order_by = 'id').fetchall()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].id, 1)
            self.assertEqual(rows[1].id, 2)
            self.assertEqual(rows[0].name, 'fred')
            self.assertEqual(rows[1].name, 'sam')

            # Update, query result
            rows[0].name = 'james'
            rows.db_update()
            rows = db.query(test_table, order_by = 'id').fetchall()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].id, 1)
            self.assertEqual(rows[0].name, 'james')

            # Delete a row, query result
            del rows[0]
            rows.db_update()
            rows = db.query(test_table, order_by = 'id').fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].id, 2)
        finally:
            db.rollback()

    def test_ref_column(self):
        db = DatabaseDescriber(database=test_db)
        try:
            # Create dependent tables
            foreign_table = 'other_test'
            td = db.new_table(foreign_table)
            td.column('label', StringColumn, primary_key = True)
            td.column('description', StringColumn)
            db.make_table(foreign_table)
            td = db.new_table(test_table)
            td.column('other', ReferenceColumn, references = foreign_table)
            db.make_table(test_table)

            # Populate
            label = 'foo'
            description = 'Foo you later, freak!'
            other_row = db.new_row(foreign_table)
            other_row.label = label
            other_row.description = description
            other_row.db_update()
            row = db.new_row(test_table)
            row.other = other_row.label
            row.db_update()

            # Query
            row = db.query(test_table).fetchone()
            self.assertEqual(row.get_ref('other').label, label)
            self.assertEqual(row.get_ref('other').description, description)
        finally:
            db.rollback()

class TestSuite(unittest.TestSuite):
    test_list = (
        'test_exprbuilder',
        'test_connect',
        'test_register_table',
        'test_make_table',
        'test_make_table_serial',
        'test_insert',
        'test_update',
        'test_delete',
        'test_boolean',
        'test_DateTime',
        'test_rows',
        'test_ref_column',
    )
    def __init__(self):
        unittest.TestSuite.__init__(self, map(Test, self.test_list))

def suite():
    return TestSuite()

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
