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
import os
import csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from casemgr.notification.client import dummy_notification_client

class DummyGlobals:
    notify = dummy_notification_client()

import casemgr
sys.modules['casemgr.globals'] = casemgr.globals = DummyGlobals()

from casemgr import demogfields


writer = csv.writer(sys.stdout)
attrs = (
    'name','label','render','section','entity',
    'show_case','show_form','show_person','show_result',
    'field_case','field_form','field_person','field_result',
)

writer.writerow(attrs)
for field in demogfields.demog_classes:
    row = []
    for attr in attrs:
        row.append(getattr(field, attr, None))
    writer.writerow(row)
