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

from casemgr import globals

dupescan_phase = dupescan_pc = dupescan_etc = None

def dupescan_event(phase, pc, etc):
    global dupescan_phase, dupescan_pc, dupescan_etc
    dupescan_phase = phase
    dupescan_pc = int(pc)
    dupescan_etc = int(etc)

def dupescan_subscribe():
    globals.notify.subscribe('dupescan', dupescan_event)

def dupescan_notify(phase, pc, etc):
    globals.notify.notify('dupescan', phase, int(pc), int(etc))

class DupeRunning(globals.Error):
    def __init__(self):
        globals.notify.poll()
        msg = 'Duplicate scan in progress'
        if dupescan_phase:
            msg += ', %s phase' % dupescan_phase
        if dupescan_pc and dupescan_etc:
            msg += ' %d%% complete, estimated completion in ' % dupescan_pc
            if dupescan_etc < 90:
                msg += '%d seconds' % dupescan_etc
            elif dupescan_etc < (90*60):
                msg += '%d minutes' % (dupescan_etc / 60)
            else:
                msg += '%d hours' % (dupescan_etc / 60 / 60)
        Exception.__init__(self, msg)

