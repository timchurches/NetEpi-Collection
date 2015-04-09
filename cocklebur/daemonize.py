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

import os

def daemonize():
    """
    Background and dissociate from controlling tty's - this is very much
    unix specific. Refer to Stevens' "Advanced Programming in the
    Unix Environment"
    """
    # Background
    pid = os.fork()
    if pid:
        os.waitpid(pid, 0)      # Wait for intermedite process - avoid zombie
        return True # Parent
    # Child
    os.setsid()
    if os.fork():
        os._exit(0)             # Ensure we aren't process group leader
    devnull = os.open("/dev/null", os.O_RDWR)
    os.close(0)
    os.close(1)
    os.dup2(devnull, 0)
    os.dup2(devnull, 1)
    os.close(devnull)
    return False
