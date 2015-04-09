#!/usr/local/bin/python
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
import albatross
import config
try:
    from albatross import fcgiappnew as fcgiapp
except ImportError:
    from albatross import fcgiapp

template = r'''
<al-include name="page_layout.html" />
<al-expand name="page_layout_banner">
 <al-setarg name="title">NetEpi Collection Application</al-setarg>
  <script language="JavaScript">
    function newWindow(fileName,windowName) {
      var flags = [
        'height=' + screen.availHeight,
        'width=' + screen.availWidth,
        'toolbar=no',
        'scrollbars=yes',
        'status=yes',
        'menubar=no',
        'hotkeys=no',
        'location=no',
        'resizable=yes',
        'copyhistory=no'
      ];
      var w = window.open(fileName, windowName, flags.join()); 
      if (w) {
        w.focus();
        w.moveTo(0,0);
      }
      return !w;
    }
  </script>
  <ul>
  <li><al-value expr="jslink('app', 'User application')" noescape /></li>
  </ul>
  <al-if expr="addrs">
   This NetEpi Collection server should be remotely accessible as <al-value expr="' or '.join(addrs)" />.
  <al-else>
   This NetEpi Collection server does not appear to have a public IP
   address although the applications will still be accessible from
   this machine.
  </al-if>
  <al-if expr="vids">
   <p>
   Demonstration videos:<br>
   <ul>
    <al-for iter="v" expr="vids">
     <al-exec expr="u, l = v.value()" />
     <li><al-a expr="u"><al-value expr="l" /></al-a></li>
    </al-for>
   </ul>
   </p>
  </al-if>
</al-expand>
'''

ip_re = re.compile('\s+inet addr:(\S+)')
flags_re = re.compile('\s+(.*)\s+MTU:')

def get_addrs():
    iface = addr = up = None
    for line in os.popen('/sbin/ifconfig'):
        if not line[0].isspace():
            if iface and up and addr:
                yield 'http://%s/%s/' % (addr, config.appname)
            iface, rest = line.split(None, 1)
            addr = up = None
        else:
            match = ip_re.match(line)
            if match:
                addr = match.group(1)
            else:
                match = flags_re.match(line)
                if match:
                    flags = match.group(1).split()
                    up = 'UP' in flags and 'LOOPBACK' not in flags

def get_videos():
    ext = '.html'
    try:
        filenames = os.listdir(os.path.join(config.html_target, 'video'))
    except OSError:
        pass
    else:
        for fn in filenames:
            if fn.endswith(ext):
                label = fn[:-len(ext)].replace('_', ' ')
                yield os.path.join('/', config.appname, 'video', fn), label

class Context(albatross.SimpleAppContext):
    def __init__(self, app):
        albatross.SimpleAppContext.__init__(self, app)
        self.locals.appath = self.appath
        self.locals.appname = config.appname
        self.locals.apptitle = config.apptitle
        self.locals._credentials = None
        self.locals.debug = False
        self.locals.get_messages = self.get_messages
        self.locals.get_errors = self.get_messages
        self.locals.has_js = False
        self.locals.request_start = 0
        self.locals.request_elapsed = self.request_elapsed
        self.locals.session_timeout = None
        self.locals.__page__ = 'menu'
        self.locals.jslink = self.jslink
        self.locals.addrs = list(get_addrs())
        self.locals.vids = list(get_videos())

    def jslink(self, app, label):
        return ('<a href="/cgi-bin/%s/%s.py"\n'
                '  onclick="return newWindow(\'/cgi-bin/%s/%s.py\',\'%s\')">'
                '%s</a>' % (config.appname, app,
                            config.appname, app, app,
                            label))
                                        
    def appath(self, *args):
        return '/'.join(('', self.locals.appname) + args)

    def get_messages(self):
        return []

    def request_elapsed(self):
        return 0

    def redirect_url(self, href):
        return href

    def current_url(self):
        return ''

app = albatross.SimpleApp('.', 'pages', None, '<secret>')
while fcgiapp.running():
    req = fcgiapp.Request()
    ctx = Context(app)
    ctx.set_request(req)
    tmpl = albatross.Template(ctx, '<magic>', template)
    tmpl.to_html(ctx)
    ctx.flush_content()
    req.return_code()
