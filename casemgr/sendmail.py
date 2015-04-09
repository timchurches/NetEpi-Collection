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
import re
import sys
from email import Message, Utils, Errors

value_addr_re = re.compile(r'^[a-z][a-z0-9_.-]*@([a-z_-]+\.)*[a-z_-]+$',
                           re.IGNORECASE)
def valid_addr(addr):
    if not value_addr_re.match(addr):
        raise Errors.MessageError('invalid address %r' % addr)

class Sendmail:
    """
    A proxy that knows how to invoke sendmail for
    email.Message.Message-like classes.
    """
    sm_path_try = (
        '/usr/lib/sendmail',
        '/usr/sbin/sendmail',
    )

    def __init__(self, message_ctor = None, *args, **kwargs):
        if message_ctor is None:
            message_ctor = Message.Message
        self.message = message_ctor(*args, **kwargs)

    def __getattr__(self, a):
        return getattr(self.message, a)

    def getaddrs(self, *hdrs):
        addrs = []
        for hdr in hdrs:
            for cmt, addr in Utils.getaddresses(self.get_all(hdr, [])):
                try:
                    valid_addr(addr)
                except Errors.MessageError, e:
                    raise Errors.MessageError('%s: %s' % (hdr, e))
                addrs.append(addr)
        return addrs

    def send(self):
        sender = self.getaddrs('from')
        if sender:
            if len(sender) > 1:
                raise Errors.MessageError('More than one sender specified: %s' %
                                          (', '.join(sender)))
            else:
                sender = sender[0]
        recipients = self.getaddrs('to', 'cc')
        if not recipients:
            raise ValueError('no recipients specified')
        if not self.has_key('subject'):
            self.add_header('subject', ' '.join(sys.argv))
        for sm_path in self.sm_path_try:
            if os.path.exists(sm_path):
                sendmail = sm_path
                break
        else:
            raise ValueError('sendmail not found')
        args = [sendmail]
        if sender:
            args.append('-f' + sender)
        args.extend(recipients)
        sm = os.popen(' '.join(args), 'w')
        try:
            sm.write(self.as_string(unixfrom = False))
        finally:
            if sm.close():
                print >> sys.stderr, 'command failed: %s' % ' '.join(args)
