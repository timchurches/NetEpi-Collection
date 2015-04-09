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
import re
import pylab

rep=re.compile(r'matching took (\d+)\..* (\d+) records')

def plot(fns):
    x = []
    y = []
    for fn in fns:
        for line in open(fn):
            match = rep.search(line)
            if match:
                x.append(int(match.group(2)))
                y.append(float(match.group(1)) / 60)
    pylab.plot(x, y)
    a = pylab.gca()
    a.set_xlabel('Persons')
    a.set_ylabel('Minutes')
    pylab.title('Dupe scan time')
    pylab.savefig('dupescan.png')
                

if __name__ == '__main__':
    plot(sys.argv[1:])
