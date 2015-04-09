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
#   Copyright (C) 2004-2011 Health Administration Corporation and others. 
#   All Rights Reserved.
#
#   Contributors: See the CONTRIBUTORS file for details of contributions.
#

"""
Paper over the differences between DB-API2 implementations
"""

from time import time

import config

# What database prefers for boolean columns
TRUE = True
FALSE = False

connect_extra = {}
try:
    from ocpgdb import *
    connect_extra = dict(use_mx_datetime=True)
except ImportError:
    from pyPgSQL import PgSQL
    PgSQL.useUTCtimeValue = True       # Works around brokeness in some vers
    PgSQL.fetchReturnsList = True      # faster, and duplicates dbobj work
    from pyPgSQL.PgSQL import *
    Binary = PgBytea
    # pyPgSQL predates python True and False
    TRUE = PG_True
    FALSE = PG_False

# Some fine-grained exceptions. Not part of the API, but this is a convenient
# place to define them.
class IdentifierError(DatabaseError): pass
class ValidationError(DatabaseError): pass
class DuplicateKeyError(OperationalError): pass
class ConstraintError(OperationalError): pass
class TooManyRecords(OperationalError): pass
class RecordDeleted(OperationalError): pass

debug = False

def execute_debug(value):
    global debug
    debug = value

debug_prefix = '+'

def execute(curs, cmd, *args):
    def pretty_cmd(cmd, args):
        if len(args) == 1 and type(args[0]) in (tuple, list):
            args = args[0]
        cleanargs = []
        for arg in args:
            arg = str(arg)
            if len(arg) > 30:
                arg = arg[:15] + '...' + arg[-10:]
            cleanargs.append(arg)
        cmdargs = cmd % tuple(cleanargs)
        return debug_prefix + cmdargs.replace('\n', '\n' + debug_prefix)

    if ';' in cmd:      # Crude security hack
        raise ProgrammingError('Only one command per execute() allowed')
    if debug:
        st = time()
    try:
        res = curs.execute(cmd, *args)
    except Error, e:
        exc_type, exc_value, exc_tb = sys.exc_info()
        if 'duplicate key' in str(exc_value):
            exc_type = DuplicateKeyError
        elif 'violates foreign key constraint' in str(exc_value):
            exc_type = ConstraintError
#        sys.stderr.write('dbapi.error: %s: %s\n' % (e, pretty_cmd(cmd, args)))
        try:
            raise exc_type, '%s%s' % (exc_value, pretty_cmd(cmd, args)), exc_tb
        finally:
            del exc_type, exc_value, exc_tb
    except Exception:
        sys.stderr.write('Exception SQL: %s\n' % pretty_cmd(cmd, args))
        raise
    else:
        if debug: 
            sys.stderr.write(pretty_cmd(cmd, args) + 
                                ' (%.3f secs)\n' % (time() - st))
        return res

class O(object): pass


class Cursor:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, cmd, *args):
        execute(self.cursor, cmd, *args)
        self.cols = None
        if self.cursor.description:
            self.cols = [d[0] for d in self.cursor.description]

    def row_obj(self, row):
        o = O()
        for col, value in zip(self.cols, row):
            setattr(o, col, value)
        return o

    def yield_obj(self):
        for row in self.cursor.fetchmany(200):
            yield self.row_obj(row)

    def one_obj(self):
        row = self.cursor.fetchone()
        if row is not None:
            return self.row_obj(row)

    def close(self):
        self.cursor.close()


class DB:
    def __init__(self):
        dsn = 'host:port:database:user'
        args = dict(connect_extra)
        for name, value in zip(dsn.split(':'), config.dsn.split(':')):
            if value:
                args[name] = value
        self.db = connect(**args)

    def commit(self):
        if debug:
            sys.stderr.write(debug_prefix + 'COMMIT\n')
        self.db.commit()

    def rollback(self):
        if debug:
            sys.stderr.write(debug_prefix + 'ROLLBACK\n')
        self.db.rollback()

    def close(self):
        if debug:
            sys.stderr.write(debug_prefix + 'CLOSE\n')
        self.db.close()

    def cursor(self):
        return self.db.cursor()

db = DB()
