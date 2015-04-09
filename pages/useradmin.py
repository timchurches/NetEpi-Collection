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
from cocklebur import dbobj
from casemgr import globals, credentials, logview, user_edit
from pages import page_common
import config

class User:
    def __init__(self, dbrow):
        self.user_id = dbrow.user_id;
        self.enabled = dbrow.enabled;
        self.username = dbrow.username;
        self.fullname = dbrow.fullname;
        self.title = dbrow.title;
        self.timelock_str = credentials.timelock_remain_str(dbrow)


class PageOps(page_common.PageOpsBase):
    def do_edit(self, ctx, user_id):
        ue = user_edit.RoleAdmin(ctx.locals._credentials, int(user_id))
        ctx.push_page('useredit', ue)

    def do_log(self, ctx, user_id):
        query = globals.db.query('users')
        query.where('user_id = %s', user_id)
        username = query.fetchone().username
        log = logview.UserLogView(ctx.locals._credentials.prefs, 
                                  'Log for user %r' % username, 
                                  user_id=user_id)

        ctx.push_page('logview', log)

    def do_back(self, ctx, ignore):
        ctx.pop_page()

    def do_new(self, ctx, ignore):
        ue = user_edit.RoleAdmin(ctx.locals._credentials, None)
        ctx.push_page('useredit', ue)

pageops = PageOps()


def page_display(ctx):
    cred = ctx.locals._credentials
    try:
        query = globals.db.query('users', order_by='fullname')
        query.join('LEFT JOIN unit_users USING (user_id)')
        query.where('unit_id = %s', cred.unit.unit_id)
        query.where('not deleted')
        ctx.locals.users = [User(r) for r in query.fetchall()]
    except dbobj.DatabaseError, e:
        ctx.add_error(e)
        ctx.locals.users = []
    ctx.run_template('useradmin.html')

def page_process(ctx):
    pageops.page_process(ctx)

