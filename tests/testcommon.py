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

import os, sys
import csv
import time
import random
import unittest

from cocklebur import dbobj
from casemgr.notification.client import dummy_notification_client


def freeze_time(t, fn, *a, **kw):
    import mx
    saved_now = mx.DateTime.now
    mx.DateTime.now = lambda : t
    try:
        return fn(*a, **kw)
    finally:
        mx.DateTime.now = saved_now


def randomDSN():
    name = ['unittest']
    for n in xrange(6):
        name.append(chr(random.randint(ord('a'), ord('z'))))
    return dbobj.DSN(database=''.join(name))

test_dsn = randomDSN()
destroy_db_atexit = True

def set_dsn(dsn):
    global test_dsn, destroy_db_atexit
    test_dsn = dbobj.DSN(dsn)
    destroy_db_atexit = False

if 'casemgr.globals' not in sys.modules:
    class DummyGlobals(object): 
        notify = dummy_notification_client()
        class Error(Exception): pass
    import casemgr
    sys.modules['casemgr.globals'] = casemgr.globals = DummyGlobals()


class DummyCredentials:

    def __init__(self, unit_id=1, user_id=1):
        class CredUnitUser:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        self.unit = CredUnitUser(unit_id=unit_id)
        self.user = CredUnitUser(user_id=user_id)
        self.rights = []


class DummySyndrome:

    def __init__(self):
        self.syndrome_id = 2


def load_table_from_csv(db, table, datadir, csvfile):
    """
    Load a table from a CSV file, with the first row of the CSV file
    naming the columns.
    """
    csvfile = os.path.join(datadir, csvfile + '.csv')
    reader = iter(csv.reader(open(csvfile)))
    # First row is column names
    cols = [name.strip() for name in reader.next()]
    for row in reader:
        dbrow = db.new_row(table)
        for col, value in zip(cols, row):
            setattr(dbrow, col, value)
        dbrow.db_update(refetch=False)

def _clean_db():
    from casemgr import globals
    if hasattr(globals, 'db'):
        print 'Destroying scratch db %s' % globals.db.dsn
        globals.db.rollback()
        globals.db.drop_database(globals.db)
        globals.db.close()
        del globals.db


def _connect_db():
    from casemgr import globals
    try:
        globals.db
    except AttributeError:
        import atexit
        if destroy_db_atexit:
            print 'Creating scratch db %s ...' % test_dsn,
        else:
            print 'Using db %s ...' % test_dsn,
        sys.stdout.flush()
        globals.db = dbobj.DatabaseDescriber(test_dsn)
        globals.db.create()
        if destroy_db_atexit:
            atexit.register(_clean_db)
        print 'done'
    return globals.db


class TestCase(unittest.TestCase):

    def assertListEq(self, a, b, msg=None):
        if a != b:
            import difflib
            a = [repr(aa) for aa in a]
            b = [repr(bb) for bb in b]
            diff = list(difflib.unified_diff(a, b, lineterm=''))
            diff = '\n'.join(diff[2:])
            if msg:
                diff = '%s\n%s' % (msg, diff)
            raise AssertionError(diff)

    def assertEqLines(self, a, b, msg=None):
        self.assertListEq(a.splitlines(), b.splitlines(), msg)


class DBTestCase(TestCase):

    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)
        self.module_path = os.path.dirname(__file__)
        self.data_path = os.path.join(self.module_path, 'data')
        self.table_path = os.path.join(self.data_path, 'tables')
        self.db = _connect_db()

    def tearDown(self):
        from casemgr import globals
        self.db.rollback()
        self.db.drop_all_tables(self.db)

    def new_table(self, tablename):
        return self.db.new_table(tablename)

    def load_table(self, tablename, filename=None):
        if filename is None:
            filename = tablename
        load_table_from_csv(self.db, tablename, self.table_path, filename)

    def psql(self):
        self.db.commit()
        os.system('psql %s' % self.db.dsn.database)
        #dbobj.execute_debug(1)


class SchemaTestCase(DBTestCase):

    """
    TestCase subclass for tests which need a database describer (schema)
    in place, but do not actually touch the database (typically those
    tests that only want to see what queries will be generated).
    """
    def setUp(self):
        from casemgr.schema import schema
        schema.define_db(test_dsn)

class AppTestCase(DBTestCase):

    """
    Test class for tests that need a more fully populated application
    schema. This takes a lot longer to set up, so we don't use it for the
    general case.
    """
    # Tables need to be loaded in a specific order
    load_tables = (
        'users', 'units',
        'forms',
        'syndrome_types', 'syndrome_forms',
        'persons', 'cases',
        'case_acl', 'case_form_summary',
        'tags', 'case_tags',
        'address_states', 'syndrome_case_assignments', 'syndrome_case_status',
    )
    # Tables not in this list are not created
    create_tables = load_tables + (
        'form_defs', 
        'report_params',
        'syndrome_demog_fields',
        'tasks',
        'workqueue_members',
        'workqueues',
    )

    def setUp(self):
        from casemgr.schema import schema
        from cocklebur import form_ui
        from casemgr import globals
        schema.define_db(test_dsn)
        # Delete any tables we don't intend to use - this considerably speeds
        # up the creation of the schema.
        for table_desc in self.db.get_tables():
            if table_desc.name not in self.create_tables:
                del self.db.table_describers[table_desc.name]
        self.db.make_database()
        self.db.commit()
        for table in self.load_tables:
            self.load_table(table)
        self.db.reset_sequences()
        self.formlib = globals.formlib =\
            form_ui.FormLibXMLDB(self.db, 'form_defs')
        table = self.make_form_table('sars_exposure')
        self.load_table(table, 'sars_exposure')
        table = self.make_form_table('hospital_admit')
        self.load_table(table, 'hospital_admit')
        self.db.commit()

    def make_form_table(self, formname):
        from cocklebur.form_ui.xmlload import xmlload
        from casemgr.formutils import deploy
        f = open(os.path.join(self.data_path, '%s.form' % formname))
        try:
            form = xmlload(f)
        finally:
            f.close()
        self.formlib.save(form, formname)
        deploy.make_form_table(self.db, form, form.table)
        return form.table
