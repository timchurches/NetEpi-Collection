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
import csv

from optparse import OptionParser

from casemgr import reports, messages
from casemgr.cmdline import cmdcommon

usage = '%prog [options] [report_name_or_pattern]'

def html_table(options, cred, params):
    cmdcommon.abort('HTML report not supported (yet)')


def csv_table(options, cred, params):
    try:
        params.export_rows
    except AttributeError:
        cmdcommon.abort('report type %r does not support CSV export' % 
                        params.report_type)
    msgs = params.check()
    if msgs.have_errors():
        cmdcommon.abort('\n'.join(msgs.get_messages()))
    try:
        repgen = params.export_rows(cred)
    except reports.Error, e:
        cmdcommon.abort(e)
    csv_write = lambda f, lines: csv.writer(f).writerows(lines)
    cmdcommon.safe_overwrite(options, csv_write, cmdcommon.OUTFILE, repgen)


def image_out(cred, params, outfile):
    msgs = params.check()
    try:
        params.report(cred, msgs, filename=outfile)
    except reports.Error, e:
        cmdcommon.abort(e)


def main(args):
    optp = OptionParser(usage=usage)
    cmdcommon.opt_user(optp)
    cmdcommon.opt_outfile(optp)
    cmdcommon.opt_syndrome(optp)
    optp.add_option('--csv', action='store_true',
            help='For line report, use CSV format (default)')
    optp.add_option('--html', action='store_true',
            help='For line report, use HTML format')
    optp.add_option('-p', '--param-file', metavar='FILENAME',
                    help='Read report parameters from FILENAME')
    options, args = optp.parse_args(args)
    if options.param_file and args:
        optp.error('Specify a parameter file OR report name, not both')

    cred = cmdcommon.user_cred(options)

    if args:
        if len(args) > 1:
            optp.error('Specify only one report name')
        report_id = cmdcommon.get_report_id(args[0]) 
        params = reports.load(report_id, cred)
    elif options.param_file:
        if not options.syndrome:
            optp.error('Specify a syndrome')
        syndrome_id = cmdcommon.get_syndrome_id(options.syndrome)
        try:
            f = open(options.param_file, 'rU')
        except EnvironmentError, (eno, estr):
            cmdcommon.abort('%s: %s' % (options.param_file, estr))
        try:
            try:
                params = reports.parse_file(syndrome_id, f)
            finally:
                f.close()
        except reports.Error, e:
            cmdcommon.abort('%s: %s' % (options.param_file, e))
    else:
        optp.error('Specify either a parameter file OR report name')

    if params.report_type in ('line', 'crosstab'):
        if options.html:
            html_table(options, cred, params)
        else:
            csv_table(options, cred, params)
    elif params.report_type in ('epicurve', 'contactvis'):
        if not options.outfile:
            optp.error('Specify an output file (--outfile)')
        image_out(cred, params, options.outfile)
    else:
        cmdcommon.abort('Report type %r not supported by command line interface' % params.report_type)
