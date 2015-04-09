#!/usr/bin/python
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
from optparse import OptionParser

try:
    import psyco
except ImportError:
    pass
else:
    psyco.full()

import config
from casemgr import globals, persondupe
from casemgr.notification.client import connect as notify_connect
from casemgr.cmdline import cmdcommon

usage = '%prog [options]'

def main(args):
    optp = OptionParser(usage=usage)
    cmdcommon.opt_user(optp)
    cmdcommon.opt_verbose(optp)
    options, args = optp.parse_args(args)

    cred = cmdcommon.user_cred(options)

    globals.notify = notify_connect(config.cgi_target,
                                    config.notification_host,
                                    config.notification_port)

    try:
        mp = persondupe.MatchPersons(globals.db, None)
        mp.save(globals.db)
        if options.verbose:
            print mp.stats()
            mp.report()
        globals.db.commit()
    except persondupe.DupeRunning:
        cmdcommon.abort('Already running')


if __name__ == '__main__':
    main(sys.argv[1:])
