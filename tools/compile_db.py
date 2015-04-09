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

# HISTORICAL NOTE:
#
# This script is now somewhat of a misnomer: initially form definitions were
# python code, and we compiled these into python bytecode (.pyc files). Over
# time, the script gained the ability to create the database schema, and
# sometime after that, forms moved to an XML format stored in the database, so
# there's no compiling going on anymore, just the database creation, schema
# upgrades and some consistency checks.

import sys, os, imp, traceback, re
try:
    set
except NameError:
    from sets import Set as set

verbose = False
debug = False

def get_ugid(user):
    import pwd
    pw = pwd.getpwnam(user)
    return pw.pw_uid, pw.pw_gid

def make_dirs(dir, owner):
    if not os.path.exists(dir):
        par_dir = os.path.dirname(dir)
        make_dirs(par_dir, owner)
        os.mkdir(dir, 0755)
        os.chown(dir, *owner)


def compile_db(dsn, target_dir, db_user):
    from casemgr.schema import schema, upgrade, check, seed

    dbobj.execute_debug(debug)
    db_desc_dir = os.path.join(target_dir, 'db')
    db = schema.define_db(dsn)
    print 'Phase 1 - schema upgrades'
    upgrade.Upgrades(db, target_dir).run()
    db.commit()
    print 'Phase 2 - create new entities'
    db.make_database() # implicit commit
    print 'Phase 3 - form checks'
    check.check_form_dependancies(db, db_user)
    db.commit()
    print 'Phase 4 - fix table ownership'
    db.chown(db_user)
    print 'Phase 5 - seeding database'
    seed.seed_db(db)
    db.commit()
    print 'Phase 6 - write describer'
    owner = get_ugid(db_user)
    make_dirs(db_desc_dir, owner)
    db.save_describer(db_desc_dir, owner = owner, mode = 0644)
    return db

def usage():
    sys.exit('''\
Usage: %s [opts] <dsn> <cgi_target_dir>
    -u <user>   grant db tables and chown files to this user
    -G          grant only (don't preen database)
    -R          revoke only (don't preen database)
    -v          verbose
    -D          debug''' % sys.argv[0])
    

if __name__ == '__main__':
    import getopt
    
    user = 'www-data'
    try:
        opts, args = getopt.getopt(sys.argv[1:], '?hu:vDTGR')
    except getopt.GetoptError, e:
        sys.exit(e)
    grant_only = revoke_only = False
    for opt, arg in opts:
        if opt in ('-h', '-?'):
            usage()
        elif opt == '-u':
            user = arg
        elif opt == '-v':
            verbose = True
        elif opt == '-D':
            debug = True
        elif opt == '-G':
            grant_only = True
        elif opt == '-R':
            revoke_only = True
    try:
        dsn, cgi_target = args
    except ValueError:
        usage()
    if grant_only and revoke_only:
        usage()
    sys.path.insert(0, cgi_target)
    from cocklebur import dbobj
    if grant_only or revoke_only:
        dbobj.execute_debug(debug)
        db = dbobj.get_db(os.path.join(cgi_target, 'db'), dsn)
        curs = db.cursor()
        for table_desc in db.get_tables():
            if grant_only:
                table_desc.grant(curs, user)
            if revoke_only:
                table_desc.revoke(curs, user)
        curs.close()
        db.commit()
        db.close()
    else:
        db = compile_db(dsn, cgi_target, user)
elif __name__ == '__install__':
    print "checking database"
    sys.path.insert(0, config.cgi_target)
    from cocklebur import dbobj

    verbose = config.install_verbose
    debug = config.install_debug
    target = config.cgi_target
    if config.install_prefix:
        target = os.path.join(config.install_prefix, target)
    db = compile_db(config.dsn, target, config.web_user)
