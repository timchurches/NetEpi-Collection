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
import fnmatch

from optparse import OptionParser

from casemgr import globals, credentials, exportselect
from casemgr.syndrome import UnitSyndromesView
from casemgr.cmdline import cmdcommon

ourname = os.path.basename(sys.argv[0])

def get_option_parser():
    """
    Create the option parser for the script
    """
    usage = '%prog [options] -s syndrome [forms] (use \\? for a list)'
    optp = OptionParser(usage=usage)
    cmdcommon.opt_user(optp)
    cmdcommon.opt_outfile(optp)
    cmdcommon.opt_syndrome(optp)
    optp.set_defaults(export_scheme="classic", 
                      deleted='n', strip_newlines=False)
    optp.add_option("-x", "--exclude-deleted", dest="deleted",
            action="store_const", const='n',
            help="exclude deleted records from output")
    optp.add_option("-d", "--include-deleted", dest="deleted",
            action="store_const", const="both", 
            help="include deleted records in output")
    optp.add_option("--only-deleted", dest="deleted",
            action="store_const", const='y',
            help="include deleted records in output")
    optp.add_option("-l", "--strip-newlines", dest="strip_newlines",
            action="store_true",
            help="replace newlines embedded in fields with spaces")
    optp.add_option("-S", "--scheme", dest="export_scheme",
            help="export using EXPORTSCHEME, default 'classic'. Use '\\?' "
                 "to see a list of available schemes.", metavar="EXPORTSCHEME")
    return optp

def print_indexed_list(indexed_list):
    maxlen = max([ len(str(i[0])) for i in indexed_list ])
    indexed_list = [ (name, label) for (label, name) in indexed_list ]
    indexed_list.sort()
    fmt = "%%%ds: %%s" % maxlen
    for name, label in indexed_list:
        print fmt % (label, name)


def print_export_schemes(es):
    """
    Print a human readable mapping of syndrome names to id
    """


def main(args):
    """
    Parse arguments and simulate the use of the export page
    """

    optp = get_option_parser()
    options, args = optp.parse_args(args)


    cred = cmdcommon.user_cred(options)

    syndrome_id = cmdcommon.get_syndrome_id(options.syndrome)

    es = exportselect.ExportSelect(syndrome_id)
    es.deleted = options.deleted
    es.strip_newlines = options.strip_newlines

    # Parse export scheme specification
    schemes = [scheme for scheme, description in es.scheme_options()]
    if options.export_scheme == '?' or options.export_scheme not in schemes:
        print 'Export schemes:'
        print_indexed_list(list(es.scheme_options()))
        sys.exit(1)
    es.export_scheme = options.export_scheme

    es.refresh(cred)
    exporter = es.exporter

    # Parse forms (if any)
    if '?' in args:
        print 'Forms:'
        forms = [(form.label, form.name) for form in exporter.forms]
        print_indexed_list(forms)
        sys.exit(1)
    formnames = [form.label for form in exporter.forms]
    for name in args:
        if name not in formnames:
            optp.error('form %r not found (for this syndrome?)' % name)
    include_forms = args

    # load the data and export
    cmdcommon.safe_overwrite(options, exporter.csv_write, 
                             include_forms, cmdcommon.OUTFILE)


if __name__ == '__main__':
    main(sys.argv[1:])

