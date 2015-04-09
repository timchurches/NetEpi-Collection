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

from cocklebur import dbobj, utils, datetime
from casemgr import globals, search, paged_search, cases, contacts
from pages import page_common
import config


class PageOps(page_common.PageOpsBase):
    
    def do_new_contact_type(self, ctx, ignore):
        ctx.locals.contact_type = ''

    def do_new_contact_type_cancel(self, ctx, ignore):
        ctx.locals.new_contact_type = None

    def do_okay(self, ctx, ignore):
        if ctx.locals.new_contact_type:
            ctx.locals.assoc_contacts.new_contact_type(ctx.locals.contact_type)
        ctx.locals.assoc_contacts.associate()
        ctx.locals.case.user_log(ctx.locals.assoc_contacts.log_msg())
        globals.db.commit()
        ctx.locals.new_contact_type = None
        ctx.pop_page('casecontacts')


pageops = PageOps()


def page_enter(ctx, mode, assoc_ids):
    ctx.locals.assoc_mode = mode
    prefs = ctx.locals._credentials.prefs
    case_id = ctx.locals.case.case_row.case_id
    ctx.locals.assoc_contacts = contacts.AssocContacts(prefs, case_id, assoc_ids)
    paged_search.push_pager(ctx, ctx.locals.assoc_contacts)
    ctx.locals.new_contact_type = None
    ctx.add_session_vars('assoc_mode', 'assoc_contacts', 'new_contact_type')

def page_leave(ctx):
    paged_search.pop_pager(ctx)
    ctx.del_session_vars('assoc_mode', 'assoc_contacts', 'new_contact_type')

def page_display(ctx):
    ctx.run_template('casecontacts_assoc.html')

def page_process(ctx):
    try:
        ctx.locals.assoc_contacts.page_process(ctx)
        if pageops.page_process(ctx):
            return
    except dbobj.DatabaseError, e:
        ctx.add_error(e)

