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
import config
from cocklebur import dbobj
from cocklebur import form_ui
from casemgr.notification.client import dummy_notification_client

__all__ = 'db', 'formlib'

# Application globals
dbobj.execute_debug(config.tracedb)
db = dbobj.get_db(os.path.join(config.cgi_target, 'db'), config.dsn)
formlib = form_ui.FormLibXMLDB(db, 'form_defs')
remote_host = None
notify = dummy_notification_client()

class Error(Exception): pass        # catchall for informational error messages
class ReviewForm(Error): pass
