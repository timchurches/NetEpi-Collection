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
import sys
import time
import socket
import config
import errno

def main(args):
    if config.notification_host == 'none':
        sys.exit('Notifications not enabled?')
    if config.notification_host == 'local':
        af = socket.AF_UNIX
        address = os.path.join(config.cgi_target,'db','notification','socket')
    else:
        af = socket.AF_INET
        address = config.notification_host, config.notification_port
    while 1:
        sock = socket.socket(af, socket.SOCK_STREAM)
        try:
            sock.connect(address)
        except socket.error, (eno, estr):
            if eno not in (errno.ECONNREFUSED, errno.ENOENT):
                raise
            time.sleep(1)
            continue
        print 'Connected'
        sock.send('monitor on\n')
        while 1:
            try:
                buf = sock.recv(8192)
            except KeyboardInterrupt:
                sys.exit(0)
            if not buf:
                break
            sys.stdout.write(buf)
        print 'Disconnected'

if __name__ == '__main__':
    main()
