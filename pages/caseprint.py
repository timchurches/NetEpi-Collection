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
from pages import page_common
from cocklebur import datetime, form_ui
from casemgr import globals, contacts

import config

def page_display(ctx):
    ctx.locals.contacts = contacts.ContactSearch(
                                        ctx.locals._credentials.prefs, 
                                        ctx.locals.case.case_row.case_id,
                                        ctx.locals.case.deleted)
    ctx.run_template('caseprint.html')

page_process = page_common.page_process
