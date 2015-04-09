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
from time import time
from cocklebur.dbobj import dbapi

debug = False
timing = False

def execute_debug(value):
    global debug
    #if value:
    #    import traceback
    #    traceback.print_stack()
    debug = value

def execute_timing(value):
    global timing, exec_timing
    timing = value
    if value:
        from exec_timing import exec_timing

prefix = '+'

def execute(curs, cmd, args=()):
    def pretty_cmd(cmd, args):
        cleanargs = []
        for arg in args:
            if hasattr(arg, 'strftime'):
                arg = str(arg)
            else:
                arg = repr(arg)
            if len(arg) > 30:
                arg = arg[:15] + '...' + arg[-10:]
            cleanargs.append(arg)
        if cleanargs:
            cmdargs = cmd % tuple(cleanargs)
        else:
            cmdargs = cmd
        return prefix + cmdargs.replace('\n', '\n' + prefix)

    if ';' in cmd:      # Crude security hack
        raise dbapi.ProgrammingError('Only one command per execute() allowed')
    if debug or timing:
        st = time()
    try:
        res = curs.execute(cmd, args)
    except dbapi.Error, e:
        exc_type, exc_value, exc_tb = sys.exc_info()
        if 'duplicate key' in str(exc_value):
            exc_type = dbapi.DuplicateKeyError
        elif 'violates foreign key constraint' in str(exc_value):
            exc_type = dbapi.ConstraintError
#        sys.stderr.write('dbapi.error: %s: %s\n' % (e, pretty_cmd(cmd, args)))
        try:
            raise exc_type, '%s%s' % (exc_value, pretty_cmd(cmd, args)), exc_tb
        finally:
            del exc_type, exc_value, exc_tb
    except Exception:
        sys.stderr.write('Exception SQL: %s\n' % pretty_cmd(cmd, args))
        raise
    else:
        if debug or timing:
            el = time() - st
        if debug: 
            sys.stderr.write(pretty_cmd(cmd, args) + (' (%.3f secs)\n' % el))
        if timing:
            exec_timing.record(cmd, el)
        return res

def commit(db):
    if debug:
        sys.stderr.write(prefix + 'COMMIT\n')
    db.commit()

def rollback(db):
    if debug:
        sys.stderr.write(prefix + 'ROLLBACK\n')
    db.rollback()
