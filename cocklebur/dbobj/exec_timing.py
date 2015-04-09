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

class ExecCmdTiming(object):

    __slots__ = 'total', 'count'

    def __init__(self):
        self.total = 0.0
        self.count = 0

    def record(self, el):
        self.total += el
        self.count += 1


class ExecTiming:

    def __init__(self):
        self.timings = {}

    def record(self, cmd, el):
        try:
            ect = self.timings[cmd]
        except KeyError:
            ect = self.timings[cmd] = ExecCmdTiming()
        ect.record(el)

    def __str__(self):
        report = ['Top 20 queries (av time, freq, cmd):']
        timings = [(ect.total / ect.count, ect.count, cmd)
                   for cmd, ect in self.timings.iteritems()]
        timings.sort()
        for avg, freq, cmd in timings[-1:-20:-1]:
            report.append('   %.3fs %4d %s' % (avg, freq, cmd))
        return '\n'.join(report)

exec_timing = ExecTiming()

def show():
    import sys
    print >> sys.stderr, exec_timing
