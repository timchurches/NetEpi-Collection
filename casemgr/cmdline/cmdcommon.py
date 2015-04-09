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
import os

from cocklebur import dbobj
from casemgr import globals
import config

ourname = sys.argv[0]

def abort(msg):
    sys.exit('%s: %s' % (ourname, msg))


def search_one(query, term, keycol, *cols):
    assert len(cols) > 0
    try:
        return int(term)
    except ValueError:
        if len(cols) > 1:
            likequery = query.sub_expr('OR')
        else:
            likequery = query
        for col in cols:
            likequery.where('%s ILIKE %%s' % col, dbobj.wild(term))
        keys = query.fetchcols(keycol)
        if not keys:
            abort('%r not found' % term)
        if len(keys) > 1:
            labels = query.fetchcols(cols[0])
            abort('%r matches multiple values: %s' % (term, ', '.join(labels)))
        return keys[0]


def get_syndrome_id(term):
    if not term:
        abort('No syndrome specified (see "%s list syndromes")' % ourname)
    query = globals.db.query('syndrome_types')
    query.where('enabled')
    return search_one(query, term, 'syndrome_id', 'name')


def get_user_id(term):
    query = globals.db.query('users')
    query.where('enabled')
    query.where('not deleted')
    return search_one(query, term, 'user_id', 'fullname', 'username')


def get_unit_id(term):
    query = globals.db.query('units')
    query.where('enabled')
    return search_one(query, term, 'unit_id', 'name')
    

def get_report_id(term):
    query = globals.db.query('report_params')
    query.where('sharing <> %s', 'last')
    return search_one(query, term, 'report_params_id', 'label')


def user_cred(options):
    from casemgr import credentials
    try:
        cred = credentials.Credentials()
        cred.auth_override(globals.db, options.username)
    except credentials.SelectUnit:
        # No mechanism to select appropriate units in this case at this time.
        abort('user %r cannot be a member of multiple %ss' %
                 (options.username, config.unit_label.lower()))
    except credentials.CredentialError, e:
        abort('authentication: %s: %r' % (e, options.username))
    return cred
    

def opt_verbose(optp):
    optp.add_option("-v", "--verbose", dest="verbose", action='store_true',
            help="Emit additional status messages")

def opt_user(optp):
    optp.add_option('-u', '--username', default='admin',
            help="Run with rights of user USERNAME (default '%default')", 
            metavar="USERNAME")


def opt_syndrome(optp):
    optp.add_option('-s', '--syndrome',
                    help="Use specified syndrome (%s)" % config.syndrome_label)


def opt_outfile(optp):
    optp.add_option("-o", "--outfile", dest="outfile",
            help="Write output to FILENAME", metavar="FILENAME")


class OUTFILE: pass


def _list_replace(l, find, replace):
    for i, v in enumerate(l):
        if v is find:
            l[i] = replace


def _dict_replace(d, find, replace):
    for k, v in d.iteritems():
        if v is find:
            d[k] = replace


def safe_overwrite(options, fn, *args, **kw):
    """
    Note, this is not "safe" in the sense that tempfile means (against
    people playing symlink tricks in the target directory. This only
    attempts to ensure the target file is updated "atomically" (no
    partial file) by renaming a temporary file into place. OUTFILE
    should appear in the /fn/ arguments - it will be replaced with the
    actual output file.
    """
    args = list(args)
    if options.outfile:
        outfile_dir, outfile_fn = os.path.split(options.outfile)
        try:
            tmp_fn = '%s.tmp%s' % (options.outfile, os.getpid())
            outfile = open(tmp_fn, 'wb')
        except EnvironmentError, (eno, estr):
            abort('%s: %s: %s' % (ourname, options.outfile, estr))
        try:
            _list_replace(args, OUTFILE, outfile)
            _dict_replace(kw, OUTFILE, outfile)
            ret = fn(*args, **kw)
        except Exception, e:
            try:
                outfile.close()
            except EnvironmentError:
                pass
            os.unlink(tmp_fn)
            abort(e)
        else:
            outfile.close()
            os.rename(tmp_fn, options.outfile)
    else:
        _list_replace(args, OUTFILE, sys.stdout)
        _dict_replace(kw, OUTFILE, sys.stdout)
        ret = fn(*args, **kw)
        sys.stdout.flush()
    return ret
