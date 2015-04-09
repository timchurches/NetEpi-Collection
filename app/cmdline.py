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

"""\
NetEpi Collection, command line interface.

    help                This help message.
    dupscan             Scan for duplicate person records
    export cases        CSV export of case data
    export form         Export form definition
    export report       Export report definition
    importxml           Import XML cases and persons.
    list forms          List available form definitions
    list reports        List available report definitions
    list syndromes      List available syndromes 
    report              Run a report

Maintenance and debugging commands (you probably won't need to use these):
    notifymon           Monitor change notification bus.
    personindex         Rebuild fuzzy person index (typically this is only
                        needed if the indexing algorithm has changed).
"""

import sys, os
sys.path.insert(0, '{{CGITARGET}}')
try:
    import casemgr, cocklebur
except ImportError:
    sys.exit('Cannot find application modules in {{CGITARGET}}')
import config
from cocklebur import dbobj

ourname = os.path.basename(sys.argv[0])

def setflag(name, arg):
    try:
        index = sys.argv.index(arg)
    except ValueError:
        setattr(config, name, False)
    else:
        setattr(config, name, True)
        del sys.argv[index]

setflag('debug', '-D')
setflag('tracedb', '-T')

mode = 'help'
if len(sys.argv) > 1:
    mode = sys.argv.pop(1)
if mode == 'help' or mode == '-h' or mode == '--help':
    if len(sys.argv) > 1:
        # ... help <mode>
        mode = sys.argv.pop(1)
        sys.argv.append('-h')
    else:
        # ... help
        print __doc__
        sys.exit(0)
elif mode in ('list', 'export'):
    if len(sys.argv) > 1:
        mode = '%s %s' % (mode, sys.argv.pop(1))
    else:
        sys.exit('%s what? See "%s help"' % (mode.title(), ourname))

main = None
try:
    module = __import__('casemgr.cmdline.' + mode.replace(' ', ''), 
                        None, None, 'main')
except ImportError:
    pass
else:
    try:
        main = module.main
    except AttributeError:
        pass
if main is None:
    sys.exit('Unknown mode %r. See "%s help"' % (mode, ourname))
main(sys.argv[1:])
