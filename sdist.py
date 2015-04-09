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

# $Id: sdist.py 4432 2011-03-03 01:08:38Z andrewm $

from distutils.core import setup
import sys, os
sys.argv.extend(['sdist', '--force-manifest'])
thisdir = os.path.normpath(os.path.dirname(__file__))
from casemgr.version import __version__

svnrev = os.popen('svnversion %s' % thisdir).read().strip()
f = open(os.path.join(thisdir, 'casemgr', 'svnrev.py'), 'w')
f.write('__svnrev__ = %r\n' % svnrev)
f.close()

import sys
sys.argv.extend(['sdist', '--force-manifest'])
setup(name = "NetEpi-Collection",
    version = __version__,
    maintainer = "NSW Department of Health",
    maintainer_email = "Tim CHURCHES <TCHUR@doh.health.nsw.gov.au>",
    description = "Network-enabled tools for epidemiology and public health practice",
    url = "http://netepi.org/",
    license = 'Health Administration Corporation Open Source License Version 1.2',
    packages = [],
)
