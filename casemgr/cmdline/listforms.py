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

from optparse import OptionParser

from cocklebur import datetime
from casemgr import globals
from casemgr.cmdline import cmdcommon

def main(args):
    optp = OptionParser()
    cmdcommon.opt_verbose(optp)
    options, args = optp.parse_args(args)
    query = globals.db.query('forms', order_by='label')
    for row in query.fetchall():
        if options.verbose:
            print '%s (version %s, updated %s)' % (row.label, row.cur_version, 
                                        datetime.relative(row.def_update_time))
        else:
            print row.label
