#!/usr/bin/python
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
import time

# Get globals setup out of the way early as other modules depend on it.
from casemgr import globals
from cocklebur import dbobj
from casemgr import albasetup, handle_exception, persondupestat
from casemgr.notification.client import connect as notify_connect
import config

config_vars = (
    'appname',
    'apptitle',
    'debug',
    'helpdesk_contact',
    'html_target',
    'session_timeout',
)

dbobj.execute_debug(config.tracedb)
dbobj.execute_timing(config.exec_timing)

globals.notify = notify_connect(config.cgi_target,
                                config.notification_host,
                                config.notification_port)

persondupestat.dupescan_subscribe()


app = albasetup.get_app(config, config_vars, 
                        base_url='app.py', 
                        module_path='pages', 
                        template_path = 'pages', 
                        start_page = 'login')


if __name__ == '__main__':

    req_count = 0
    for req in albasetup.next_request():
        if req.get_method() == 'OPTIONS':
            # MS Sharepoint emits HTTP 1.1 OPTIONS methods to determine if the
            # server supports WebDAV - the cgi module generates a broken
            # FieldStorage object in this case, so we short-circuit the
            # request.
            req.end_headers()
            req.return_code()
            continue
        req_count += 1
        globals.remote_host = req.get_remote_host()
        try:
            globals.db.load_describer()         # Pick up any schema changes
            app.run(req)
            globals.notify.poll()
        finally:
            globals.db.rollback()
        if config.exec_timing:
            from cocklebur.dbobj import exec_timing
            exec_timing.show()
        if config.max_requests and req_count >= config.max_requests:
            # After servicing this many requests, we exit gracefully to
            # minimise the impact of memory fragmentation and object leaks.
            break
