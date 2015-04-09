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

from casemgr import globals
from casemgr import reports

from casemgr.cmdline import cmdcommon

usage = '%prog [options] <report_name_or_pattern>'

def main(args):
    optp = OptionParser(usage=usage)
    cmdcommon.opt_user(optp)
    cmdcommon.opt_outfile(optp)
    options, args = optp.parse_args(args)
    if len(args) != 1:
        optp.usage()

    report_id = cmdcommon.get_report_id(args[0]) 

    cred = cmdcommon.user_cred(options)

    params = reports.load(report_id, cred)
    cmdcommon.safe_overwrite(options, params.xmlsave, cmdcommon.OUTFILE)
