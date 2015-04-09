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

# System libraries
import sys
import os
import socket
import errno
try:
    set
except NameError:
    from sets import Set as set

# Application modules
from socketcore import SocketCore
from daemon import notification_daemon

def exec_daemon(host, port=None):
    pid = os.fork()
    if pid:
        # Parent (forks again after init, and intermediate exits)
        os.waitpid(pid, 0)
    else:
        thisdir = os.path.dirname(__file__)
        daemonpath = os.path.join(thisdir, 'daemon.py')
        pypath=os.path.abspath(os.path.join(thisdir, os.pardir, os.pardir))
        args = ['python', daemonpath, '--bg', '--listen', host]
        if port:
            args.append('--port')
            args.append(port)
        env=dict(PYTHONPATH=pypath)
        os.execve(sys.executable, args, env)
        sys._exit(1)


class dummy_notification_client:

    def poll(self):
        pass

    def notify(self, *event):
        pass

    def subscribe(self, event, callback):
        return False


class notification_client(SocketCore):

    def __init__(self):
        SocketCore.__init__(self)
        self.sock = None
        self.subscriptions = {}
        self.sent_subscriptions = set()

    def connect(self):
        self.sock.setblocking(0)
        self.sent_subscriptions = set()
        self.poll()

    def proc_line(self, line):
        words = line.split()
        if words[0] == '!':
            callbacks = self.subscriptions.get(words[2])
            if callbacks:
                for callback in callbacks:
                    callback(*words[3:])

    def subscribe(self, event, callback):
        if self.sock is None:
            self.connect()
        try:
            self.subscriptions[event].add(callback)
        except KeyError:
            callbacks = self.subscriptions[event] = set()
            callbacks.add(callback)
        return True

    def notify(self, *event):
        # Notifications should only be sent after transactions are committed to
        # the database, or a quick client may fetch the data before the
        # transaction is committed.
        if self.sock is None:
            self.connect()
        self.write('notify %s\n' % ' '.join(map(str, event)))
        self.poll()

    def poll(self):
        if self.sock is None:
            self.connect()
        want_subscriptions = set(self.subscriptions)
        add = want_subscriptions - self.sent_subscriptions
        if add:
            self.write('subscribe %s\n' % ','.join(add))
            self.sent_subscriptions = want_subscriptions
        SocketCore.poll(self)


class unix_notification_client(notification_client):
    def __init__(self, path):
        notification_client.__init__(self)
        self.path = os.path.join(path, 'db', 'notification', 'socket')

    def connect(self):
        sockdir = os.path.dirname(self.path)
        try:
            os.mkdir(sockdir)
        except OSError, (eno, estr):
            if eno != errno.EEXIST:
                raise
        else:
            os.chmod(sockdir, 0300)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.sock.connect(self.path)
        except socket.error, (eno, estr):
            if eno == errno.ECONNREFUSED:
                # Daemon has died without cleaning up? This is racy...
                self.unlink()
            elif eno != errno.ENOENT:
                self.sock.close()
                raise
            exec_daemon(self.path)
            self.sock.connect(self.path)
        notification_client.connect(self)

    def unlink(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass


class inet_notification_client(notification_client):
    def __init__(self, host, port):
        notification_client.__init__(self)
        self.host = host
        self.port = port

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.host, self.port))
        except socket.error:
            self.sock.close()
            raise
        notification_client.connect(self)


def connect(path, host, port):
    if host == 'none':
        return dummy_notification_client()
    try:
        if host == 'local':
            return unix_notification_client(path)
        else:
            return inet_notification_client(host, port)
    except Exception:
        import sys, traceback
        traceback.print_exc()
        print >> sys.stderr, 'WARNING: notification client startup failed, falling back on time-based cache expiry'
        return dummy_notification_client()
