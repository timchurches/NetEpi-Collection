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
import os
import sys
import time
import cPickle
import weakref
try:
    set
except NameError:
    from sets import Set as set

from cocklebur.dbobj import dbapi, query_builder, table_describer, result, \
                            table_dict, participation_table, misc
from cocklebur.dbobj.execute import execute, commit, rollback

def order_by_dependancies(objs, debug = 0):
    """ Order some collection of objects to satisfy dependancies """
    needs = dict([(obj.name, (obj, obj.dependancies())) for obj in objs])
    in_order = []
    while needs:
        did_work = False
        if debug:
            print 'needs: ', ','.join(['%s(%s)' % (name, ','.join(deps)) 
                                       for name, (obj, deps) in needs.items()])
        for name in needs.keys():
            obj, depends = needs[name]  # Don't use .items() as we update
            if not depends:
                if debug: print "resolved:", name
                did_work = True
                in_order.append(obj)
                del needs[name]
                for obj, dependancies in needs.values():
                    dependancies.discard(name)
        if debug: print 'inorder: ', ','.join([obj.name for obj in in_order])
        if not did_work:
            errs = ["%s: %s" % (name, ','.join(depends))
                    for name, (obj, depends) in needs.items()]
            raise ValueError("Couldn't resolve dependancies for: " +
                                  ', '.join(errs))
    return in_order

class DSN(str):
    """
    A string-like class for DSN's (Data Source Name)

    host, port, dbname and user are accessable as R/O attributes -
    other elements of the DSN (password) are not recorded.

    Instances are intended to be trivialably hashable and small, 
    hence subclass of str.
    """

#    __slots__ = ()
    _index = {'host': 0, 'port': 1, 'database': 2, 'user': 3}

    def __new__(cls, dsn = '', **kwargs):
        params = dsn.split(':')[:4]
        params.extend([''] * (4 - len(params)))
        if kwargs:
            for name, index in cls._index.items():
                params[index] = str(kwargs.get(name, params[index]))
        return str.__new__(cls, ':'.join(params))

    def __getattr__(self, name):
        try:
            index = self._index[name]
        except KeyError:
            raise AttributeError('DSN object has no attribute %r' % name)
        return self.split(':')[index]

    def get_kw(self):
        kw = {}
        params = self.split(':')
        for name, index in self._index.items():
            param = params[index]
            if param:
                kw[name] = param
        return kw

    def connect(self):
        connect_args = self.get_kw()
        connect_args.update(dbapi.connect_extra)
        return dbapi.connect(**connect_args)


def template_exec(dsn, cmd):
    """
    Connect to the template1 database, retrying if necessary
    """
    template_dsn = DSN(dsn, database='template1')
    db = template_dsn.connect()
    try:
        db.autocommit = True
        curs = db.cursor()
        n = 0
        while 1:
            try:
                execute(curs, cmd)
                break
            except dbapi.DatabaseError, e:
                if n < 3 and 'is being accessed by other users' in str(e):
                    n += 1
                    time.sleep(1)
                    continue
                else:
                    raise
    finally:
        db.close()


