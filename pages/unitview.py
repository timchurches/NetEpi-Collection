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
from casemgr import globals, paged_search, user_search
from pages import page_common

import config


class PageOps(page_common.PageOpsBase):
    def do_pager(self, ctx, op):
        ctx.locals.unit_users.do(op)

pageops = PageOps()

def page_enter(ctx, unit_id):
    cred = ctx.locals._credentials
    query = globals.db.query('units')
    query.where('unit_id = %s', unit_id)
    ctx.locals.unit = query.fetchone()
    unit_users = user_search.UserByUnitSearch(cred.prefs, unit_id)
    paged_search.push_pager(ctx, unit_users)
    ctx.add_session_vars('unit')

def page_leave(ctx):
    paged_search.pop_pager(ctx)
    ctx.del_session_vars('unit')

def page_display(ctx):
    ctx.run_template('unitview.html')

def page_process(ctx):
    pageops.page_process(ctx)
