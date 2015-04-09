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

import sys, os
from optparse import OptionParser

from cocklebur.form_ui.xmlsave import xmlsave
from casemgr import globals
from casemgr.cmdline import cmdcommon

def main(args):
    optp = OptionParser()
    cmdcommon.opt_outfile(optp)
    options, args = optp.parse_args(args)
    if len(args) == 2:
        name = args[0]
        version = int(args[1])
    elif len(args) == 1:
        name = args[0]
        query = globals.db.query('forms')
        query.where('label=%s', name)
        row = query.fetchone()
        if row is None:
            cmdcommon.abort('Unknown form %r', name)
        version = row.cur_version
    else:
        sys.exit('Usage: %s exportform <name> [version]')

    try:
        form = globals.formlib.load(name, version)
    except Exception, e:
        cmdcommon.abort(e)

    cmdcommon.safe_overwrite(options, xmlsave, cmdcommon.OUTFILE, form)