class DatabaseDescriberCore:
    """
    Describe a database

    Instances of this class contain the DSN of the database,
    as well as a description of the tables and associated
    indexes and sequences. The class otherwise behaves as a
    partial proxy to the DB-API 2.0 "db" object - specifically,
    the cursor(), commit(), rollback() and close() methods.
    """

    def __init__(self, dsn = '', **kwargs):
        if not isinstance(dsn, DSN):
            dsn = DSN(dsn, **kwargs)
        self.dsn = dsn
        self.db = None
        self.updated = True
        self.filename = str(self.dsn)
        self.mtime = 0
        self.clear_pending()
        self._invalidate_sys_info()
        self.table_describers = {}

    def _invalidate_sys_info(self):
        self.__sys_relations = None

    def _get_sys_info(self):
        curs = self.cursor()
        curs.execute('select relname from pg_class')
        self.__sys_relations = dict([(r[0].lower(), True) 
                                     for r in curs.fetchall()])

    def load_describer(self, path = ''):
        if path:
            self.filename = os.path.join(path, str(self.dsn))
        f = open(self.filename, 'rb')
        st = os.fstat(f.fileno())
        try:
            if st.st_mtime > self.mtime:
                self.mtime = st.st_mtime
                self._invalidate_sys_info()
                self.table_describers, = cPickle.load(f)
                for table_desc in self.table_describers.values():
                    table_desc.db = self
                self.updated = False
        finally:
            f.close()

    def save_describer(self, path = '', owner = None, mode = None):
        if path:
            self.filename = os.path.join(path, str(self.dsn))
        if self.updated:
            import tempfile

            fd, tmpname = tempfile.mkstemp(dir = os.path.dirname(self.filename))
            f = os.fdopen(fd, 'wb')
            try:
                # Break cycles prior to pickling
                for table_desc in self.table_describers.values():
                    table_desc.db = None
                try:
                    cPickle.dump((self.table_describers,), f, -1)
                finally:
                    for table_desc in self.table_describers.values():
                        table_desc.db = self
                self.mtime = os.fstat(f.fileno()).st_mtime
                f.close()
                if mode is None:
                    mode = 0644
                # We really want fchmod/fchown here for safety
                os.chmod(tmpname, mode)
                if owner is not None:
                    os.chown(tmpname, *owner)
                os.rename(tmpname, self.filename)
                self.updated = False
            finally:
                try:
                    os.unlink(tmpname)
                except OSError:
                    pass

    def new_table(self, name, **kwargs):
        name = name.lower()
        table_desc = table_describer.TableDescriber(self, name, **kwargs)
        self.table_describers[name] = table_desc
        self.updated = True
        return table_desc

    def rename_table(self, old_name, new_name):
        old_name = old_name.lower()
        new_name = new_name.lower()
        table_desc = self.get_table(old_name)
        table_desc.rename(new_name)
        del self.table_describers[old_name]
        self.table_describers[new_name] = table_desc
        self.updated = True
        return table_desc
        
    def get_table(self, name):
        try:
            return self.table_describers[name.lower()]
        except KeyError:
            raise KeyError('unknown table describer "%s"' % name)

    def has_table(self, name):
        return name in self.table_describers

    def get_tables(self):
        return self.table_describers.values()

    def query(self, table, **kwargs):
        return query_builder.Query(self.get_table(table), **kwargs)

    def table_dict(self, table, key_col = None):
        return table_dict.TableDict(self.get_table(table), key_col)

    def participation_table(self, table, master_col, slave_col):
        return participation_table.ParticipationTable(self.get_table(table),
                                                      master_col, slave_col)

    def ptset(self, table, master_col, slave_col, key=None, filter=None):
        return participation_table.ptset(self.get_table(table),
                                         master_col, slave_col, key, filter)

    def new_row(self, table, **seed_values):
        return self.get_table(table).get_row(seed_values=seed_values)

    def nextval(self, table, colname):
        "Return the next value associated with a SERIAL column"
        return self.get_table(table).nextval(colname)

    def empty_result_set(self, table):
        return result.ResultSet(self.get_table(table))

    def make_table(self, table, **kw):
        self.get_table(table).create(**kw)

    def drop_table(self, table):
        self.get_table(table).drop()
        del self.table_describers[table]
        self.updated = True

    def make_user(self, username):
        curs = self.cursor()
        try:
            execute(curs, 'SELECT usename FROM pg_user'
                            ' WHERE usename=%s', (username,))
            if not curs.fetchone():
                execute(curs, 'CREATE USER "%s"' % username)
                self.commit()
        finally:
            curs.close()

    def create(self, owner=None, grant=None):
        # Attempt to connect to the database, create it if it doesn't exist
        try:
            self._connect_db()
        except dbapi.DatabaseError, e:
            if 'does not exist' not in str(e):
                raise
            misc.valid_identifier(self.dsn.database, 'database name', 
                                  strict=False)
            template_exec(self.dsn, 'CREATE DATABASE %s' % self.dsn.database)
        if grant:
            self.make_user(grant)
        if owner:
            self.make_user(owner)

    def make_database(self, owner=None, grant=None):
        self.create(owner, grant)
        # Reconnect to the (potentially newly created) database and create
        # missing tables
        table_descs = order_by_dependancies(self.table_describers.values())
        for table_desc in table_descs:
            table_desc.create(grant=grant, owner=owner)
        self.commit()                    # Can't rollback CREATE DB anyway

    def chown(self, owner):
        curs = self.cursor()
        try:
            for table_desc in self.table_describers.values():
                table_desc.owner(curs, owner)
        finally:
            curs.close()

    def drop_all_tables(self, db):
        """
        Drops all the tables we know about. At this time, this method
        is only used by the unittests to restore the schema to a known
        state prior to running the next test.
        """
        assert self is db               # Paranoia
        table_descs = order_by_dependancies(self.table_describers.values())
        for table_desc in table_descs[::-1]:
            table_desc.drop()
        self.commit()
        self._invalidate_sys_info()

    def reset_sequences(self):
        """
	Scans all sequences, resetting them to the highest value
	appearing in the associated table.
        """
        curs = self.db.cursor()
        try:
            for table_desc in self.table_describers.values():
                table_desc.reset_sequences(curs)
        finally:
            curs.close()

    def drop_database(self, db):
        assert self is db               # Paranoia
        self.unload()
        try:
            template_exec(self.dsn, 'DROP DATABASE %s' % self.dsn.database)
        except dbapi.DatabaseError, e:
            if 'does not exist' not in str(e):
                raise

    def db_has_relation(self, name):
        if self.__sys_relations is None:
            self._get_sys_info()
        return self.__sys_relations.get(name.lower())

    # Proxy to Database API connection objects
    def _connect_db(self):
        self.db = self.dsn.connect()
        curs = self.db.cursor()
        try:
            execute(curs, "SET datestyle TO 'ISO,European'")
