#!/usr/bin/python
#
#   The contents of this file are subject to the HACOS License Version 1.2
#   (the "License"); you may not use this file except in compliance with
#   the License.  Software distributed under the License is distributed
#   on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
#   implied. See the LICENSE file for the specific language governing
#   rights and limitations under the License.  The Original Software
#   is "NetEpi Case Manager". The Initial Developer of the Original
#   Software is the Health Administration Corporation, incorporated in
#   the State of New South Wales, Australia.
#
#   Copyright (C) 2006 Health Administration Corporation.
#   All Rights Reserved.
#
# $Source: /usr/local/cvsroot/NSWDoH/httpinteract/httpinteract.cgi,v $
# $Id: httpinteract.cgi,v 1.7 2006/04/21 04:55:27 andrewm Exp $

import sys, os
from datetime import datetime
from pyPgSQL import PgSQL

server_send = 30 * 1024                 # Bytes to send to client
client_send = 4 * 1024                  # Bytes sent by client to us
interval = 60                           # Time between tests in seconds
motd = '''\
Thankyou for participating in this test.
'''                                     # Message to users

database = dict(database='httpinteract')
table = 'reports'

server_junk = 'X' * server_send


client_data = sys.stdin.read()

if 0:
    f = open('/tmp/x', 'w')
    for k, v in os.environ.items():
        f.write('%20s: %s\n' % (k, v))
    f.write('%r\n' % client_data)
    f.close()

print """\
Content-type: text/plain

{
    "interval": %(interval)r,
    "sendcount": %(client_send)r,
    "motd": %(motd)r,
    "junk": %(server_junk)r
}
""" % vars()
sys.stdout.close()

class Updater:
    cols = ('started', 'siteinfo', 'status', 'elapsed', 'received', 
              'srcaddr', 'forwarded', 'useragent')
    keys = 'started', 'siteinfo'
    table = table

    def execute(self, curs, cmd, *args):
        try:
            curs.execute(cmd, args)
        except PgSQL.DatabaseError, e:
            raise e.__class__('%s%s' % (e, cmd % args))

    def update(self, curs, vars):
        args = []
        s, k = [], []
        for col in self.cols:
            if col in vars:
                args.append(vars[col])
                s.append('%s=%%s' % col)
        for key in self.keys:
            args.append(vars[key])
            k.append('%s=%%s' % key)
        cmd = 'UPDATE %s SET %s WHERE %s' % (table, ', '.join(s), 
                                             ' AND '.join(k))
        self.execute(curs, cmd, *args)

    def insert(self, curs, vars):
        args = [vars.get(col) for col in self.cols]
        s = ['%s'] * len(self.cols)
        cmd = 'INSERT INTO %s (%s) VALUES (%s)' % (table, ', '.join(self.cols), 
                                                   ', '.join(s))
        self.execute(curs, cmd, *args)

    def updateinsert(self, vars):
        curs = db.cursor()
        try:
            self.execute(curs, 'LOCK TABLE %s' % table)
            self.update(curs, vars)
            if curs.rowcount == 0:
                self.insert(curs, vars)
        finally:
            curs.close()


db = PgSQL.connect(**database)
try:
    siteinfo = None
    for line in client_data.splitlines():
        if siteinfo is None:
            siteinfo = line
        elif line == '-- ':
            break
        else:
            vars = {}
            fields = line.split(',')
            vars['started'] = str(datetime.fromtimestamp(float(fields[0])/1000))
            vars['siteinfo'] = siteinfo
            vars['status'] = fields[1]
            try:
                vars['elapsed'] = float(fields[2]) / 1000
            except ValueError:
                pass
            try:
                vars['received'] = int(fields[3])
            except ValueError:
                pass
            vars['srcaddr'] = os.environ.get('REMOTE_ADDR')
            vars['forwarded'] = (os.environ.get('HTTP_X_FORWARDED_FOR') or
                                os.environ.get('HTTP_FORWARDED'))
            vars['useragent'] = os.environ.get('HTTP_USER_AGENT')
            Updater().updateinsert(vars)
except PgSQL.DatabaseError, e:
    db.rollback()
    print >> sys.stderr, 'update failed: %s' % e
else:
    db.commit()
