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
import os
import sys
import socket
import select
import errno
try:
    set
except NameError:
    from sets import Set as set

from cocklebur.daemonize import daemonize

from socketcore import SocketCore


class Client(SocketCore):
    def __init__(self, registry, sock, addr):
        self.registry = registry
        SocketCore.__init__(self, sock, addr)
        self.write('+ OK\n')

    def write_start(self):
        self.registry.write_start(self)

    def write_stop(self):
        self.registry.write_stop(self)

    def read_start(self):
        self.registry.read_start(self)

    def read_stop(self):
        self.registry.read_stop(self)

    def close_event(self):
        self.close()
        self.registry.client_close(self)

    def proc_line(self, line):
        words = line.split()
        if words:
            cmd = words.pop(0)
            try:
                meth = getattr(self, 'do_' + cmd)
            except AttributeError:
                self.write('- Unknown command %r\n' % cmd)
            else:
                try:
                    meth(*words)
                except SystemExit:
                    raise
                except Exception, e:
                    self.write('- %s\n' % e)

    def notify(self, *args):
        self.write('! NOTIFY %s\n' % (' '.join(args)))

    def monitor(self, msg):
        self.write('! MONITOR %s\n' % msg)

    def do_subscribe(self, events):
        self.write('+ OK\n')
        self.registry.subscribe(self, events)

    def do_notify(self, *args):
        self.write('+ OK\n')
        self.registry.notify(self, *args)

    def do_list(self):
        for evname in self.registry.seen:
            self.write('%s\n' % evname)
        self.write('+ OK\n')

    def do_subscribers(self):
        for evname, clients in self.registry.events.iteritems():
            self.write('%s\n' % evname)
            for client in clients:
                self.write('  %s\n' % (client.addr,))
        self.write('+ OK\n')
        
    def do_help(self):
        self.write('notify <event>,...       Send notifications for events\n')
        self.write('subscribe <event>,...    Subscribe to events\n')
        self.write('list                     List events\n')
        self.write('help                     This help text\n')
        self.write('+ OK\n')

    def do_monitor(self, state):
        if state == 'on':
            self.registry.add_monitor(self)
        elif state == 'off':
            self.registry.del_monitor(self)
        else:
            self.write('! monitor <on|off>\n')
            return
        self.write('+ OK\n')

    def do_quit(self):
        self.close()

    def do_shutdown(self):
        self.log('Received SHUTDOWN from %s' % (self.addr,))
        sys.exit(0)


class Registry:
    def __init__(self, sock):
        self.events = {}
        self.sock = sock
        self.clients = set()
        self.read_start(self)
        self.writers = set()
        self.seen = set()
        self.monitors = set()

    def fileno(self):
        return self.sock.fileno()

    def write_start(self, client):
        self.writers.add(client)

    def write_stop(self, client):
        self.writers.discard(client)

    def read_start(self, client):
        self.clients.add(client)

    def read_stop(self, client):
        self.clients.discard(client)

    def read_event(self):
        s, addr = self.sock.accept()
        s.setblocking(0)
        Client(self, s, addr)

    def add_monitor(self, client):
        self.monitors.add(client)

    def del_monitor(self, client):
        self.monitors.discard(client)

    def monitor(self, msg):
        for client in self.monitors:
            client.monitor(msg)

    def subscribe(self, client, events):
        if self.monitors:
            self.monitor('subscribe from %s, events %s' % (client.addr, events))
        for evname in events.split(','):
            try:
                event = self.events[evname]
            except KeyError:
                event = self.events[evname] = set()
            event.add(client)

    def notify(self, client, evname, *args):
        if self.monitors:
            self.monitor('notify from %s, event %s, args %s' % 
                            (client.addr, evname, args))
        self.seen.add(evname)
        event = self.events.get(evname)
        if event:
            for client in event:
                client.notify(evname, *args)

    def client_close(self, client):
        self.del_monitor(client)
        for event in self.events.itervalues():
            event.discard(client)

    def poll(self):
        r, w, e = select.select(list(self.clients), list(self.writers), [], None)
        for o in r:
            o.read_event()
        for o in w:
            o.write_event()


def notification_daemon(address_family, address, want_background=True):
    l = socket.socket(address_family, socket.SOCK_STREAM)
    l.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    l.setblocking(0)
    try:
        l.bind(address)
        l.listen(5)
    except socket.error, (eno, estr):
        if eno == errno.EADDRINUSE:
            l.close()
            return
        raise
    if want_background and daemonize():
        l.close()
        return                  # Parent
    try:
        registry = Registry(l)
        while 1:
            registry.poll()
    finally:
        try:
            l.close()
        except socket.error:
            pass
        if address_family == AF_UNIX:
            try:
                os.unlink(address)
            except OSError:
                pass
    sys.exit(0)


def kill_daemon(addr, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((addr, port))
    except socket.error, (eno, estr):
        if eno != errno.ECONNREFUSED:
            sys.exit('%s port %s: %s' % (addr, port, estr))
    else:
        s.send('shutdown\n')
        s.close()


if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser()
    parser.add_option('-l', '--listen', default='0.0.0.0',
                      help='Listen address (default ALL)', metavar='ADDR')
    parser.add_option('-p', '--port', type='int', default=13535,
                      help='port to listen on')
    parser.add_option('--background', '--bg', 
                      default=False, action='store_true',
                      help='Daemonise (background and dissociate from tty)')
    parser.add_option('--kill', default=False, action='store_true',
                      help='kill running daemon (if any)')
    options, args = parser.parse_args()
    if options.listen.startswith('/'):
        af = socket.AF_UNIX
        address = options.listen
    else:
        af = socket.AF_INET
        address = (options.listen, options.port)
    if options.kill:
        kill_daemon('127.0.0.1', options.port)
    else:
        notification_daemon(af, address, want_background=options.background)