# May potentially open us up to an SQL injection attack:
# http://www.postgresql.org/docs/techdocs.50
#            execute(curs, "SET client_encoding TO unicode")
            execute(curs, "SET client_encoding TO SQL_ASCII")
        finally:
            curs.close()

    def clear_pending(self):
        self.pending = set()

    def add_pending(self, row):
        self.pending.add(weakref.ref(row))

    def del_pending(self, row):
        self.pending.discard(weakref.ref(row))

    def commit(self):
        self._invalidate_sys_info()
        if self.db is not None:
            commit(self.db)
            for ref in list(self.pending):
                row = ref()
                if row:
                    row.db_commit()
            self.clear_pending()

    def rollback(self):
        if self.db is not None:
            rollback(self.db)
            for ref in list(self.pending):
                row = ref()
                if row:
                    row.db_rollback()
            self.clear_pending()

    def cursor(self):
        if self.db is None:
            self._connect_db()
            return self.db.cursor()
        try:
            return self.db.cursor()
        except dbapi.OperationalError, e:
            print >> sys.stderr, 'RETRYING - %s' % e
            self.close()
            self._connect_db()
            return self.db.cursor()

    def close(self):
        if self.db is not None:
            self.clear_pending()
            self.db.close()
            self.db = None
#            import traceback
#            traceback.print_stack()

    def unload(self):
        if self.db is not None:
            self.close()

    def lock_table(self, table, mode, wait=True):
        cmd = 'LOCK %s IN %s MODE' % (table, mode)
        if not wait:
            cmd += ' NOWAIT'
        curs = self.cursor()
        try:
            execute(curs, cmd)
        finally:
            curs.close()


class DatabaseDescriber(DatabaseDescriberCore):
    """
    We want pickles of this class to contain just a text representation
    of the DSN, not the table describers and other support structures
    (which are quite large), so that it can be saved to a browser hidden
    field. The table describers are loaded from the local filesystem prior
    to unpickling - the unpickled instance will refer to the previously
    loaded instance.

    We use a Borg pattern keyed by DSN to ensure there is
    only one connection to a database per DSN, and one set of
    table describers.

    """
    instances = {}

    def __init__(self, dsn = '', **kwargs):
        if not isinstance(dsn, DSN):
            dsn = DSN(dsn, **kwargs)
        try:
            self._borg(dsn)
        except KeyError:
            DatabaseDescriber.instances[dsn] = self.__dict__
            DatabaseDescriberCore.__init__(self, dsn)
            self._invalidate_sys_info()

    def _borg(self, dsn):
        self.__dict__ = DatabaseDescriber.instances[dsn]

    def __getstate__(self):
        return self.dsn,

    def __setstate__(self, state):
        dsn, = state
        self._borg(dsn)

    def unload(self):
        DatabaseDescriberCore.unload(self)
        try:
            del DatabaseDescriber.instances[self.dsn]
        except KeyError:
            pass


def get_db(path, dsn):
    db = DatabaseDescriber(dsn)
    db.load_describer(path)
    return db
