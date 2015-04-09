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
import socket
import select
import errno

class SocketCore:
    def __init__(self, sock=None, addr=None):
        self.sock = sock
        self.addr = addr
        self.wrbuf = ''
        self.rdbuf = ''
        if sock:
            self.read_start()

    def fileno(self):
        return self.sock.fileno()

    def write(self, data):
        if data and not self.wrbuf:
            self.write_start()
        self.wrbuf += data

    def write_start(self):
        "Add the socket to the write select list"

    def write_stop(self):
        "Remove the socket to the write select list"

    def read_start(self):
        "Add the socket to the read select list"

    def read_stop(self):
        "Remove the socket to the read select list"

    def close(self):
        if self.sock is not None:
            self.read_stop()
            self.write_stop()
            try:
                self.sock.close()
            except socket.error, (eno, estr):
                self.log('%s: close: %s' % (self.addr, estr))
            self.sock = None

    def close_event(self):
        self.close()

    def write_event(self):
        "Socket ready for write"
        if self.sock is not None:
            try:
                n = self.sock.send(self.wrbuf)
            except socket.error, (eno, estr):
                if eno == errno.EAGAIN:
                    return
                self.log('%s: send: %s' % (self.addr, estr))
                return self.close_event()
            self.wrbuf = self.wrbuf[n:]
            if not self.wrbuf:
                self.write_stop()

    def read_event(self):
        "Socket ready for read"
        if self.sock is not None:
            try:
                buf = self.sock.recv(8192)
            except socket.error, (eno, estr):
                if eno == errno.EAGAIN:
                    return
                if eno != errno.ECONNRESET:
                    self.log('%s: recv: %s' % (self.addr, estr))
                return self.close_event()
            if not buf:
                return self.close_event()
            lines = (self.rdbuf + buf).split('\n')
            self.rdbuf = lines.pop(-1)
            for line in lines:
                self.proc_line(line)

    def poll(self):
        w = []
        if self.wrbuf:
            w = [self.sock]
        r, w, e = select.select([self.sock], w, [], 0)
        if r:
            self.read_event()
        if w:
            self.write_event()
        
    def log(cls, msg):
        print >> sys.stderr, '%s.%s: %s' % (cls.__module__, cls.__name__, msg)
    log = classmethod(log)
