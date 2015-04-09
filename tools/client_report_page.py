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

"""
Generate a page with various plots from the client reports
"""

import sys
import os

import client_report

class Options:
    def __init__(self, d):
        self.filter = None
        self.groupby = None
        self.local = False
        self.logscale = False
        self.outfile = None
        self.rate = False
        self.__dict__.update(d)

def generate_page(outdir, *infiles):
    def plot(lines, name, **kwargs):
        fn  = name + '.png'
        outfiles.append(fn)
        kwargs['plotfile'] = os.path.join(outdir, fn)
        client_report.plot(Options(kwargs), lines)
    outfiles = []
    lines = list(client_report.parse_files(infiles))
    plot(lines, 'rate', rate=True)
    plot(lines, 'local_page', local=True, groupby='page')
    plot(lines, 'remote_page', local=False, groupby='page')
    plot(lines, 'remote_ip', local=False, groupby='ip')
    f = open(os.path.join(outdir, 'index.html'), 'w')
    f.write('<html><body><center>')
    for of in outfiles:
        f.write('<img src="%s"><br>' % of)
    f.write('</center></body></html>')
    f.close()


if __name__ == '__main__':
    os.environ['TZ'] = 'Australia/NSW'
    if len(sys.argv) < 3:
        sys.exit('Usage: %s <outdir> <infiles> ...')
    generate_page(*sys.argv[1:])

